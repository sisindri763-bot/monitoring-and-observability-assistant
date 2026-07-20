"""
MONITORING API + TUSK COPILOT — Start Script
Launches the FastAPI backend server.
Run from: d:\projects\monitoring_api\
"""

import subprocess
import sys
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(BASE, "monitoring_pipelines")

processes = []


def start_all():
    print("\n" + "=" * 55)
    print("  MONITORING API + TUSK COPILOT -- Starting Up")
    print("=" * 55 + "\n")

    print("  >> Starting: FastAPI Server (Tusk Backend)")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app:app", 
            "--reload", 
            "--reload-dir", API_DIR, 
            "--reload-dir", os.path.join(BASE, "ai"), 
            "--port", "8000"
        ],
        cwd=API_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(("FastAPI Server", proc))

    print("\n" + "=" * 55)
    print("  [OK] Server starting...")
    print("  [API] http://127.0.0.1:8000")
    print("  [DOC] http://127.0.0.1:8000/docs")
    print("  [AI]  POST /agents/copilot  (Tusk Copilot)")
    print("=" * 55)
    print("\n  Press Ctrl+C to stop.\n")

    try:
        while True:
            for name, proc in processes:
                line = proc.stdout.readline()
                if line:
                    print(f"[{name[:22]:22}] {line.rstrip()}")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n\nStopping server...\n")
        for name, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  [OK] Stopped: {name}")
            except Exception:
                proc.kill()
        print("\nGoodbye!\n")
        sys.exit(0)


if __name__ == "__main__":
    start_all()
