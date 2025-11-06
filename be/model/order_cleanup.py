import threading
import time
from datetime import datetime, timedelta
import sqlite3
from be.model import db_conn
from be.model import error


class OrderCleanup(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)
        self.running = False
        self.thread = None
        # 超时时间设置为30分钟（单位：秒）
        self.timeout_seconds = 1800

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
            # 计算超时时间点
            timeout_time = datetime.now() - timedelta(seconds=self.timeout_seconds)
            timeout_timestamp = timeout_time.strftime('%Y-%m-%d %H:%M:%S')

            # 开启事务
            self.conn.execute("BEGIN")

            # 查找超时未付款的订单（假设新增了create_time和status字段）
            cursor = self.conn.execute(
                "SELECT order_id, user_id, store_id FROM new_order "
                "WHERE status = 'pending' AND create_time < ?",
                (timeout_timestamp,)
            )
            timeout_orders = cursor.fetchall()

            for order in timeout_orders:
                order_id, user_id, store_id = order

                # 恢复库存
                detail_cursor = self.conn.execute(
                    "SELECT book_id, count FROM new_order_detail WHERE order_id = ?",
                    (order_id,)
                )
                details = detail_cursor.fetchall()
                for book_id, count in details:
                    self.conn.execute(
                        "UPDATE store SET stock_level = stock_level + ? "
                        "WHERE store_id = ? AND book_id = ?",
                        (count, store_id, book_id)
                    )

                # 更新订单状态为已取消
                self.conn.execute(
                    "UPDATE new_order SET status = 'cancelled', cancel_reason = 'timeout' "
                    "WHERE order_id = ?",
                    (order_id,)
                )

                print(f"Cancelled timeout order: {order_id}")

            # 提交事务
            self.conn.commit()

        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"SQLite error in order cleanup: {e}")
        except Exception as e:
            self.conn.rollback()
            print(f"Unexpected error in order cleanup: {e}")