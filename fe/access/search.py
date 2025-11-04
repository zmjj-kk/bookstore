# fe/access/search.py
import requests
from urllib.parse import urljoin

class Search:
    def __init__(self, url_prefix):
        self.url_prefix = urljoin(url_prefix, "search/")

    def search_books(self, keyword: str, store_id: str = None, page: int = 1, page_size: int = 20):
        json = {
            "keyword": keyword,
            "store_id": store_id,
            "page": page,
            "page_size": page_size
        }
        url = urljoin(self.url_prefix, "books")
        try:
            r = requests.post(url, json=json, timeout=10)
            if r.status_code == 200:
                return r.status_code, r.json().get("message", ""), r.json().get("results", [])
            else:
                return r.status_code, r.text, []
        except Exception as e:
            return 500, str(e), []