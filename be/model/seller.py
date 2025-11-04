import json
import logging
from be.model import error
from be.model import db_conn
from pymongo.errors import PyMongoError

class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(self, user_id: str, store_id: str, book_id: str, book_json_str: str, stock_level: int):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            # 添加图书到店铺
            store_doc = {
                "store_id": store_id,
                "book_id": book_id,
                "book_info": book_json_str,
                "stock_level": stock_level
            }
            
            self.db.store.insert_one(store_doc)
            return 200, "ok"
            
        except PyMongoError as e:
            logging.error(f"MongoDB error in add_book: {e}")
            return 528, "{}".format(str(e))
        except Exception as e:
            logging.error(f"Unexpected error in add_book: {e}")
            return 530, "{}".format(str(e))

    def add_stock_level(self, user_id: str, store_id: str, book_id: str, add_stock_level: int):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            result = self.db.store.update_one(
                {
                    "store_id": store_id,
                    "book_id": book_id
                },
                {
                    "$inc": {"stock_level": add_stock_level}
                }
            )
            
            if result.modified_count == 0:
                return error.error_non_exist_book_id(book_id)
                
            return 200, "ok"
            
        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except Exception as e:
            return 530, "{}".format(str(e))

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
                
            store_doc = {
                "store_id": store_id,
                "user_id": user_id
            }
            
            self.db.user_store.insert_one(store_doc)
            return 200, "ok"
            
        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except Exception as e:
            return 530, "{}".format(str(e))
        
    # 在 seller.py 中添加以下方法

    def ship_books(self, user_id: str, store_id: str, order_id: str) -> (int, str):
        try:
            print(f"DEBUG ship_books: Starting shipment for order {order_id}")
            print(f"DEBUG ship_books: user_id={user_id}, store_id={store_id}")
            
            # 验证用户是否有权限管理该店铺
            store_owner = self.db.user_store.find_one({
                "store_id": store_id, 
                "user_id": user_id
            })
            if store_owner is None:
                print(f"DEBUG ship_books: Authorization failed - user {user_id} doesn't own store {store_id}")
                return error.error_authorization_fail()

            print(f"DEBUG ship_books: Store ownership verified")

            # 查找订单
            order = self.db.orders.find_one({
                "order_id": order_id,
                "store_id": store_id
            })
            if order is None:
                print(f"DEBUG ship_books: Order {order_id} not found in store {store_id}")
                return error.error_invalid_order_id(order_id)

            print(f"DEBUG ship_books: Order found: {order}")

            # 检查订单状态是否为已付款
            current_status = order.get("status")
            print(f"DEBUG ship_books: Current order status: {current_status}")
            
            if current_status != "paid":
                print(f"DEBUG ship_books: Order status is '{current_status}', expected 'paid'")
                return 518, "Order is not paid yet"

            # 更新订单状态为已发货
            result = self.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": "shipped"}}
            )

            print(f"DEBUG ship_books: Update result - modified_count: {result.modified_count}")

            if result.modified_count == 0:
                print(f"DEBUG ship_books: Failed to update order status")
                return 518, "Failed to update order status"

            print(f"DEBUG ship_books: Shipment successful!")
            return 200, "ok"

        except PyMongoError as e:
            print(f"DEBUG ship_books: MongoDB error: {e}")
            return 528, "{}".format(str(e))
        except Exception as e:
            print(f"DEBUG ship_books: Unexpected error: {e}")
            import traceback
            print(f"DEBUG ship_books: Traceback: {traceback.format_exc()}")
            return 530, "{}".format(str(e))