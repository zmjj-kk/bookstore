import sys
import os

# 获取当前文件的绝对路径
current_file = os.path.abspath(__file__)
# 计算项目根目录（根据实际目录结构调整层级）
# 假设当前文件位于 "scripts/run.py"，则根目录是其上层目录
project_root = os.path.dirname(os.path.dirname(current_file))
# 将项目根目录添加到 Python 搜索路径（最前面，优先于其他路径）
sys.path.insert(0, project_root)

from be import serve

if __name__ == "__main__":
    serve.be_run()