import subprocess
import time
import os
import sys
import signal

BACKEND_PORT = 8011
FRONTEND_PORT = 3000
processes = []

def kill_port(port):
    """杀掉占用指定端口的所有进程（包括孤儿进程）"""
    result = subprocess.run(
        'netstat -ano', shell=True, capture_output=True, text=True
    )
    pids = set()
    for line in result.stdout.splitlines():
        if f':{port} ' in line or f':{port}\t' in line:
            parts = line.strip().split()
            if parts:
                pid = parts[-1]
                if pid.isdigit() and pid != '0':
                    pids.add(pid)
    for pid in pids:
        r = subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True, text=True)
        if '成功' in r.stdout or 'SUCCESS' in r.stdout.upper():
            print(f"  已终止 PID {pid} (port {port})")
    if pids:
        time.sleep(1)

def start_services():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, 'backend')
    frontend_dir = os.path.join(base_dir, 'frontend')

    print(f"清理旧进程...")
    kill_port(BACKEND_PORT)
    kill_port(FRONTEND_PORT)

    print(f"启动后端服务 (port {BACKEND_PORT})...")
    backend = subprocess.Popen(
        ['python', 'run.py'],
        cwd=backend_dir,
        stdout=open(os.path.join(base_dir, 'backend.log'), 'w'),
        stderr=subprocess.STDOUT
    )
    processes.append(backend)
    time.sleep(2)

    print(f"启动前端服务 (port {FRONTEND_PORT})...")
    frontend = subprocess.Popen(
        ['python', '-m', 'http.server', str(FRONTEND_PORT)],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    processes.append(frontend)
    time.sleep(1)

    # 验证启动
    import urllib.request
    try:
        urllib.request.urlopen(f'http://127.0.0.1:{BACKEND_PORT}/all_blogs', timeout=5)
        backend_ok = True
    except:
        backend_ok = False

    try:
        urllib.request.urlopen(f'http://127.0.0.1:{FRONTEND_PORT}/', timeout=5)
        frontend_ok = True
    except:
        frontend_ok = False

    print("\n" + "="*50)
    print("系统启动状态：")
    print(f"  前端: http://localhost:{FRONTEND_PORT}  {'[OK]' if frontend_ok else '[FAIL]'}")
    print(f"  后端: http://localhost:{BACKEND_PORT}  {'[OK]' if backend_ok else '[FAIL]'}")
    print("="*50)
    print("\n按 Ctrl+C 停止所有服务")

    def shutdown(sig=None, frame=None):
        print("\n正在关闭所有服务...")
        for p in processes:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, shutdown)

    while True:
        if backend.poll() is not None:
            out, _ = backend.communicate() if backend.stdout else (b'', b'')
            print(f"\n警告：后端服务意外退出，请重新运行 start.py")
            shutdown()
        time.sleep(2)

if __name__ == "__main__":
    start_services()
