# -*- mode: python ; coding: utf-8 -*-
# Usage: pyinstaller SmartTrafficCounter.spec

block_cipher = None

from PyInstaller.utils.hooks import collect_all

app_name = 'SmartTrafficCounter'
main_script = 'modern_vehicle_counter.py'

datas = []
binaries = []
hiddenimports = []

for pkg in ['ultralytics', 'torch', 'torchvision', 'cv2', 'PIL']:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Optionally bundle files:
# datas += [('yolo11n.pt', '.'), ('settings.json', '.')]

a = Analysis(
    [main_script],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=app_name
)