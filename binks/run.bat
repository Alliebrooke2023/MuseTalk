@echo off
REM run.bat - start Binks on Windows (PowerShell/cmd)
cd /d "%~dp0"
python -m pip install -r requirements.txt >nul 2>&1
python binks.py serve --port %1
