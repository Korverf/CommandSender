# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for CommandSender (cross-platform)
# Windows: python -m PyInstaller CommandSender.spec
# Linux:   python3 -m PyInstaller CommandSender.spec

a = Analysis(
    ['command_sender.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'window_manager',
        'pyperclip',
        'pyautogui',
        'tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CommandSender',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
