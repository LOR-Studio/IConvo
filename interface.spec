# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['interface.py'],
    pathex=[],
    binaries=[],
    datas=[('config.yaml', '.'), ('light_bulb.png', '.'), ('dark_bulb.png', '.')],
    hiddenimports=['opencv-python', 'sklearn', 'pygame', 'pyaudio', 'keyboard', 'nltk', 'pygments'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='interface',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='interface',
)
