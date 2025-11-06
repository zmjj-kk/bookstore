import uuid
import json
import logging
from be.model import db_conn
from be.model import error
from pymongo.errors import PyMongoError
from datetime import datetime


class Buyer(db_conn.DBConn):
    def __init__(self):
        super().__init__()  # 使用super()简化初始化

    def new_order(self, user_id: str, store_id: str, id_and_count: [(str, int)]) -> (int, str, str):
        order_id = ""
        try:
            # 验证用户和店铺存在性
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            
            # 生成唯一订单ID
            uid = f"{user_id}_{store_id}_{uuid.uuid1()}"
            order_details = []

            for book_id, count in id_and_count:
                # 查询图书库存
                store_item = self.db.store.find_one({
                    "store_id": store_id,
                    "book_id": book_id
                })
                
                if not store_item:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = store_item.get("stock_level", 0)
                book_info = store_item.get("book_info", "{}")
                
                # 解析图书价格
                try:
                    book_info_json = json.loads(book_info)
                    price = book_info_json.get("price", 0)
                except json.JSONDecodeError:
                    logging.warning(f"Invalid book info JSON for book {book_id}")
                    price = 0

                # 检查库存
                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                # 原子性更新库存（避免超卖）
                update_result = self.db.store.update_one(
                    {
                        "store_id": store_id,
                        "book_id": book_id,
                        "stock_level": {"$gte": count}
                    },
                    {"$inc": {"stock_level": -count}}
                )
                
                if update_result.modified_count == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)

                # 收集订单详情
                order_details.append({
                    "order_id": uid,
                    "book_id": book_id,
                    "count": count,
                    "price": price
                })

            # 批量插入订单详情
            if order_details:
                self.db.order_details.insert_many(order_details)

            # 创建订单主记录（含状态和时间）
            self.db.orders.insert_one({
                "order_id": uid,
                "user_id": user_id,
                "store_id": store_id,
                "status": "pending",  # 待付款
                "create_time": datetime.now()
            })
            
            return 200, "ok", uid
            
        except PyMongoError as e:
            logging.error(f"MongoDB error in new_order: {str(e)}")
            return 528, str(e), ""
        except Exception as e:
            logging.error(f"Unexpected error in new_order: {str(e)}")
            return 530, str(e), ""

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            # 查询订单
            order = self.db.orders.find_one({"order_id": order_id})
            if not order:
                return error.error_invalid_order_id(order_id)

            # 验证订单归属
            buyer_id = order["user_id"]
            if buyer_id != user_id:
                return error.error_authorization_fail()

            # 验证买家密码
            buyer = self.db.user.find_one({"user_id": buyer_id})
            if not buyer:
                return error.error_non_exist_user_id(buyer_id)
            if buyer["password"] != password:
                return error.error_authorization_fail()

            # 查询店铺所属卖家
            store_owner = self.db.user_store.find_one({"store_id": order["store_id"]})
            if not store_owner:
                return error.error_non_exist_store_id(order["store_id"])
            seller_id = store_owner["user_id"]

            # 验证卖家存在
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            # 计算订单总价
            total_price = 0
            for item in self.db.order_details.find({"order_id": order_id}):
                total_price += item["price"] * item["count"]

            # 检查买家余额
            if buyer.get("balance", 0) < total_price:
                return error.error_not_sufficient_funds(order_id)

            # 原子性扣减买家余额
            if self.db.user.update_one(
                {"user_id": buyer_id, "balance": {"$gte": total_price}},
                {"$inc": {"balance": -total_price}}
            ).modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            # 增加卖家余额
            if self.db.user.update_one(
                {"user_id": seller_id},
                {"$inc": {"balance": total_price}}
            ).modified_count == 0:
                return error.error_non_exist_user_id(seller_id)

            # 更新订单状态为已付款
            self.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": "paid", "pay_time": datetime.now()}}
            )

            return 200, "ok"
            
        except PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

    def add_funds(self, user_id: str, password: str, add_value: int) -> (int, str):
        try:
            # 验证用户及密码
            user = self.db.user.find_one({"user_id": user_id})
            if not user:
                return error.error_authorization_fail()
            if user["password"] != password:
                return error.error_authorization_fail()

            # 增加余额
            if self.db.user.update_one(
                {"user_id": user_id},
                {"$inc": {"balance": add_value}}
            ).modified_count == 0:
                return error.error_non_exist_user_id(user_id)

            return 200, "ok"
            
        except PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

    def receive_books(self, user_id: str, order_id: str) -> (int, str):
        """买家确认收货"""
        try:
            order = self.db.orders.find_one({"order_id": order_id})
            if not order:
                return error.error_invalid_order_id(order_id)

            # 验证权限和订单状态
            if order["user_id"] != user_id:
                return error.error_authorization_fail()
            if order["status"] != "shipped":
                return 518, "Order not in shipped status"

            # 更新为已完成
            self.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": "completed", "receive_time": datetime.now()}}
            )
            return 200, "ok"

        except PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)

    def query_orders(self, user_id: str, status: str = None) -> (int, str, list):
        """查询订单列表（支持按状态筛选）"""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + ([],)

            # 构建查询条件
            query = {"user_id": user_id}
            if status:
                query["status"] = status

            # 查询订单并排序
            orders = self.db.orders.find(query).sort("create_time", -1)
            order_list = []

            for order in orders:
                # 获取订单详情
                details = self.db.order_details.find({"order_id": order["order_id"]})
                items = []
                total = 0

                for d in details:
                    # 补充图书信息
                    book = self.db.book.find_one({"id": d["book_id"]}) or {}
                    items.append({
                        "book_id": d["book_id"],
                        "title": book.get("title", ""),
                        "count": d["count"],
                        "price": d["price"]
                    })
                    total += d["count"] * d["price"]

                order_list.append({
                    "order_id": order["order_id"],
                    "store_id": order["store_id"],
                    "status": order["status"],
                    "create_time": order["create_time"],
                    "total_amount": total,
                    "items": items
                })

            return 200, "ok", order_list

        except PyMongoError as e:
            return 528, str(e), []
        except Exception as e:
            return 530, str(e), []

    def cancel_order(self, user_id: str, order_id: str) -> (int, str):
        """取消订单（支持未付款/已付款状态）"""
        try:
            order = self.db.orders.find_one({"order_id": order_id})
            if not order:
                return error.error_invalid_order_id(order_id)

            # 验证权限
            if order["user_id"] != user_id:
                return error.error_authorization_fail()

            # 检查可取消状态
            current_status = order["status"]
            if current_status not in ["pending", "paid"]:
                return 518, f"Cannot cancel order in {current_status} status"

            # 已付款订单需要退款
            if current_status == "paid":
                # 计算退款金额
                total = 0
                details = self.db.order_details.find({"order_id": order_id})
                for d in details:
                    total += d["count"] * d["price"]

                # 退款给买家
                self.db.user.update_one(
                    {"user_id": user_id},
                    {"$inc": {"balance": total}}
                )

                # 从卖家扣回
                store = self.db.user_store.find_one({"store_id": order["store_id"]})
                if store:
                    self.db.user.update_one(
                        {"user_id": store["user_id"]},
                        {"$inc": {"balance": -total}}
                    )

            # 恢复库存
            for d in self.db.order_details.find({"order_id": order_id}):
                self.db.store.update_one(
                    {"store_id": order["store_id"], "book_id": d["book_id"]},
                    {"$inc": {"stock_level": d["count"]}}
                )

            # 更新订单状态
            self.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": "cancelled", "cancel_time": datetime.now()}}
            )

            return 200, "ok"

        except PyMongoError as e:
            return 528, str(e)
        except Exception as e:
            return 530, str(e)