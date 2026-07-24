@echo off
REM One-command start: sets up the backend venv, installs deps, creates .env
REM if missing, then runs the FastAPI backend AND serves the frontend.
cd /d "%~dp0"

python start.py
