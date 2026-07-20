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
# ============================================================
# 必须使用【系统】Python 构建：conda/miniforge 的 Tk 只能看到极少的
# 核心位图字体（无 CJK），打包后应用内中文会回退到 song ti 等位图字体，
# 显示异常。系统 /usr/bin/python3 的 Tk 能看到系统安装的 Noto CJK 字体。
# ============================================================
BUILD_PYTHON=""
for cand in /usr/bin/python3 /usr/local/bin/python3; do
    if [ -x "$cand" ] && "$cand" -c "import tkinter" 2>/dev/null; then
        BUILD_PYTHON="$cand"
        break
    fi
done

if [ -z "$BUILD_PYTHON" ]; then
    # 系统 python 缺 tkinter，尝试安装 python3-tk 后重试
    if [ -x /usr/bin/python3 ]; then
        echo "[WARN] system python3 lacks tkinter, installing python3-tk..."
        sudo apt-get install -y python3-tk python3-venv
        if /usr/bin/python3 -c "import tkinter" 2>/dev/null; then
            BUILD_PYTHON=/usr/bin/python3
        fi
    fi
fi

if [ -z "$BUILD_PYTHON" ]; then
    echo "[ERROR] 未找到带 tkinter 的系统 Python（/usr/bin/python3）。"
    echo "conda/miniforge 的 Python 不能用于构建（其 Tk 看不到系统 CJK 字体）。"
    echo "请安装： sudo apt install -y python3 python3-venv python3-tk"
    exit 1
fi
echo "[INFO] 使用系统 Python 构建： $BUILD_PYTHON ($("$BUILD_PYTHON" --version 2>&1))"

# 确保 venv + ensurepip 可用（系统 python 需 python3-venv 包）
if ! "$BUILD_PYTHON" -c "import ensurepip" 2>/dev/null; then
    echo "[WARN] python3-venv/ensurepip 缺失，正在安装 python3-venv..."
    PYVER=$("$BUILD_PYTHON" -c "import sys; print('%d.%d' % sys.version_info[:2])")
    sudo apt-get install -y python3-venv "python${PYVER}-venv" 2>/dev/null || sudo apt-get install -y python3-venv
fi

echo "[1/4] Checking system dependencies..."

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
"$BUILD_PYTHON" -m venv "$VENV_DIR"

# Strip libpython 调试符号（仅当存在时；system python 通常无此文件，
# conda-forge 的 libpython 含大量调试符号，strip 后可大幅减体）
PYTHON_LIB=$(find "$VENV_DIR" -maxdepth 3 -name 'libpython*.so*' 2>/dev/null | head -1)
if [ -n "$PYTHON_LIB" ] && [ -f "$PYTHON_LIB" ]; then
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
