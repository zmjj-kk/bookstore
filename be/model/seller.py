import json
import logging
from datetime import datetime
from be.model import error
from be.model import db_conn
from pymongo.errors import PyMongoError


class Seller(db_conn.DBConn):
    def __init__(self):
        super().__init__()

    def add_book(self, user_id: str, store_id: str, book_id: str, book_json_str: str, stock_level: int) -> (int, str):
        """添加图书到店铺"""
        try:
            # 验证用户和店铺存在性
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            # 验证图书是否已存在
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            # 解析图书信息（验证JSON格式）
            try:
                book_info = json.loads(book_json_str)
                if "price" not in book_info:
                    return error.error_invalid_parameter("book_info missing 'price'")
            except json.JSONDecodeError:
                return error.error_invalid_parameter("invalid book_json_str format")

            # 添加图书到店铺集合
            self.db.store.insert_one({
                "store_id": store_id,
                "book_id": book_id,
                "book_info": book_json_str,
                "stock_level": stock_level,
                "add_time": datetime.now()  # 记录添加时间
            })
            return 200, "ok"
            
        except PyMongoError as e:
            logging.error(f"MongoDB error in add_book: {str(e)}")
            return error.error_database_error(str(e))
        except Exception as e:
            logging.error(f"Unexpected error in add_book: {str(e)}")
            return 530, str(e)

    def add_stock_level(self, user_id: str, store_id: str, book_id: str, add_stock_level: int) -> (int, str):
        """增加图书库存"""
        try:
            # 验证权限和存在性
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)
            # 验证库存增量为正数
            if add_stock_level <= 0:
                return error.error_invalid_parameter("add_stock_level must be positive")

            # 原子性增加库存
            result = self.db.store.update_one(
                {"store_id": store_id, "book_id": book_id},
                {"$inc": {"stock_level": add_stock_level}, "$set": {"update_time": datetime.now()}}
            )
            
            if result.modified_count == 0:
                return error.error_non_exist_book_id(book_id)
                
            return 200, "ok"
            
        except PyMongoError as e:
            return error.error_database_error(str(e))
        except Exception as e:
            return 530, str(e)

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        """创建店铺"""
        try:
            # 验证用户存在性
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            # 验证店铺是否已存在
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
                
            # 创建店铺记录
            self.db.user_store.insert_one({
                "store_id": store_id,
                "user_id": user_id,
                "create_time": datetime.now()
            })
            return 200, "ok"
            
        except PyMongoError as e:
            return error.error_database_error(str(e))
        except Exception as e:
            return 530, str(e)

    def ship_books(self, user_id: str, store_id: str, order_id: str) -> (int, str):
        """发货操作"""
        try:
            # 验证店铺所有权
            store_owner = self.db.user_store.find_one({
                "store_id": store_id, 
                "user_id": user_id
            })
            if not store_owner:
                return error.error_authorization_fail()

            # 查询订单
            order = self.db.orders.find_one({
                "order_id": order_id,
                "store_id": store_id
            })
            if not order:
                return error.error_invalid_order_id(order_id)

            # 验证订单状态
            current_status = order.get("status")
            if current_status != "paid":
                return error.error_order_not_paid(order_id)  # 使用新增的错误码

            # 更新订单状态为已发货（记录发货时间）
            result = self.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {
                    "status": "shipped",
                    "ship_time": datetime.now()
                }}
            )

            if result.modified_count == 0:
                return 518, "Failed to update order status"

            return 200, "ok"

        except PyMongoError as e:
            return error.error_database_error(str(e))
        except Exception as e:
            return 530, str(e)

    # 新增：查询店铺订单
    def query_store_orders(self, user_id: str, store_id: str, status: str = None) -> (int, str, list):
        """查询店铺订单（支持按状态筛选）"""
        try:
            # 验证店铺所有权
            if not self.db.user_store.find_one({"store_id": store_id, "user_id": user_id}):
                return error.error_authorization_fail() + ([],)

            # 构建查询条件
            query = {"store_id": store_id}
            if status:
                query["status"] = status

            # 查询订单并按创建时间排序
            orders = self.db.orders.find(query).sort("create_time", -1)
            order_list = []

            for order in orders:
                # 获取订单详情
                details = self.db.order_details.find({"order_id": order["order_id"]})
                items = []
                total = 0

                for d in details:
                    book = self.db.books.find_one({"id": d["book_id"]}) or {}
                    items.append({
                        "book_id": d["book_id"],
                        "title": book.get("title", ""),
                        "count": d["count"],
                        "price": d["price"]
                    })
                    total += d["count"] * d["price"]

                order_list.append({
                    "order_id": order["order_id"],
                    "user_id": order["user_id"],
                    "status": order["status"],
                    "create_time": order["create_time"],
                    "total_amount": total,
                    "items": items
                })

            return 200, "ok", order_list

        except PyMongoError as e:
            return error.error_database_error(str(e)) + ([],)
        except Exception as e:
            return 530, str(e), []