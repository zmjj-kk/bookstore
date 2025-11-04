# debug_ship_api.py
import requests
import json
from fe.access.new_seller import register_new_seller
from fe.access.new_buyer import register_new_buyer
from fe.access.book import Book
import uuid

def debug_ship_api():
    print("=== Debug Ship API ===")
    
    # 创建测试数据
    seller_id = "debug_seller_" + str(uuid.uuid1())
    buyer_id = "debug_buyer_" + str(uuid.uuid1())
    store_id = "debug_store_" + str(uuid.uuid1())
    password = "password"
    
    seller = register_new_seller(seller_id, password)
    buyer = register_new_buyer(buyer_id, password)
    
    # 创建店铺和图书
    seller.create_store(store_id)
    
    test_book = Book()
    test_book.id = "debug_book_001"
    test_book.title = "调试图书"
    test_book.price = 100
    
    seller.add_book(store_id, 10, test_book)
    
    # 创建订单
    book_ids = [(test_book.id, 1)]
    code, order_id = buyer.new_order(store_id, book_ids)
    print(f"Create order: {code}, {order_id}")
    
    # 付款
    buyer.add_funds(1000)
    code = buyer.payment(order_id)
    print(f"Payment: {code}")
    
    # 测试发货接口
    if hasattr(seller, 'ship_books'):
        print("Testing ship_books method...")
        code = seller.ship_books(store_id, order_id)
        print(f"Ship books result: {code}")
        
        if code == 404:
            print("❌ 发货接口返回404，说明后端路由没有正确注册")
        elif code == 200:
            print("✅ 发货接口正常工作")
        else:
            print(f"⚠️ 发货接口返回其他错误: {code}")
    else:
        print("❌ seller.ship_books 方法不存在")
    
    print("=== Debug Complete ===")

if __name__ == "__main__":
    debug_ship_api()