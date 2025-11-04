# fe/access/mongo_book.py
import random
import base64
from be.model.store import get_db_conn

class MongoBook:
    def __init__(self):
        self.id = ""
        self.title = ""
        self.author = ""
        self.publisher = ""
        self.original_title = ""
        self.translator = ""
        self.pub_year = ""
        self.pages = 0
        self.price = 0
        self.currency_unit = ""
        self.binding = ""
        self.isbn = ""
        self.author_intro = ""
        self.book_intro = ""
        self.content = ""
        self.tags = []
        self.pictures = []

class MongoBookDB:
    def __init__(self):
        self.db = get_db_conn()

    def get_book_count(self):
        try:
            return self.db.books.count_documents({})
        except Exception as e:
            print(f"Error getting book count: {e}")
            return 0

    def get_book_info(self, start, size):
        books = []
        try:
            cursor = self.db.books.find().skip(start).limit(size)
            
            for doc in cursor:
                book = MongoBook()
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
                
                # 处理tags
                tags = doc.get("tags", [])
                if isinstance(tags, list):
                    book.tags = tags
                else:
                    book.tags = [tags] if tags else []
                
                book.pictures = []
                books.append(book)
            
            print(f"Retrieved {len(books)} books from MongoDB")
            return books
            
        except Exception as e:
            print(f"Error getting book info: {e}")
            return []

    def get_book_by_id(self, book_id: str) -> MongoBook:
        doc = self.db.books.find_one({"id": book_id})
        if not doc:
            return None
            
        book = MongoBook()
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
        
        # 处理tags
        tags = doc.get("tags", [])
        if isinstance(tags, list):
            book.tags = tags
        else:
            book.tags = [tags] if tags else []
            
        return book