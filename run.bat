@echo off
cd /d C:\Users\Parth\Desktop\sovereign-supply-chain-meta
taskkill /f /im python.exe 2>nul
python -m uvicorn vr_api:app --port 8502 --reload