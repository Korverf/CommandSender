#!/bin/bash
# Cleanup build artifacts
set -e
cd "$(dirname "$0")"
rm -rf ../dist_new build_new CommandSender.spec __pycache__
rm -f _rebuild.sh cleanup.sh
# Also clean PyInstaller cache
rm -rf ~/.cache/pyinstaller
echo "Cleaned up"
