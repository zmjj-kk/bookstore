# be/model/search.py
import logging
from be.model import db_conn
from be.model import error
from pymongo.errors import PyMongoError

class Search(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def search_books(self, keyword: str, store_id: str = None, 
                    search_fields: list = None, page: int = 1, 
                    page_size: int = 20) -> (int, str, list):
        try:
            print(f"DEBUG search: Searching for '{keyword}' in store '{store_id}'")
            
            # 简单的关键词搜索实现（使用正则表达式）
            query = {
                "$or": [
                    {"title": {"$regex": keyword, "$options": "i"}},
                    {"author": {"$regex": keyword, "$options": "i"}},
                    {"publisher": {"$regex": keyword, "$options": "i"}},
                    {"tags": {"$regex": keyword, "$options": "i"}}
                ]
            }
            
            # 如果指定了店铺，只搜索该店铺的图书
            if store_id and store_id != "None":
                print(f"DEBUG search: Filtering by store {store_id}")
                if not self.store_id_exist(store_id):
                    return error.error_non_exist_store_id(store_id) + ([],)
                
                # 获取店铺中的图书ID
                store_books = self.db.store.find(
                    {"store_id": store_id}, 
                    {"book_id": 1}
                )
                book_ids = [book["book_id"] for book in store_books]
                query["id"] = {"$in": book_ids}
                print(f"DEBUG search: Store has {len(book_ids)} books")

            # 执行搜索
            skip = (page - 1) * page_size
            cursor = self.db.books.find(query).skip(skip).limit(page_size)
            total_count = self.db.books.count_documents(query)
            
            print(f"DEBUG search: Found {total_count} total matches")

            results = []
            for book in cursor:
                # 获取图书在指定店铺的库存信息
                stock_info = {}
                if store_id and store_id != "None":
                    store_item = self.db.store.find_one({
                        "store_id": store_id,
                        "book_id": book.get("id")
                    })
                    if store_item:
                        stock_info = {
                            "stock_level": store_item.get("stock_level", 0),
                            "store_price": store_item.get("price", book.get("price", 0))
                        }
                
                result_item = {
                    "book_id": book.get("id", ""),
                    "title": book.get("title", ""),
                    "author": book.get("author", ""),
                    "publisher": book.get("publisher", ""),
                    "price": book.get("price", 0),
                    "book_intro": book.get("book_intro", "")[:100] + "..." if book.get("book_intro") else "",
                    "tags": book.get("tags", [])
                }
                result_item.update(stock_info)
                results.append(result_item)

            print(f"DEBUG search: Returning {len(results)} results")
            return 200, "ok", results

        except PyMongoError as e:
            logging.error(f"MongoDB error in search_books: {e}")
            return 528, "{}".format(str(e)), []
        except Exception as e:
            logging.error(f"Unexpected error in search_books: {e}")
            return 530, "{}".format(str(e)), []