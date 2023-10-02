# -*- mode: python ; coding: utf-8 -*-

with open("VERSION", "r") as file:
  VERSION = file.read()

print("Mads Version: " + VERSION)

a = Analysis(
    ['mads/compiler.py', 'mads/const.py', 'mads/__main__.py', 'mads/output.py', 'mads/pre.py', 'mads/tokenizer.py', 'mads/utils.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    name='mads',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mads',
)
