#!/bin/bash
# Build CommandSender using clean venv
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
/tmp/commandsender-venv/bin/python3 -m PyInstaller \
    --onefile --windowed \
    --name "CommandSender" \
    --add-data "commandsender.png:." \
    --distpath ../dist_venv \
    --workpath build_venv \
    --clean \
    command_sender.py
echo "Build output:" 
ls -lh ../dist_venv/CommandSender
