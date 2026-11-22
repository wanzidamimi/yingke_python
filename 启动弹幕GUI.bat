@echo off
cd /d "%~dp0"
echo Installing dependencies if needed...
python -m pip install -r requirements.txt
echo Starting server at http://127.0.0.1:8801
start "" http://127.0.0.1:8801
python -m uvicorn app:app --host 127.0.0.1 --port 8801
pause
