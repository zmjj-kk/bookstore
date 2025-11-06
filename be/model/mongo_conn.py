from pymongo import MongoClient
import os
import threading

class MongoConn:
    def __init__(self):
        # 连接本地 MongoDB（默认端口 27017）
        self.client = MongoClient("mongodb://localhost:27017/")
        # 创建/使用数据库
        self.db = self.client["bookstore"]

    def get_collection(self, collection_name):
        """获取集合（类似 SQL 的表）"""
        return self.db[collection_name]

# 单例模式
mongo_instance = None
init_completed_event = threading.Event()

def init_mongo():
    global mongo_instance
    mongo_instance = MongoConn()
    init_completed_event.set()

def get_mongo_conn():
    global mongo_instance
    return mongo_instance