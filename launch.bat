@echo off
title AnyPS5 Launcher
cd /d "%~dp0"

echo ====================================================================
echo        AnyPS5 Launcher - Standalone Desktop Application
echo ====================================================================
echo.

if exist "AnyPS5Launcher.exe" (
    echo Launching native desktop application window...
    start "" "AnyPS5Launcher.exe"
    exit /b 0
)

echo Starting launcher with standalone application window...
python launcher.py
