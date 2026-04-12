
# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files

# === Paths ===
project_root = os.path.abspath('src')

# === Include resources folder (all files recursively) ===
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
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],  # you can exclude unwanted modules here
    noarchive=False,
    optimize=0,
)

# === PYZ ===
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# === EXE ===
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='switchblade',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# === COLLECT ===
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='switchblade',
)

# === macOS BUNDLE ===
plist = {
    'CFBundleName': 'switchblade',
    'CFBundleDisplayName': 'switchblade',
    'CFBundleIdentifier': 'com.joergBeigang.switchblade',
    'CFBundleIconFile': 'icon',  # no .icns
    'NSRequiresAquaSystemAppearance': False,
    'NSHighResolutionCapable': True,
}

app = BUNDLE(
    coll,
    name='switchblade.app',
    icon=os.path.join(project_root, 'resources/images/icon.icns'),
    bundle_identifier='com.joergBeigang.switchblade',
    info_plist=plist,
)
