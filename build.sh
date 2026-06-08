#!/bin/bash
# =============================================
#   CommandSender Build Script (Linux/Ubuntu)
# =============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  CommandSender Build Script (Ubuntu 22.04)"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found!"
    echo "Please install: sudo apt install python3 python3-pip"
    exit 1
fi

echo "[1/4] Checking system dependencies..."
# Check for tkinter
python3 -c "import tkinter" 2>/dev/null || {
    echo "[WARN] tkinter not found, installing python3-tk..."
    sudo apt-get install -y python3-tk
}

# Check for xdotool (required for Linux window management)
if ! command -v xdotool &> /dev/null; then
    echo "[WARN] xdotool not found, installing..."
    sudo apt-get install -y xdotool
fi

echo "[2/4] Installing Python dependencies..."
pip3 install pyautogui pyperclip pyinstaller -q --break-system-packages

echo "[3/4] Building executable..."
python3 -m PyInstaller --onefile --windowed --name "CommandSender" --clean command_sender.py

if [ $? -ne 0 ]; then
    echo "[ERROR] Build failed!"
    exit 1
fi

echo ""
echo "[4/4] Build complete!"
echo "============================================"
echo "Output: dist/CommandSender"
echo ""
echo "Runtime dependencies on target system:"
echo "  sudo apt install xdotool python3-tk"
echo ""
echo "To run: ./dist/CommandSender"
echo ""
