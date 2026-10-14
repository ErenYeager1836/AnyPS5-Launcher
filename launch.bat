@echo off
title AnyPS5 Launcher Hub
echo ====================================================================
echo        AnyPS5 Launcher - Next-Gen PlayStation 5 Companion Hub
echo ====================================================================
echo.
echo Checking Python environment...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python 3 is not found in PATH!
    echo Please install Python from https://python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

echo Launching companion daemon on http://localhost:8085...
timeout /t 1 /nobreak >nul
start "" "http://localhost:8085"
python launcher.py
