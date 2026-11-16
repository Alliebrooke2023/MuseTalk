@echo off
REM Binks.bat - double-click to launch Binks as a local app (Windows)
cd /d "%~dp0"
python -m pip install -r requirements.txt >nul 2>&1
python binks.py start
pause
