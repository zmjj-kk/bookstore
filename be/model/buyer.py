import uuid
import json
import logging
from be.model import db_conn
from be.model import error
from pymongo.errors import PyMongoError
from datetime import datetime

class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(self, user_id: str, store_id: str, id_and_count: [(str, int)]) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
            order_details = []

            for book_id, count in id_and_count:
                # 查找图书库存
                store_item = self.db.store.find_one({
                    "store_id": store_id,
                    "book_id": book_id
                })
                
                if store_item is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = store_item.get("stock_level", 0)
                book_info = store_item.get("book_info", "{}")
                
                try:
                    book_info_json = json.loads(book_info)
                    price = book_info_json.get("price", 0)
                except:
                    price = 0

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                # 更新库存
                result = self.db.store.update_one(
                    {
                        "store_id": store_id,
                        "book_id": book_id,
                        "stock_level": {"$gte": count}
                    },
                    {
                        "$inc": {"stock_level": -count}
                    }
                )
                
                if result.modified_count == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)

                # 添加订单详情
                order_detail = {
                    "order_id": uid,
                    "book_id": book_id,
                    "count": count,
                    "price": price
                }
                order_details.append(order_detail)

            # 插入订单详情
            if order_details:
                self.db.order_details.insert_many(order_details)

            # 创建订单
            order_doc = {
                "order_id": uid,
                "user_id": user_id,
                "store_id": store_id,
                "status": "pending", # 新增状态字段
                "create_time": datetime.now()  # 添加创建时间
            }
            self.db.orders.insert_one(order_doc)
            
            order_id = uid
            return 200, "ok", order_id
            
        except PyMongoError as e:
            logging.error(f"MongoDB error in new_order: {e}")
            return 528, "{}".format(str(e)), ""
        except Exception as e:
            logging.error(f"Unexpected error in new_order: {e}")
            return 530, "{}".format(str(e)), ""

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            # 查找订单
            order = self.db.orders.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)

            buyer_id = order.get("user_id")
            store_id = order.get("store_id")

            if buyer_id != user_id:
                return error.error_authorization_fail()

            # 验证买家密码
            buyer = self.db.user.find_one({"user_id": buyer_id})
            if buyer is None:
                return error.error_non_exist_user_id(buyer_id)
                
            if password != buyer.get("password"):
                return error.error_authorization_fail()

            # 查找卖家
            store_owner = self.db.user_store.find_one({"store_id": store_id})
            if store_owner is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = store_owner.get("user_id")
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            # 计算总价
            order_items = self.db.order_details.find({"order_id": order_id})
            total_price = 0
            for item in order_items:
                count = item.get("count", 0)
                price = item.get("price", 0)
                total_price += price * count

            balance = buyer.get("balance", 0)
            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            # 更新买家余额
            result_buyer = self.db.user.update_one(
                {
                    "user_id": buyer_id,
                    "balance": {"$gte": total_price}
                },
                {
                    "$inc": {"balance": -total_price}
                }
            )
            
            if result_buyer.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            # 更新卖家余额
            result_seller = self.db.user.update_one(
                {"user_id": seller_id},
                {"$inc": {"balance": total_price}}
            )
            
            if result_seller.modified_count == 0:
                return error.error_non_exist_user_id(seller_id)

            # 更新订单状态
            self.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": "paid"}}
            )

            return 200, "ok"
            
        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except Exception as e:
            return 530, "{}".format(str(e))

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            user_doc = self.db.user.find_one({"user_id": user_id})
            if user_doc is None:
                return error.error_authorization_fail()

            if user_doc.get("password") != password:
                return error.error_authorization_fail()

            result = self.db.user.update_one(
                {"user_id": user_id},
                {"$inc": {"balance": add_value}}
            )
            
            if result.modified_count == 0:
                return error.error_non_exist_user_id(user_id)

            return 200, "ok"
            
        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except Exception as e:
            return 530, "{}".format(str(e))
        
    # 在 buyer.py 中添加以下方法

    # be/model/buyer.py
    def receive_books(self, user_id: str, order_id: str) -> (int, str):
        try:
            # 查找订单
            order = self.db.orders.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)

            # 验证用户权限
            if order.get("user_id") != user_id:
                return error.error_authorization_fail()

            # 检查订单状态是否为已发货
            if order.get("status") != "shipped":
                return 518, "Order is not shipped yet"

            # 更新订单状态为已完成
            result = self.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": "completed"}}
            )

            if result.modified_count == 0:
                return 518, "Failed to update order status"

            return 200, "ok"

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except Exception as e:
            return 530, "{}".format(str(e))
    # 在 buyer.py 中添加以下方法

    def query_orders(self, user_id: str, status: str = None) -> (int, str, list):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + ([],)

            # 构建查询条件
            query = {"user_id": user_id}
            if status:
                query["status"] = status

            # 查询订单
            orders = self.db.orders.find(query).sort("order_id", -1)
            
            order_list = []
            for order in orders:
                order_id = order["order_id"]
                store_id = order["store_id"]
                status = order["status"]
                
                # 获取订单详情
                order_details = self.db.order_details.find({"order_id": order_id})
                items = []
                total_amount = 0
                
                for detail in order_details:
                    book_info = self.db.book.find_one({"id": detail["book_id"]})
                    item = {
                        "book_id": detail["book_id"],
                        "count": detail["count"],
                        "price": detail["price"],
                        "title": book_info.get("title", "") if book_info else "",
                        "author": book_info.get("author", "") if book_info else ""
                    }
                    items.append(item)
                    total_amount += detail["price"] * detail["count"]
                
                order_info = {
                    "order_id": order_id,
                    "store_id": store_id,
                    "status": status,
                    "items": items,
                    "total_amount": total_amount,
                    "create_time": order.get("_id").generation_time if order.get("_id") else None
                }
                order_list.append(order_info)

            return 200, "ok", order_list

        except PyMongoError as e:
            return 528, "{}".format(str(e)), []
        except Exception as e:
            return 530, "{}".format(str(e)), []

    def cancel_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            # 查找订单
            order = self.db.orders.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)

            # 验证用户权限
            if order.get("user_id") != user_id:
                return error.error_authorization_fail()

            current_status = order.get("status")
            if current_status not in ["pending", "paid"]:
                return 518, "Cannot cancel order in current status"

            # 如果是已付款订单，需要退款
            if current_status == "paid":
                # 计算订单总金额
                order_details = self.db.order_details.find({"order_id": order_id})
                total_amount = 0
                for detail in order_details:
                    total_amount += detail["price"] * detail["count"]

                # 退款给买家
                self.db.user.update_one(
                    {"user_id": user_id},
                    {"$inc": {"balance": total_amount}}
                )

                # 从卖家账户扣除
                store_id = order["store_id"]
                store_owner = self.db.user_store.find_one({"store_id": store_id})
                if store_owner:
                    seller_id = store_owner["user_id"]
                    self.db.user.update_one(
                        {"user_id": seller_id},
                        {"$inc": {"balance": -total_amount}}
                    )

            # 恢复库存
            order_details = self.db.order_details.find({"order_id": order_id})
            for detail in order_details:
                self.db.store.update_one(
                    {
                        "store_id": order["store_id"],
                        "book_id": detail["book_id"]
                    },
                    {"$inc": {"stock_level": detail["count"]}}
                )

            # 更新订单状态为已取消
            self.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": "cancelled"}}
            )

            return 200, "ok"

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except Exception as e:
            return 530, "{}".format(str(e))