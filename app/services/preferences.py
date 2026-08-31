from __future__ import annotations

import json
from pathlib import Path


class Preferences:
    def __init__(self, path: Path, default_auto_update: bool = True) -> None:
        self.path = path
        self.values = {"automatic_update_check": default_auto_update, "last_installed_version": "", "supplier_auto_suggest": True, "quick_print_without_cheque_number": False, "dark_mode": False, "google_drive_backup": False, "google_drive_folder": ""}
        try:
            self.values.update(json.loads(path.read_text(encoding="utf-8")))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.values, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def get_bool(self, key: str) -> bool:
        return bool(self.values.get(key, False))

    def set(self, key: str, value: object) -> None:
        self.values[key] = value
        self.save()

