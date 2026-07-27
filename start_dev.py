import subprocess
import time
import webbrowser
import os
import sys

def main():
    print("=" * 60)
    print("AI Shop Analyzer - 一键启动脚本")
    print("=" * 60)

    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")

    print("\n1. 检查并安装后端依赖...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        print("   ✓ 后端依赖安装完成")
    except Exception as e:
        print(f"   ⚠️  依赖安装可能需要手动处理: {e}")

    print("\n2. 启动后端服务...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print("   等待后端启动...")
    time.sleep(5)

    print("\n3. 安装前端依赖...")
    try:
        subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=300
        )
        print("   ✓ 前端依赖安装完成")
    except Exception as e:
        print(f"   ⚠️  前端依赖安装失败: {e}")

    print("\n4. 启动前端服务...")
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print("\n5. 等待服务就绪...")
    time.sleep(3)

    print("\n6. 打开浏览器...")
    webbrowser.open("http://localhost:3000")

    print("\n" + "=" * 60)
    print("服务已启动！")
    print(f"后端 API: http://localhost:8000")
    print(f"前端页面: http://localhost:3000")
    print("=" * 60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n正在停止服务...")
        backend_process.terminate()
        frontend_process.terminate()
        print("服务已停止")

if __name__ == "__main__":
    main()