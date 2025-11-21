# -*- mode: python ; coding: utf-8 -*-

import os

assets_dir = 'remotex_viewer/assets'
datas = [
    (os.path.join(assets_dir, f), 'remotex_viewer/assets') for f in os.listdir(assets_dir) if f != 'default.json'
]

a = Analysis(
    ['remotex_viewer/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["default.json"],
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
    name='Remotex Viewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='remotex_viewer/assets/app_icon.ico'
)
