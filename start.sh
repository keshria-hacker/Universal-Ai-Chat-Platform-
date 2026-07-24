#!/usr/bin/env bash
# One-command start: sets up the backend venv, installs deps, creates .env
# if missing, then runs the FastAPI backend AND serves the frontend.
set -e
cd "$(dirname "$0")"

python3 start.py
