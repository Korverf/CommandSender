@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo   CommandSender Build Script
echo ============================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install pyautogui pyperclip pywin32 pyinstaller -q

echo [2/3] Building...
python -m PyInstaller --onefile --windowed --name "CommandSender" --clean command_sender.py

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo ============================================
echo Output: dist\CommandSender.exe
echo.
pause
