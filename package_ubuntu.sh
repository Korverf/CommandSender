#!/bin/bash
# =============================================
#   CommandSender Ubuntu Package Builder
#   生成适用于 Ubuntu 22.04 的可执行安装包
# =============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="2.1.0"
PACKAGE_NAME="CommandSender-${VERSION}-ubuntu22.04"
BUILD_DIR="dist/${PACKAGE_NAME}"

echo "============================================"
echo "  CommandSender Package Builder"
echo "  Version: ${VERSION}"
echo "  Target:  Ubuntu 22.04"
echo "============================================"
echo ""

# Step 1: Build the executable
echo "[1/4] Building executable..."
bash build.sh

# Step 2: Create package directory structure
echo "[2/4] Creating package structure..."
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/bin"
mkdir -p "${BUILD_DIR}/commands"
mkdir -p "${BUILD_DIR}/share/applications"
mkdir -p "${BUILD_DIR}/share/icons/hicolor/48x48/apps"

# Copy executable
cp dist/CommandSender "${BUILD_DIR}/bin/"

# Copy sample commands
cp dist/commands/*.txt "${BUILD_DIR}/commands/" 2>/dev/null || true

# Copy icon
cp "$SCRIPT_DIR/commandsender.png" "${BUILD_DIR}/share/icons/hicolor/48x48/apps/commandsender.png"

# Create .desktop file
cat > "${BUILD_DIR}/share/applications/commandsender.desktop" << 'DESKTOPEOF'
[Desktop Entry]
Type=Application
Name=CommandSender
Name[zh_CN]=命令行发送工具
Comment=Cross-platform command line sending tool
Comment[zh_CN]=跨平台命令行批量发送工具
Exec=/usr/local/bin/CommandSender
Icon=/usr/share/icons/hicolor/48x48/apps/commandsender.png
Terminal=false
Categories=Utility;Development;
Keywords=command;terminal;send;batch;
StartupWMClass=CommandSender
DESKTOPEOF

# Step 3: Create install script
echo "[3/4] Creating installer..."
cat > "${BUILD_DIR}/install.sh" << 'INSTALLEOF'
#!/bin/bash
# CommandSender Installer for Ubuntu 22.04
set -e

echo "============================================"
echo "  CommandSender v2.1.0 Installer"
echo "  Target: Ubuntu 22.04"
echo "============================================"
echo ""

# Check dependencies
echo "[*] Checking dependencies..."

DEPS_TO_INSTALL=""

if ! command -v xdotool &> /dev/null; then
    DEPS_TO_INSTALL="$DEPS_TO_INSTALL xdotool"
fi

python3 -c "import tkinter" 2>/dev/null || {
    DEPS_TO_INSTALL="$DEPS_TO_INSTALL python3-tk"
}

# Check for CJK font (required for proper Chinese character display)
if ! fc-list :lang=zh 2>/dev/null | grep -q .; then
    DEPS_TO_INSTALL="$DEPS_TO_INSTALL fonts-wqy-microhei"
fi

if [ -n "$DEPS_TO_INSTALL" ]; then
    echo "[*] Installing system dependencies: $DEPS_TO_INSTALL"
    sudo apt-get update -qq
    sudo apt-get install -y $DEPS_TO_INSTALL
fi

# Install executable
echo "[*] Installing CommandSender..."
sudo cp bin/CommandSender /usr/local/bin/
sudo chmod +x /usr/local/bin/CommandSender

# Install desktop file
echo "[*] Installing desktop entry..."
if [ -d share/applications ]; then
    sudo cp share/applications/commandsender.desktop /usr/share/applications/
fi

# Install icon
echo "[*] Installing application icon..."
if [ -f share/icons/hicolor/48x48/apps/commandsender.png ]; then
    sudo mkdir -p /usr/share/icons/hicolor/48x48/apps
    sudo cp share/icons/hicolor/48x48/apps/commandsender.png /usr/share/icons/hicolor/48x48/apps/
fi

# Install sample commands
echo "[*] Installing sample commands..."
mkdir -p "$HOME/.config/commandsender/commands"
cp -n commands/*.txt "$HOME/.config/commandsender/commands/" 2>/dev/null || true
mkdir -p "$HOME/.config/commandsender"

# Fix Xauthority for WSLg/X11 environments
echo "[*] Configuring X11 authentication..."
if [ -z "$XAUTHORITY" ] && [ ! -f "$HOME/.Xauthority" ]; then
    if command -v xauth &> /dev/null; then
        DISPLAY=${DISPLAY:-:0} xauth generate $DISPLAY . timeout 0 2>/dev/null || {
            touch "$HOME/.Xauthority"
        }
    else
        touch "$HOME/.Xauthority"
    fi
fi

# Create initial config
if [ ! -f "$HOME/.config/commandsender/app_config.json" ]; then
    cat > "$HOME/.config/commandsender/app_config.json" << 'CONFEOF'
{
  "commands_dir": "commands",
  "delay_after_focus": 0.3,
  "delay_between_keys": 0.005,
  "use_clipboard": true,
  "recent_files": [],
  "last_directory": ""
}
CONFEOF
fi

echo ""
echo "============================================"
echo "  Installation complete!"
echo "============================================"
echo ""
echo "Usage:"
echo "  CommandSender              # Run from terminal"
echo "  Or find 'CommandSender' in your application menu"
echo ""
echo "Command files location: ~/.config/commandsender/commands/"
echo "Config file location:    ~/.config/commandsender/app_config.json"
echo ""
INSTALLEOF

chmod +x "${BUILD_DIR}/install.sh"

# Create uninstall script
cat > "${BUILD_DIR}/uninstall.sh" << 'UNINSTALLEOF'
#!/bin/bash
# CommandSender Uninstaller
set -e

echo "Uninstalling CommandSender..."
sudo rm -f /usr/local/bin/CommandSender
sudo rm -f /usr/share/applications/commandsender.desktop
sudo rm -f /usr/share/icons/hicolor/48x48/apps/commandsender.png
echo "Done. User data at ~/.config/commandsender/ is preserved."
UNINSTALLEOF

chmod +x "${BUILD_DIR}/uninstall.sh"

# Step 4: Create archive
echo "[4/4] Creating package archive..."
cd dist
tar czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}"

# Generate checksum
if command -v sha256sum &> /dev/null; then
    sha256sum "${PACKAGE_NAME}.tar.gz" > "${PACKAGE_NAME}.tar.gz.sha256"
elif command -v shasum &> /dev/null; then
    shasum -a 256 "${PACKAGE_NAME}.tar.gz" > "${PACKAGE_NAME}.tar.gz.sha256"
fi

echo ""
echo "============================================"
echo "  Package created successfully!"
echo "============================================"
echo ""
echo "Package:  dist/${PACKAGE_NAME}.tar.gz"
echo "Checksum: dist/${PACKAGE_NAME}.tar.gz.sha256"
echo ""
echo "Installation:"
echo "  tar xzf ${PACKAGE_NAME}.tar.gz"
echo "  cd ${PACKAGE_NAME}"
echo "  ./install.sh"
echo ""
