import logging
from be.model import db_conn
from be.model import error
from pymongo.errors import PyMongoError
from pymongo import TEXT


class Search(db_conn.DBConn):
    def __init__(self):
        super().__init__()
        # 初始化全文索引（仅首次运行时创建，重复调用会忽略）
        self._create_text_index()

    def _create_text_index(self):
        """为图书集合创建全文索引，优化搜索性能"""
        try:
            self.db.books.create_index(
                [
                    ("title", TEXT),
                    ("author", TEXT),
                    ("publisher", TEXT),
                    ("tags", TEXT),
                    ("book_intro", TEXT)
                ],
                name="book_text_index",
                default_language="english"
            )
        except PyMongoError as e:
            logging.warning(f"全文索引创建失败（可能已存在）: {e}")

    def search_books(self, 
                    keyword: str, 
                    store_id: str = None, 
                    search_fields: list = None, 
                    page: int = 1, 
                    page_size: int = 20) -> (int, str, list):
        """
        搜索图书
        :param keyword: 搜索关键词
        :param store_id: 可选，指定店铺ID
        :param search_fields: 可选，指定搜索字段（如["title", "author"]）
        :param page: 页码，默认1
        :param page_size: 每页数量，默认20
        :return: 状态码、消息、图书列表
        """
        try:
            # 验证分页参数
            if page < 1 or page_size < 1:
                return error.error_invalid_parameter("page or page_size") + ([],)

            # 构建基础查询
            if search_fields:
                # 按指定字段搜索（正则匹配，不区分大小写）
                query_conditions = []
                for field in search_fields:
                    if field not in ["title", "author", "publisher", "tags", "book_intro"]:
                        return error.error_invalid_parameter(f"invalid field: {field}") + ([],)
                    query_conditions.append({
                        field: {"$regex": keyword, "$options": "i"}
                    })
                query = {"$or": query_conditions}
            else:
                # 全文索引搜索（更高效）
                query = {"$text": {"$search": keyword}}

            # 店铺过滤
            store_book_ids = None
            if store_id:
                if not self.store_id_exist(store_id):
                    return error.error_non_exist_store_id(store_id) + ([],)
                
                # 获取店铺内所有图书ID
                store_books = self.db.store.find(
                    {"store_id": store_id}, 
                    {"book_id": 1, "_id": 0}
                )
                store_book_ids = [book["book_id"] for book in store_books]
                if not store_book_ids:
                    return 200, "ok", []  # 店铺无图书
                query["id"] = {"$in": store_book_ids}

            # 执行查询（带分页）
            skip = (page - 1) * page_size
            cursor = self.db.books.find(query).skip(skip).limit(page_size)
            total_count = self.db.books.count_documents(query)

            # 处理结果
            results = []
            for book in cursor:
                book_info = {
                    "book_id": book.get("id", ""),
                    "title": book.get("title", ""),
                    "author": book.get("author", ""),
                    "publisher": book.get("publisher", ""),
                    "price": book.get("price", 0),
                    "book_intro": book.get("book_intro", "")[:150] + "..." 
                                  if book.get("book_intro") else "",
                    "tags": book.get("tags", []),
                    "total_matches": total_count  # 总匹配数，用于前端分页
                }

                # 添加店铺库存信息（如果指定了店铺）
                if store_id and store_book_ids:
                    store_item = self.db.store.find_one(
                        {"store_id": store_id, "book_id": book["id"]},
                        {"stock_level": 1, "_id": 0}
                    )
                    if store_item:
                        book_info["stock_level"] = store_item.get("stock_level", 0)

                results.append(book_info)

            return 200, "ok", results

        except PyMongoError as e:
            logging.error(f"MongoDB搜索错误: {str(e)}")
            return error.error_database_error(str(e)) + ([],)
        except Exception as e:
            logging.error(f"搜索异常: {str(e)}")
            return 530, str(e), []