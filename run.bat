@echo off
cd /d %~dp0
taskkill /f /im python.exe 2>nul
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload