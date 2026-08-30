from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(*args: str) -> None:
    print("+", " ".join(args))
    subprocess.run(args, cwd=ROOT, check=True)


def version() -> str:
    value = str(json.loads((ROOT / "version.json").read_text(encoding="utf-8"))["version"])
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise SystemExit("version.json must contain a numeric MAJOR.MINOR.PATCH version")
    return value


def write_version_info(value: str) -> None:
    numbers = tuple(map(int, value.split("."))) + (0,)
    content = f"""VSVersionInfo(ffi=FixedFileInfo(filevers={numbers}, prodvers={numbers}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)), kids=[StringFileInfo([StringTable('040904B0', [StringStruct('CompanyName', 'Yohan Dananjaya'), StringStruct('FileDescription', 'CheqMint'), StringStruct('FileVersion', '{value}'), StringStruct('InternalName', 'CheqMint'), StringStruct('OriginalFilename', 'CheqMint.exe'), StringStruct('ProductName', 'CheqMint'), StringStruct('ProductVersion', '{value}')])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])"""
    (ROOT / "installer" / "version_info.txt").write_text(content, encoding="utf-8")


def find_iscc() -> Path:
    override = os.getenv("LEDGERDESK_ISCC")
    if override and Path(override).is_file(): return Path(override)
    candidates = [Path(os.getenv("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
                  Path(os.getenv("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe"]
    for candidate in candidates:
        if candidate.is_file(): return candidate
    found = shutil.which("ISCC.exe")
    if found: return Path(found)
    raise SystemExit("Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php")


def main() -> int:
    if sys.platform != "win32": raise SystemExit("Release builds must run on 64-bit Windows.")
    value = version(); write_version_info(value)
    for folder in (ROOT / "build", ROOT / "dist", ROOT / "release"):
        if folder.exists(): shutil.rmtree(folder)
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "LedgerDesk.spec")
    iscc = find_iscc()
    run(str(iscc), f"/DMyAppVersion={value}", f"/DSourceRoot={ROOT}", str(ROOT / "installer" / "LedgerDesk.iss"))
    installer = ROOT / "release" / f"CheqMint-Setup-{value}.exe"
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    checksum = installer.with_suffix(installer.suffix + ".sha256")
    checksum.write_text(f"{digest}  {installer.name}\n", encoding="ascii")
    print(f"\nApplication: {ROOT / 'dist' / 'CheqMint'}\nInstaller:   {installer}\nChecksum:    {checksum}")
    return 0


if __name__ == "__main__": raise SystemExit(main())

