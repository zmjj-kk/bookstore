# be/model/order_cleanup.py
import threading
import time
from datetime import datetime, timedelta
from be.model import db_conn
from pymongo.errors import PyMongoError

class OrderCleanup(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)
        self.running = False
        self.thread = None

    def start_cleanup(self, interval=300):  # 5分钟检查一次
        """启动订单自动取消任务"""
        self.running = True
        self.thread = threading.Thread(target=self._cleanup_loop, args=(interval,))
        self.thread.daemon = True
        self.thread.start()

    def stop_cleanup(self):
        """停止订单自动取消任务"""
        self.running = False
        if self.thread:
            self.thread.join()

    def _cleanup_loop(self, interval):
        """订单清理循环"""
        while self.running:
            try:
                self._cancel_timeout_orders()
                time.sleep(interval)
            except Exception as e:
                print(f"Order cleanup error: {e}")

    def _cancel_timeout_orders(self):
        """取消超时未付款的订单"""
        try:
            # 查找创建时间超过30分钟且状态为pending的订单
            timeout_time = datetime.now() - timedelta(minutes=30)
            
            timeout_orders = self.db.orders.find({
                "status": "pending",
                "create_time": {"$lt": timeout_time}
            })

            for order in timeout_orders:
                order_id = order["order_id"]
                user_id = order["user_id"]
                store_id = order["store_id"]

                # 恢复库存
                order_details = self.db.order_details.find({"order_id": order_id})
                for detail in order_details:
                    self.db.store.update_one(
                        {
                            "store_id": store_id,
                            "book_id": detail["book_id"]
                        },
                        {"$inc": {"stock_level": detail["count"]}}
                    )

                # 更新订单状态为已取消
                self.db.orders.update_one(
                    {"order_id": order_id},
                    {"$set": {"status": "cancelled", "cancel_reason": "timeout"}}
                )

                print(f"Cancelled timeout order: {order_id}")

        except PyMongoError as e:
            print(f"MongoDB error in order cleanup: {e}")