#!/bin/bash
# 测试脚本：只执行测试并生成覆盖率报告

# 配置参数
export PYTHONPATH=$(pwd)
BACKEND_PORT=5000                  # 后端服务端口
BACKEND_LOG="backend.log"
HEALTH_CHECK_URL="http://localhost:$BACKEND_PORT/health"  # 假设后端提供健康检查接口
MAX_RETRIES=3

# 清理残留进程
cleanup() {
    if [ -n "$BACKEND_PID" ]; then
        if kill "$BACKEND_PID" 2>/dev/null; then
            echo "✅ 后端服务已停止 (PID: $BACKEND_PID)"
        fi
    fi
}

# 检查依赖
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ 缺少依赖: $1，请先安装"
        exit 1
    fi
}

# 健康检查接口
check_backend_health() {
    echo "⏳ 等待后端服务启动并检查健康状态..."
    for i in {1..20}; do
        # 健康检查接口
        if curl -s $HEALTH_CHECK_URL >/dev/null; then
            echo "✅ 后端服务启动并准备就绪"
            return 0
        fi
        if [ $i -eq 20 ]; then
            echo "❌ 后端服务启动失败，查看日志: tail -n 50 $BACKEND_LOG"
            return 1
        fi
        sleep 1
    done
}

# 捕获中断信号
trap cleanup EXIT INT TERM

# 1. 检查依赖
echo "🔍 检查依赖..."
check_dependency "python3"
check_dependency "coverage"
check_dependency "pytest"
check_dependency "curl"  # 新增：用于检查后端健康接口
echo "✅ 所有依赖已安装"

# 2. 检查后端健康状态
check_backend_health
if [ $? -ne 0 ]; then
    exit 1
fi

# 3. 执行测试并生成覆盖率报告
echo -e "\n🧪 执行测试并计算覆盖率..."
coverage run --timid --branch --source fe,be --concurrency=thread -m pytest -v --ignore=fe/data

if [ $? -eq 0 ]; then
    coverage combine
    echo -e "\n📊 覆盖率摘要："
    coverage report
    coverage html
    echo -e "\n✅ 测试完成！HTML覆盖率报告：htmlcov/index.html"
else
    echo -e "\n❌ 测试执行失败，请查看日志排查问题"
    exit 1
fi
