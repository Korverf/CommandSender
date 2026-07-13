#!/bin/bash
# =============================================
#   CommandSender Build Script (Linux/Ubuntu)
#   使用隔离的 venv 构建，避免打包无关依赖
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

# ============================================================
# 使用隔离的 venv 构建，防止将 conda/system Python 的
# 无关包（CUDA、PyQt5、OpenCV、matplotlib 等）打包进去
#
# 注意：conda-forge 的 libpython 包含大量调试符号，
# 用 strip --strip-unneeded 可将其从 ~32MB 降至 ~5MB。
# ============================================================
VENV_DIR="/tmp/commandsender-build-venv"
echo "[2/4] Creating isolated build environment..."
rm -rf "$VENV_DIR"
python3 -m venv "$VENV_DIR"

# Strip libpython 调试符号（conda-forge 的 libpython 通常 ~32MB，
# strip 后可降至 ~5MB，对最终二进制体积影响巨大）
PYTHON_LIB="$VENV_DIR/lib/python3.13/lib-dynload/../../libpython3.13.so.1.0"
if [ -f "$PYTHON_LIB" ]; then
    echo "[INFO] Stripping debug symbols from libpython..."
    ls -lh "$PYTHON_LIB"
    strip --strip-unneeded "$PYTHON_LIB" 2>/dev/null && ls -lh "$PYTHON_LIB"
fi

echo "[3/4] Installing build dependencies in venv..."
"$VENV_DIR/bin/pip" install pyautogui pyperclip pyinstaller -q

echo "[4/4] Building executable..."
"$VENV_DIR/bin/python" -m PyInstaller \
    --onefile --windowed \
    --name "CommandSender" \
    --add-data "commandsender.png:." \
    --strip \
    --clean \
    command_sender.py

if [ $? -ne 0 ]; then
    echo "[ERROR] Build failed!"
    exit 1
fi

# Clean up venv
rm -rf "$VENV_DIR"

# ============================================================
# UPX 压缩（PyInstaller 6.21 + Linux 默认禁用，显式执行）
# UPX 3.96 对 PyInstaller 产物有兼容问题，捕获崩溃不阻塞构建
# ============================================================
if command -v upx &> /dev/null; then
    echo ""
    echo "[INFO] UPX found, trying to compress executable..."
    BEFORE=$(stat -c%s "dist/CommandSender" 2>/dev/null || stat -f%z "dist/CommandSender" 2>/dev/null)
    set +e
    upx --best dist/CommandSender 2>&1
    UPX_EXIT=$?
    set -e
    if [ $UPX_EXIT -eq 0 ]; then
        AFTER=$(stat -c%s "dist/CommandSender" 2>/dev/null || stat -f%z "dist/CommandSender" 2>/dev/null)
        if [ -n "$BEFORE" ] && [ -n "$AFTER" ] && [ "$AFTER" -lt "$BEFORE" ]; then
            echo "[INFO] UPX: $BEFORE -> $AFTER bytes ($(( (BEFORE-AFTER)*100/BEFORE ))% reduction)"
        fi
    else
        echo "[WARN] UPX compression skipped (exit code $UPX_EXIT)."
        echo "       This is expected with older UPX versions on PyInstaller binaries."
        echo "       Binary is still fully functional at $(numfmt --to=iec $BEFORE 2>/dev/null || echo "$BEFORE bytes")."
    fi
else
    echo "[WARN] upx not found, skipping compression."
    echo "       Install: sudo apt install upx -y"
fi

echo ""
echo "============================================"
echo "  Build complete!"
echo "============================================"
echo "Output: dist/CommandSender"
echo ""
echo "Runtime dependencies on target system:"
echo "  sudo apt install xdotool python3-tk"
echo ""
echo "To run: ./dist/CommandSender"
echo ""
