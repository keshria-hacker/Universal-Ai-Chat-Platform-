# Troubleshooting Guide

## 🚀 How to Start the Application

### Method 1: Using run.bat (Recommended for Windows)

Simply double-click `run.bat` in the project folder. This will:
- Open a command window that stays visible
- Start both backend and frontend servers
- Show server logs in real-time
- Keep running until you press Ctrl+C

### Method 2: Using start.py from Command Line

Open Command Prompt or PowerShell and run:

```bash
cd "D:/chat apps/Universal-Ai-Chat-Platform--main"
python start.py
```

The application will start and keep running. Press **Ctrl+C** to stop it.

### Method 3: Start Servers Manually

If you want to start servers separately:

**Backend (API Server):**
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

**Frontend (Web Server):**
```bash
cd frontend
python -m http.server 5500
```

## ❌ Common Issues and Fixes

### Issue 1: Window opens and closes immediately

**Cause:** You're double-clicking `start.py` which runs and exits immediately.

**Solution:** 
- Use `run.bat` instead (double-click it)
- OR open Command Prompt first, then run `python start.py`

### Issue 2: Port already in use

**Error:** `OSError: [WinError 10048] Only one usage of each socket address is normally permitted`

**Solution:**
```bash
# Find and kill the process using the port
netstat -ano | findstr :8001
taskkill /PID <PID> /F

# Then restart the application
python start.py
```

### Issue 3: Missing dependencies

**Error:** `ModuleNotFoundError: No module named 'fastapi'` or similar

**Solution:**
```bash
# Make sure you're in the project directory
cd "D:/chat apps/Universal-Ai-Chat-Platform--main"

# Install dependencies
python -m pip install -r requirements.txt
```

### Issue 4: Missing MASTER_KEY

**Error:** `ERROR: Missing required setting(s) in .env: MASTER_KEY`

**Solution:**
```bash
# Generate a master key
python scripts/generate_master_key.py

# Copy the generated key and add it to .env
# The file should have a line like:
MASTER_KEY=nIYa_omqHkTvtczuKJAz3S4qnomG-Rz71W6bRwSOHPw=
```

### Issue 5: Database errors

**Error:** `sqlite3.OperationalError: no such table: users` or similar

**Solution:**
```bash
# Delete the corrupted database file
rmdir /s /q history
mkdir history

# Restart the application
python start.py
```

### Issue 6: Python version issues

**Error:** `SyntaxError: invalid syntax` or similar

**Solution:**
- This project requires **Python 3.11 or 3.12**
- Check your Python version: `python --version`
- If you have an older version, download and install Python 3.12 from [python.org](https://www.python.org/downloads/)

### Issue 7: Virtual environment issues

**Error:** `No module named 'uvicorn'` even after installing

**Solution:**
```bash
# Delete the virtual environment
rmdir /s /q venv

# Create a new one
python -m venv venv

# Activate it and install dependencies
venv\Scripts\activate
pip install -r requirements.txt
```

### Issue 8: Browser doesn't open automatically

**Cause:** The application waits for both servers to be fully ready before opening the browser.

**Solution:**
- Wait 10-15 seconds for servers to start
- OR manually open: [http://localhost:5500](http://localhost:5500)

### Issue 9: CORS errors in browser

**Error:** `Access to fetch at 'http://127.0.0.1:8001/api/...' from origin 'http://localhost:5500' has been blocked by CORS policy`

**Solution:**
- Make sure you're using `http://127.0.0.1:5500` (not `localhost:5500`)
- The backend is configured to accept requests from `127.0.0.1:5500`

### Issue 10: Application runs but nothing works

**Checklist:**
1. ✅ Backend is running: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)
2. ✅ Frontend is running: [http://127.0.0.1:5500](http://127.0.0.1:5500)
3. ✅ .env file has MASTER_KEY
4. ✅ No errors in the command window
5. ✅ You're using the correct URLs (127.0.0.1, not localhost)

## 🔍 Debugging Steps

### Step 1: Run the debug script

```bash
python start_debug.py
```

This will test each component and tell you exactly what's wrong.

### Step 2: Check server logs

When running `start.py`, you should see logs like:

```
=== UniversalAI — starting ===
-> Backend: http://127.0.0.1:8001/docs
-> Frontend: http://127.0.0.1:5500
INFO:     Started server process [1234]
INFO:     Uvicorn running on http://127.0.0.1:8001
```

If you see error messages, they will be in **red** and clearly indicate what's wrong.

### Step 3: Test endpoints manually

**Backend health:**
```bash
curl http://127.0.0.1:8001/health
```

**Frontend:**
```bash
curl http://127.0.0.1:5500
```

### Step 4: Check ports

```bash
# Check if ports are in use
netstat -ano | findstr "8001\|5500"
```

### Step 5: Enable debug mode

Edit `.env` and set:
```
APP_DEBUG=true
```

This will show more detailed error messages.

## 📚 Common Windows-Specific Issues

### Windows Defender/Firewall blocking

**Symptoms:** Servers start but can't connect

**Solution:**
1. Allow Python through Windows Defender Firewall
2. Or temporarily disable firewall for testing

### Antivirus blocking

**Symptoms:** Application crashes silently

**Solution:**
- Add exception for the project folder in your antivirus
- Or temporarily disable real-time protection

### Path too long

**Symptoms:** Errors about path length

**Solution:**
- Move the project to `C:\ai-chat` (shorter path)
- Or enable long paths in Windows: `reg edit` for LongPathsEnabled

### Python not in PATH

**Symptoms:** `python` command not found

**Solution:**
1. Reinstall Python and check "Add to PATH"
2. OR use full path: `C:\Python312\python.exe start.py`

## 🎯 Quick Start Checklist

Before asking for help, verify:

- [ ] Python 3.11 or 3.12 is installed
- [ ] You're in the correct directory: `D:\chat apps\Universal-Ai-Chat-Platform--main`
- [ ] Virtual environment exists: `venv\` folder is present
- [ ] Dependencies installed: `pip install -r requirements.txt` was run
- [ ] .env file exists and has MASTER_KEY
- [ ] No other application is using ports 8001 or 5500
- [ ] You're running from Command Prompt, not double-clicking start.py

## 🆘 Still Having Issues?

Run the debug script and share the output:

```bash
python start_debug.py > debug_output.txt 2>&1
```

Then check `debug_output.txt` and share its contents when asking for help.

## 📞 Support

For additional help:
1. Check the full documentation in `README.md`
2. Review the architecture in `ARCHITECTURE.md`
3. Run `python start_debug.py` for automated diagnostics
4. Check the GitHub issues for known problems
