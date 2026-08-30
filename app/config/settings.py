from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


def resource_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / name


@dataclass(frozen=True)
class AppConfig:
    application_name: str
    company_name: str
    publisher_url: str
    github_owner: str
    github_repository: str
    update_check_enabled: bool
    copyright: str
    data_storage_path: str

    @property
    def data_dir(self) -> Path:
        override = os.getenv("CHEQMINT_DATA_DIR") or os.getenv("LEDGERDESK_DATA_DIR")
        if override:
            return Path(override).expanduser().resolve()
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / Path(self.data_storage_path)

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def github_api_url(self) -> str:
        return f"https://api.github.com/repos/{self.github_owner}/{self.github_repository}/releases/latest"


def load_config() -> AppConfig:
    return AppConfig(**json.loads(resource_path("config.json").read_text(encoding="utf-8")))


def load_version() -> str:
    return str(json.loads(resource_path("version.json").read_text(encoding="utf-8"))["version"])

