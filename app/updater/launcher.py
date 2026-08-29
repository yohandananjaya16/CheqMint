from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def launch_installer(installer: Path) -> None:
    # Inno Setup waits for this process, performs a silent upgrade, and relaunches the app.
    args = [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS",
            "/RESTARTAPPLICATIONS", "/RESTARTEXITCODE=3010", "/LOG"]
    creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(args, close_fds=True, creationflags=creation_flags, cwd=str(installer.parent))


def current_executable() -> Path:
    return Path(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]).resolve()

