# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

# Resolve spec directory
spec_dir = Path(__file__).resolve().parent

block_cipher = None

# Data files: include all files from icons/ and plugins.json
datas = []
icons_dir = spec_dir / 'icons'
if icons_dir.exists() and icons_dir.is_dir():
    for f in icons_dir.iterdir():
        if f.is_file():
            # copy each icon into the 'icons' folder in the bundle
            datas.append((str(f), 'icons'))

plugins_json = spec_dir / 'plugins.json'
if plugins_json.exists() and plugins_json.is_file():
    datas.append((str(plugins_json), '.'))

# Minimal hidden imports based on the codebase
hiddenimports = [
    'bs4',
    'py7zr',
    'win32com.client',
    'winshell',
    'requests',
    'pywintypes',
    'pythoncom',
]

# Entry script
entry_script = str(spec_dir / 'run_installer.py')

a = Analysis(
    [entry_script],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Choose an icon if present
exe_icon = None
default_icon = icons_dir / 'cgg-rotated-logo.ico'
if default_icon.exists():
    exe_icon = str(default_icon)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OBS_Installer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=exe_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='OBS_Installer',
)