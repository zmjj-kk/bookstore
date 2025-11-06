import logging
import os  # 添加这一行
import threading
from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError, ConnectionFailure


class Store:
    def __init__(self, db_name: str = "bookstore"):
        """初始化MongoDB连接和集合
        
        Args:
            db_name: 数据库名称，默认使用"bookstore"
        """
        self.client = None
        self.db = None
        self.db_name = db_name
        self._connect()  # 建立连接
        self.init_collections()  # 初始化集合和索引

    def _connect(self):
        """建立MongoDB连接并处理连接错误"""
        try:
            # 支持通过环境变量配置MongoDB连接（便于部署）
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
            self.client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000,  # 连接超时时间5秒
                maxPoolSize=100  # 连接池大小
            )
            
            # 验证连接
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]
            logging.info(f"Successfully connected to MongoDB: {self.db_name}")
            
        except ConnectionFailure:
            logging.error("MongoDB connection failed: Could not connect to server")
            raise  # 抛出异常让上层处理
        except PyMongoError as e:
            logging.error(f"MongoDB connection error: {str(e)}")
            raise

    def init_collections(self):
        """初始化集合和索引，确保数据完整性和查询性能"""
        try:
            # 先删除所有 id 为 null 的文档
            self.db.book.delete_many({"id": None})

            # 创建索引，并忽略 id 为 null 的文档
            self.db.book.create_index(
                [("id", ASCENDING)],
                unique=True,
                background=True,
                partialFilterExpression={"id": {"$exists": True}}  # 仅为存在 id 的文档创建索引
            )

            # 用户集合：存储用户信息
            self.db.user.create_index(
                [("user_id", ASCENDING)], 
                unique=True,
                background=True  # 后台创建索引，不阻塞其他操作
            )
            
            # 店铺-用户关联集合：记录店铺归属
            self.db.user_store.create_index(
                [("store_id", ASCENDING)], 
                unique=True,
                background=True
            )
            self.db.user_store.create_index(
                [("user_id", ASCENDING)],
                background=True
            )
            
            # 库存集合：记录店铺图书库存
            self.db.store.create_index(
                [("store_id", ASCENDING), ("book_id", ASCENDING)],
                unique=True,
                background=True
            )
            # 新增库存查询索引（按店铺和库存水平） 
            self.db.store.create_index(
                [("store_id", ASCENDING), ("stock_level", ASCENDING)],
                background=True
            )
            
            # 图书信息集合
            self.db.book.create_index(
                [("title", ASCENDING), ("author", ASCENDING)],
                background=True
            )
            
            # 订单集合
            self.db.orders.create_index(
                [("order_id", ASCENDING)],
                unique=True,
                background=True
            )
            self.db.orders.create_index(
                [("user_id", ASCENDING), ("status", ASCENDING)],
                background=True
            )
            self.db.orders.create_index(
                [("store_id", ASCENDING), ("status", ASCENDING)],
                background=True
            )
            # 订单超时清理索引（与order_cleanup.py对应）
            self.db.orders.create_index(
                [("status", ASCENDING), ("create_time", ASCENDING)],
                background=True
            )
            
            # 订单详情集合
            self.db.order_details.create_index(
                [("order_id", ASCENDING), ("book_id", ASCENDING)],
                unique=True,
                background=True
            )
            
            logging.info("MongoDB collections and indexes initialized successfully")
            
        except PyMongoError as e:
            logging.error(f"Failed to initialize collections/indexes: {str(e)}")
            raise

    def get_db_conn(self):
        """获取数据库连接对象"""
        if not self.db:
            raise RuntimeError("MongoDB connection not initialized")
        return self.db

    def close(self):
        """关闭数据库连接"""
        if self.client:
            self.client.close()
            logging.info("MongoDB connection closed")


# 单例模式管理数据库实例
database_instance: Store = None
init_completed_event = threading.Event()  # 用于同步初始化完成状态


def init_database(db_name: str = "bookstore"):
    """初始化数据库单例实例"""
    global database_instance
    if not database_instance:
        try:
            database_instance = Store(db_name)
            init_completed_event.set()  # 标记初始化完成
            logging.info("Database initialization completed")
        except Exception as e:
            logging.error(f"Database initialization failed: {str(e)}")
            init_completed_event.clear()
            raise


def get_db_conn():
    """获取数据库连接（确保初始化完成）"""
    global database_instance
    if not init_completed_event.wait(timeout=10):  # 等待初始化完成，超时10秒
        raise TimeoutError("Database initialization timed out")
    if not database_instance:
        raise RuntimeError("Database not initialized")
    return database_instance.get_db_conn()


# 程序退出时自动关闭连接
import atexit
atexit.register(lambda: database_instance.close() if database_instance else None)

