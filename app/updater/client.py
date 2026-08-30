from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)
INSTALLER_PATTERN = re.compile(r"-Setup-[0-9]+\.[0-9]+\.[0-9]+\.exe$", re.IGNORECASE)


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    download_url: str
    sha256: str
    size: int
    notes: str
    filename: str


class UpdateClient:
    def __init__(self, owner: str, repository: str, timeout: int = 20) -> None:
        self.owner, self.repository, self.timeout = owner, repository, timeout
        self.api_url = f"https://api.github.com/repos/{owner}/{repository}/releases/latest"

    @staticmethod
    def _version(value: str) -> tuple[int, int, int]:
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
        if not match:
            raise UpdateError("The release has an invalid version number.")
        return tuple(map(int, match.groups()))  # type: ignore[return-value]

    @classmethod
    def is_newer(cls, current: str, candidate: str) -> bool:
        return cls._version(candidate) > cls._version(current)

    def _request(self, url: str):
        request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "CheqMint-Updater"})
        return urlopen(request, timeout=self.timeout)

    def check(self, current_version: str) -> UpdateInfo | None:
        try:
            with self._request(self.api_url) as response:
                if getattr(response, "status", 200) != 200: raise UpdateError("The update service returned an error.")
                release = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise UpdateError("Unable to contact the update service.") from exc
        candidate = str(release.get("tag_name", "")).lstrip("v")
        if not self.is_newer(current_version, candidate): return None
        assets = release.get("assets", [])
        installer = next((a for a in assets if INSTALLER_PATTERN.search(str(a.get("name", "")))), None)
        if installer is None: raise UpdateError("This release does not contain a Windows installer.")
        checksum_asset = next((a for a in assets if a.get("name") == str(installer["name"]) + ".sha256"), None)
        if checksum_asset is None: raise UpdateError("The release checksum is missing; the update was rejected.")
        return UpdateInfo(candidate, str(installer["browser_download_url"]),
                          self._read_checksum(str(checksum_asset["browser_download_url"])),
                          int(installer.get("size", 0)), str(release.get("body", "")), str(installer["name"]))

    def _read_checksum(self, url: str) -> str:
        self._validate_download_url(url)
        try:
            with self._request(url) as response: text = response.read(4096).decode("ascii", errors="ignore")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise UpdateError("Unable to download the update checksum.") from exc
        match = re.search(r"\b[a-fA-F0-9]{64}\b", text)
        if not match: raise UpdateError("The update checksum is invalid.")
        return match.group(0).lower()

    def _validate_download_url(self, url: str) -> None:
        parsed = urlparse(url)
        allowed = {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
        if parsed.scheme != "https" or parsed.hostname not in allowed:
            raise UpdateError("The update download is not hosted by the official GitHub service.")

    def download(self, info: UpdateInfo, destination: Path,
                 progress: Callable[[int, int], None], cancelled: Callable[[], bool]) -> Path:
        self._validate_download_url(info.download_url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".part"); partial.unlink(missing_ok=True)
        digest, received = hashlib.sha256(), 0
        try:
            with self._request(info.download_url) as response, partial.open("wb") as target:
                final_url = response.geturl()
                self._validate_download_url(final_url)
                total = int(response.headers.get("Content-Length", info.size or 0))
                while True:
                    if cancelled(): raise UpdateError("The update download was cancelled.")
                    chunk = response.read(1024 * 256)
                    if not chunk: break
                    target.write(chunk); digest.update(chunk); received += len(chunk); progress(received, total)
            if info.size and received != info.size: raise UpdateError("The downloaded update has an unexpected size.")
            if digest.hexdigest().lower() != info.sha256.lower():
                raise UpdateError("The downloaded update failed its SHA-256 integrity check.")
            partial.replace(destination); return destination
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise UpdateError("The update download was interrupted.") from exc
        finally:
            if partial.exists() and not destination.exists(): partial.unlink(missing_ok=True)

