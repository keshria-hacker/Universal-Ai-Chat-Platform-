#!/usr/bin/env python3
"""
Debug version of start.py that shows better error messages.
This script will help diagnose why start.py might be crashing.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
VENV_DIR = ROOT / "venv"

print("=" * 60)
print("Universal AI Chat Platform - Debug Start")
print("=" * 60)

# Step 1: Check if venv exists
print("\n[1/6] Checking virtual environment...")
if not VENV_DIR.exists():
    print("  [ERROR] Virtual environment not found at:", VENV_DIR)
    print("  --> Run: python -m venv venv")
    sys.exit(1)
print("  [OK] Virtual environment exists")

# Step 2: Check Python executable
python_exe = str(VENV_DIR / "Scripts" / "python.exe") if os.name == "nt" else str(VENV_DIR / "bin" / "python")
print("\n[2/6] Checking Python executable:", python_exe)
if not Path(python_exe).exists():
    print("  [ERROR] Python executable not found")
    print("  --> Virtual environment may be corrupted")
    print("  --> Delete 'venv' directory and run: python -m venv venv")
    sys.exit(1)
print("  [OK] Python executable found")

# Step 3: Check if requirements are installed
print("\n[3/6] Checking dependencies...")
try:
    result = subprocess.run(
        [python_exe, "-c", "import uvicorn; import fastapi; import sqlite3"],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        print("  [ERROR] Missing dependencies")
        print("  --> Error:", result.stderr)
        print("  --> Run: pip install -r requirements.txt")
        sys.exit(1)
    print("  [OK] Core dependencies installed")
except Exception as e:
    print("  [ERROR] Error checking dependencies:", str(e))
    sys.exit(1)

# Step 4: Check .env file
print("\n[4/6] Checking .env file...")
env_file = ROOT / ".env"
if not env_file.exists():
    print("  [ERROR] .env file not found")
    print("  --> Copy .env.example to .env")
    print("  --> Generate MASTER_KEY with: python scripts/generate_master_key.py")
    sys.exit(1)

# Check for MASTER_KEY
env_content = env_file.read_text()
if "MASTER_KEY=" not in env_content:
    print("  [ERROR] MASTER_KEY not found in .env")
    print("  --> Generate one with: python scripts/generate_master_key.py")
    print("  --> Add to .env: MASTER_KEY=your_generated_key_here")
    sys.exit(1)
print("  [OK] .env file is valid")

# Step 5: Try starting backend manually
print("\n[5/6] Testing backend startup...")
print("  Running: uvicorn main:app --host 127.0.0.1 --port 8001")
print("  (This will take a few seconds...)")

backend_proc = subprocess.Popen(
    [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001"],
    cwd=BACKEND_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

# Wait for backend to start or fail
time.sleep(3)

if backend_proc.poll() is not None:
    # Backend crashed
    stdout, stderr = backend_proc.communicate()
    print("  [ERROR] Backend crashed!")
    print("\n  --- STDOUT ---")
    print(stdout)
    print("\n  --- STDERR ---")
    print(stderr)
    print("\n  Common fixes:")
    print("    • Run: pip install -r requirements.txt")
    print("    • Check .env file has MASTER_KEY")
    print("    • Delete history/nexus.db if corrupted")
    sys.exit(1)
else:
    print("  [OK] Backend started successfully!")
    print("  --> Backend running at: http://127.0.0.1:8001/docs")

    # Test backend health
    try:
        import urllib.request
        response = urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=2)
        if response.status == 200:
            print("  [OK] Backend health check passed")
        else:
            print(f"  [WARN]  Backend returned status: {response.status}")
    except Exception as e:
        print(f"  [WARN]  Could not connect to backend: {e}")

    backend_proc.terminate()
    backend_proc.wait()

# Step 6: Try starting frontend manually
print("\n[6/6] Testing frontend startup...")
print("  Running: python -m http.server 5500")

frontend_proc = subprocess.Popen(
    [python_exe, "-m", "http.server", "5500"],
    cwd=FRONTEND_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

time.sleep(2)

if frontend_proc.poll() is not None:
    stdout, stderr = frontend_proc.communicate()
    print("  [ERROR] Frontend crashed!")
    print("\n  --- STDOUT ---")
    print(stdout)
    print("\n  --- STDERR ---")
    print(stderr)
    sys.exit(1)
else:
    print("  [OK] Frontend started successfully!")
    print("  --> Frontend running at: http://127.0.0.1:5500")
    frontend_proc.terminate()
    frontend_proc.wait()

print("\n" + "=" * 60)
print("[OK] All checks passed!")
print("=" * 60)
print("\nYou can now run the full application with:")
print("  python start.py")
print("\nOr start servers manually:")
print("  Backend:  cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8001")
print("  Frontend: cd frontend && python -m http.server 5500")
