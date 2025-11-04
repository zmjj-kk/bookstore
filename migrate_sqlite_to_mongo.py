# -*- coding: utf-8 -*-
"""
Created on Sun Nov  2 10:13:00 2025

@author: LL
"""

import sqlite3
from pymongo import MongoClient

# 连接 SQLite 数据库
sqlite_conn = sqlite3.connect(r'C:\Users\LL\bookstore\fe\data\book_lx.db')
sqlite_cursor = sqlite_conn.cursor()

# 连接 MongoDB 数据库
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['bookstore_db']
books_collection = db['books']

# 读取 SQLite 数据并插入到 MongoDB
sqlite_cursor.execute("SELECT * FROM book")  # 假设表名为 "book"
rows = sqlite_cursor.fetchall()
for row in rows:
    book_data = {
        'id': row[0],
        'title': row[1],
        'author': row[2],
        'price': row[3],
        # 添加其他字段...
    }
    books_collection.insert_one(book_data)

# 关闭连接
sqlite_conn.close()
mongo_client.close()