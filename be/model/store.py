import logging
import os
import threading
from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError

class Store:
    def __init__(self, db_name):
        # 使用固定的数据库名
        self.client = MongoClient('localhost', 27017)
        self.db = self.client[db_name]
        self.init_collections()

    def init_collections(self):
        try:
            # 创建集合和索引
            # User 集合
            self.db.user.create_index([("user_id", ASCENDING)], unique=True)
            
            # User_store 集合
            self.db.user_store.create_index([("store_id", ASCENDING)], unique=True)
            self.db.user_store.create_index([("user_id", ASCENDING)])
            
            # Store 集合 (店铺库存)
            self.db.store.create_index([("store_id", ASCENDING), ("book_id", ASCENDING)], unique=True)
            self.db.store.create_index([("store_id", ASCENDING)])
            self.db.store.create_index([("book_id", ASCENDING)])
            
            # Book 集合 (图书信息)
            self.db.book.create_index([("id", ASCENDING)], unique=True)
            
            # Orders 集合
            self.db.orders.create_index([("order_id", ASCENDING)], unique=True)
            self.db.orders.create_index([("user_id", ASCENDING)])
            self.db.orders.create_index([("store_id", ASCENDING)])
            
            # Order_details 集合
            self.db.order_details.create_index([("order_id", ASCENDING), ("book_id", ASCENDING)], unique=True)
            self.db.order_details.create_index([("order_id", ASCENDING)])
            
            print("MongoDB collections initialized successfully")
            
        except PyMongoError as e:
            logging.error(f"MongoDB initialization error: {e}")
            print(f"MongoDB initialization error: {e}")

    def get_db_conn(self):
        return self.db

database_instance: Store = None
init_completed_event = threading.Event()

def init_database(db_name):
    global database_instance
    database_instance = Store(db_name)

def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()