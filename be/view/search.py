# be/view/search.py
from flask import Blueprint, request, jsonify
from be.model.search import Search

bp_search = Blueprint("search", __name__, url_prefix="/search")

@bp_search.route("/books", methods=["POST"])
def search_books():
    keyword: str = request.json.get("keyword")
    store_id: str = request.json.get("store_id")
    page: int = request.json.get("page", 1)
    page_size: int = request.json.get("page_size", 20)
    
    s = Search()
    code, message, results = s.search_books(keyword, store_id, None, page, page_size)
    return jsonify({"message": message, "results": results}), code