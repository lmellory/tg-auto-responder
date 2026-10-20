@echo off
chcp 65001 > nul
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -X utf8 login.py
) else (
    python -X utf8 login.py
)
pause
