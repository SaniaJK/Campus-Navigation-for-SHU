import subprocess
import sys
import os
import time
import webbrowser
import threading
import requests 


SUBPROCESS_FLAG = "NAV_RECURSION_CHECK"

if os.environ.get(SUBPROCESS_FLAG) == "1":
    sys.exit(0)


# --- 1. 核心路径配置 ---
# 地图数据文件名称 (与项目根目录下的文件名称一致)
MAP_FILE_NAME = "backend/map_test.osm" 
BACKEND_SCRIPT_NAME = "app.py" 
FRONTEND_FILE_NAME = "index.html"

# 获取脚本所在的目录 (即 backend/ 目录)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) 

# 假设 startup.py 位于 backend/ 目录下，项目根目录是上级目录
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) 

# 使用绝对路径来定位核心文件
# 注意：我们现在使用绝对路径
BACKEND_SCRIPT = os.path.join(SCRIPT_DIR, BACKEND_SCRIPT_NAME) # app.py 在 backend 目录下
FRONTEND_FILE = os.path.join(PROJECT_ROOT, "frontend", FRONTEND_FILE_NAME) # index.html 在 frontend 目录下
MAP_FILE = os.path.join(PROJECT_ROOT, MAP_FILE_NAME) # map_1.osm 在项目根目录下

# Flask 默认运行地址和端口
FLASK_URL = "http://127.0.0.1:5000"

# 依赖库列表
REQUIRED_PACKAGES = ['flask', 'requests', 'lxml'] 
# -------------------------

def check_and_install_dependencies():
    """ 检查并安装所需的 Python 库 """
    print(">>> 检查并安装依赖库...")
    try:
        # 使用 pip install --upgrade 确保依赖存在且是最新版本
        print("尝试安装/更新依赖...")

        env = os.environ.copy()
        env[SUBPROCESS_FLAG] = "1"


        # 注意: 如果用户环境没有管理员权限，这可能会失败。但这是最标准的一键安装方式。
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade"] + REQUIRED_PACKAGES,
            env=env # 将环境传递给子进程
        )
        print(">>> 依赖库安装成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"错误: 无法安装依赖库。请确保 'pip' 可用且网络连接正常。错误信息: {e}")
        return False
    except FileNotFoundError:
        print("错误: 找不到 Python 解释器或 pip。")
        return False

def check_prerequisites():
    """ 检查前置文件是否存在 """
    print(">>> 检查前置文件...")
    
    if not os.path.exists(MAP_FILE):
        print(f"❌ 错误: 找不到核心地图文件 {MAP_FILE}。程序无法启动。")
        print(f"请确保文件 {MAP_FILE_NAME} 位于项目根目录: {PROJECT_ROOT}")
        return False
    if not os.path.exists(BACKEND_SCRIPT):
        print(f"❌ 错误: 找不到后端启动文件 {BACKEND_SCRIPT}。")
        return False
    if not os.path.exists(FRONTEND_FILE):
        print(f"⚠️ 警告: 找不到前端文件 {FRONTEND_FILE}。后端仍会启动。")
        
    print(">>> 前置文件检查通过。")
    return True

def start_backend():
    """ 在后台线程启动 Flask 应用 """
    print(">>> 正在启动 Flask 后端...")
    
    python_path = sys.executable
    
    def run_flask():
        global flask_process
        try:
            # 🚀 关键：设置 CWD 为项目根目录，确保 app.py 能找到 map_1.osm
            flask_process = subprocess.Popen(
                [python_path, BACKEND_SCRIPT], 
                cwd=PROJECT_ROOT, # 设置工作目录为项目根目录
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            print(f"Flask 进程 ID: {flask_process.pid}")
            # 实时打印 Flask 的错误输出，方便调试
            for line in iter(flask_process.stderr.readline, ''):
                if line:
                    print(f"[Flask-Error] {line.strip()}")
                if flask_process.poll() is not None:
                    break
        except Exception as e:
            print(f"启动 Flask 失败: {e}")
            
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True 
    flask_thread.start()
    
    return True

def wait_for_backend():
    """ 尝试连接后端，直到服务启动 """
    max_retries = 30 # 最多等待 30 秒
    print(">>> 正在等待后端服务启动...")
    for i in range(max_retries):
        try:
            # 尝试访问 Flask 端点
            response = requests.get(f"{FLASK_URL}/api/locations", timeout=5) 
            # 只要能收到响应，就认为服务已启动
            if response.status_code == 200 or response.status_code == 404: 
                print(f">>> 后端服务已启动 ({FLASK_URL})!")
                return True
        except requests.exceptions.ConnectionError:
            print(f"   [尝试 {i+1}/{max_retries}] 仍在等待...")
            time.sleep(1)
        except Exception as e:
            print(f"连接检查中发生意外错误: {e}")
            break
            
    print("❌ 错误: 无法连接到后端服务。启动失败。")
    return False

def open_frontend():
    """ 启动前端界面 """
    abs_path = os.path.abspath(FRONTEND_FILE)
    print(f">>> 正在启动浏览器打开前端界面: file:///{abs_path}")
    webbrowser.open(f"file:///{abs_path}")

def main():
    print("--- 校园路径漫游导航启动程序 ---")
    
    if not check_and_install_dependencies():
        input("\n按任意键退出...")
        return
        
    if not check_prerequisites():
        input("\n按任意键退出...")
        return

    if not start_backend():
        input("\n按任意键退出...")
        return
        
    if not wait_for_backend():
        print("后端启动失败，正在尝试终止 Flask 进程...")
        if 'flask_process' in globals() and flask_process.poll() is None:
            flask_process.terminate() 
        input("\n按任意键退出...")
        return

    open_frontend()
    
    print("\n=======================================================")
    print(">>> 启动成功! 请勿关闭此终端窗口，否则后端服务将停止。")
    print("=======================================================")
    
    try:
        while True:
            time.sleep(10) # 保持主进程运行
    except:
        pass

    print(">>> 正在终止 Flask 进程...")
    if 'flask_process' in globals() and flask_process.poll() is None:
        flask_process.terminate()

if __name__ == "__main__":
    flask_process = None 
    main()