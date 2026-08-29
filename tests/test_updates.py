import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from app.updater.client import UpdateClient, UpdateError, UpdateInfo


class UpdateTests(unittest.TestCase):
    def test_semantic_version_comparison(self) -> None:
        self.assertTrue(UpdateClient.is_newer("1.9.9", "1.10.0"))
        self.assertFalse(UpdateClient.is_newer("2.0.0", "1.99.0"))

    def test_invalid_version_is_rejected(self) -> None:
        with self.assertRaises(UpdateError): UpdateClient.is_newer("1.0.0", "not-a-version")

    def test_non_github_download_is_rejected(self) -> None:
        with self.assertRaises(UpdateError):
            UpdateClient("owner", "repo")._validate_download_url("https://example.com/update.exe")

    def test_corrupt_download_is_removed(self) -> None:
        with TemporaryDirectory() as temp:
            folder = Path(temp); response = self._response(b"bad")
            info = UpdateInfo("1.1.0", "https://github.com/owner/repo/releases/download/v1.1.0/LedgerDesk-Setup-1.1.0.exe", "0" * 64, 3, "", "update.exe")
            target = folder / "update.exe"
            with patch.object(UpdateClient, "_request", return_value=response), self.assertRaises(UpdateError):
                UpdateClient("owner", "repo").download(info, target, lambda *_: None, lambda: False)
            self.assertFalse(target.exists()); self.assertFalse((folder / "update.exe.part").exists())

    def test_cancelled_download_is_removed(self) -> None:
        with TemporaryDirectory() as temp:
            folder = Path(temp); response = self._response(b"data")
            info = UpdateInfo("1.1.0", "https://github.com/o/r/releases/download/v1/u.exe", "x", 4, "", "u.exe")
            with patch.object(UpdateClient, "_request", return_value=response), self.assertRaises(UpdateError):
                UpdateClient("o", "r").download(info, folder / "u.exe", lambda *_: None, lambda: True)

    @staticmethod
    def _response(data: bytes) -> Mock:
        response = Mock(); response.__enter__ = Mock(return_value=response); response.__exit__ = Mock(return_value=False)
        response.headers = {"Content-Length": str(len(data))}; response.geturl.return_value = "https://github.com/o/r/releases/download/v1/u.exe"
        response.read.side_effect = [data, b""]; return response


if __name__ == "__main__": unittest.main()

