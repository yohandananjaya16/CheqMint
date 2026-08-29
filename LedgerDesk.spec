# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / "app" / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "config.json"), "."), (str(root / "version.json"), "."), (str(root / "assets"), "assets")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="LedgerDesk", debug=False,
          bootloader_ignore_signals=False, strip=False, upx=True, console=False,
          icon=str(root / "assets" / "app.ico"), version=str(root / "installer" / "version_info.txt"))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="LedgerDesk")

