
# -*- mode: python ; coding: utf-8 -*-
import os

project_root = os.path.abspath('src')

# === Include resources folder ===
datas = [
    (os.path.join(project_root, 'resources'), 'resources')
]

# === Analysis ===
a = Analysis(
    ['src/main.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],  # exclude unwanted modules here
    noarchive=False,
    optimize=0,
)

# === PYZ ===
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# === EXE ===
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='switchblade.exe',
    debug=False,
    strip=False,    # Windows: stripping may remove necessary debug info
    upx=True,       # optional compression
    console=False,  # GUI app, no terminal window
    icon=os.path.join(project_root, 'resources/images/icon.ico'),
)

# === COLLECT ===
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='switchblade',
)
