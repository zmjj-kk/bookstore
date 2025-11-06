import os
import random
import base64
import simplejson as json
from pymongo import MongoClient


class Book:
    id: str
    title: str
    author: str
    publisher: str
    original_title: str
    translator: str
    pub_year: str
    pages: int
    price: int
    currency_unit: str
    binding: str
    isbn: str
    author_intro: str
    book_intro: str
    content: str
    tags: [str]
    pictures: [bytes]

    def __init__(self):
        self.tags = []
        self.pictures = []


class BookDB:
    def __init__(self, large: bool = False):
        # 连接 MongoDB（与迁移脚本保持一致）
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['bookstore_db']  # 数据库名
        self.collection = self.db['books']     # 集合名（迁移后的图书数据）

        # 兼容原逻辑的路径定义（实际不再使用SQLite）
        parent_path = os.path.dirname(os.path.dirname(__file__))
        self.db_s = os.path.join(parent_path, "data/book.db")
        self.db_l = os.path.join(parent_path, "data/book_lx.db")
        self.large = large  # 保留参数，兼容原有调用方式

    def get_book_count(self) -> int:
        """获取图书总数（替代SQLite查询）"""
        return self.collection.count_documents({})

    def get_book_info(self, start: int, size: int) -> [Book]:
        """批量获取图书信息（从MongoDB查询，保持原返回格式）"""
        books = []
        
        # MongoDB查询：按id排序，分页获取
        cursor = self.collection.find() \
            .sort("id", 1) \
            .skip(start) \
            .limit(size)

        for doc in cursor:
            book = Book()
            # 基础字段映射（与MongoDB文档字段对应）
            book.id = doc.get("id", "")
            book.title = doc.get("title", "")
            book.author = doc.get("author", "")
            book.publisher = doc.get("publisher", "")
            book.original_title = doc.get("original_title", "")
            book.translator = doc.get("translator", "")
            book.pub_year = doc.get("pub_year", "")
            book.pages = doc.get("pages", 0)
            book.price = doc.get("price", 0)
            book.currency_unit = doc.get("currency_unit", "")
            book.binding = doc.get("binding", "")
            book.isbn = doc.get("isbn", "")
            book.author_intro = doc.get("author_intro", "")
            book.book_intro = doc.get("book_intro", "")
            book.content = doc.get("content", "")

            # 处理标签（原SQLite中是换行分隔的字符串）
            tags = doc.get("tags", "")
            if isinstance(tags, str):
                for tag in tags.split("\n"):
                    if tag.strip():
                        book.tags.append(tag)
            elif isinstance(tags, list):
                # 若迁移时已转为列表，直接使用
                book.tags = [t for t in tags if t.strip()]

            # 处理图片（模拟原逻辑的随机数量base64编码）
            picture = doc.get("picture", None)
            if picture:
                encode_str = base64.b64encode(picture).decode("utf-8")
                # 随机生成0-9张图片（与原逻辑一致）
                for _ in range(random.randint(0, 9)):
                    book.pictures.append(encode_str)

            books.append(book)

        return books