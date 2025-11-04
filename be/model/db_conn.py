from be.model import store
from pymongo.errors import PyMongoError

class DBConn:
    def __init__(self):
        self.db = store.get_db_conn()

    def user_id_exist(self, user_id):
        try:
            user = self.db.user.find_one({"user_id": user_id})
            return user is not None
        except PyMongoError:
            return False

    def book_id_exist(self, store_id, book_id):
        try:
            # 检查店铺中是否有该图书
            store_item = self.db.store.find_one({
                "store_id": store_id, 
                "book_id": book_id
            })
            return store_item is not None
        except PyMongoError:
            return False

    def store_id_exist(self, store_id):
        try:
            store_doc = self.db.user_store.find_one({"store_id": store_id})
            return store_doc is not None
        except PyMongoError:
            return False