import logging
import os
from flask import Flask, Blueprint, request
from be.view import auth, seller, buyer, search
from be.model.store import init_database, init_completed_event


# 蓝图定义（保持功能不变，调整位置便于维护）
bp_shutdown = Blueprint("shutdown", __name__)

@bp_shutdown.route("/shutdown", methods=["POST"])  # 改为POST更安全，避免误触发
def be_shutdown():
    """关闭服务器接口"""
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Server not running with Werkzeug")
    func()
    return "Server shutting down..."


def be_run():
    """启动后端服务"""
    # 1. 路径与日志配置优化
    # 获取当前文件路径（be/serve.py），定位项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # 假设be/是项目子目录，根目录为其上层
    log_dir = os.path.join(project_root, "logs")  # 日志目录单独存放
    os.makedirs(log_dir, exist_ok=True)  # 确保日志目录存在
    log_file = os.path.join(log_dir, "app.log")

    # 2. 数据库初始化（等待初始化完成再启动服务）
    init_database("bookstore")
    if not init_completed_event.wait(timeout=10):  # 最多等待10秒，避免无限阻塞
        raise RuntimeError("Database initialization timed out")

    # 3. 日志配置增强（区分级别，格式化更清晰）
    logging.basicConfig(
        level=logging.INFO,  # 默认为INFO级别，比ERROR更实用（可捕获更多信息）
        format="%(asctime)s [%(threadName)s] [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),  # 日志文件（支持中文）
            logging.StreamHandler()  # 同时输出到控制台
        ]
    )
    logging.info("Starting backend server...")  # 增加启动日志，便于追踪

    # 4. Flask应用配置（增加端口和host参数，支持外部访问）
    app = Flask(__name__)
    # 注册蓝图
    app.register_blueprint(bp_shutdown)
    app.register_blueprint(auth.bp_auth)
    app.register_blueprint(seller.bp_seller)
    app.register_blueprint(buyer.bp_buyer)
    app.register_blueprint(search.bp_search)

    # 5. 启动服务（指定端口和host，便于脚本检测）
    # 端口与test.sh中的BACKEND_PORT保持一致（默认5000）
    app.run(
        host="0.0.0.0",  # 允许外部访问（如测试脚本）
        port=5000,
        debug=False  # 生产环境关闭debug模式（避免安全风险）
    )
    logging.info("Server stopped")