@echo off
color 0A
cls
echo ============================================================
echo Universal AI Chat Platform - Starting...
echo ============================================================
echo.
echo This window will stay open while the servers are running.
echo Press Ctrl+C to stop the servers and close this window.
echo.
echo Starting backend and frontend servers...
echo.

cd /d "%~dp0"

REM Start the Python application
python start.py

echo.
echo Servers stopped.
echo You can close this window now.
pause