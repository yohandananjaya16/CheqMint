from __future__ import annotations

import re

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QProgressBar,
                               QPushButton, QTextBrowser, QVBoxLayout)

from app.updater import UpdateClient, UpdateError, UpdateInfo


def readable_notes(markdown: str) -> str:
    text = re.sub(r"!\[[^]]*]\([^)]*\)", "", markdown)
    text = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return text.strip() or "Maintenance and reliability improvements."


class UpdateDialog(QDialog):
    def __init__(self, current: str, info: UpdateInfo, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Update Available")
        self.setMinimumSize(520, 420)
        layout = QVBoxLayout(self)
        title = QLabel(f"<h2>Version {info.version} is available</h2>")
        layout.addWidget(title)
        layout.addWidget(QLabel(f"Current version: <b>{current}</b><br>New version: <b>{info.version}</b>"))
        layout.addWidget(QLabel("Release notes"))
        notes = QTextBrowser()
        notes.setPlainText(readable_notes(info.notes))
        layout.addWidget(notes)
        buttons = QDialogButtonBox()
        self.update_button = buttons.addButton("Update Now", QDialogButtonBox.AcceptRole)
        buttons.addButton("Later", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class DownloadWorker(QThread):
    progress = Signal(int, int)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, client: UpdateClient, info: UpdateInfo, destination) -> None:
        super().__init__()
        self.client, self.info, self.destination = client, info, destination
        self.cancelled = False

    def run(self) -> None:
        try:
            path = self.client.download(self.info, self.destination, self.progress.emit, lambda: self.cancelled)
            self.succeeded.emit(str(path))
        except UpdateError as exc:
            self.failed.emit(str(exc))


class DownloadDialog(QDialog):
    downloaded = Signal(str)

    def __init__(self, client: UpdateClient, info: UpdateInfo, destination, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Downloading Update")
        self.setMinimumWidth(480)
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h2>Downloading LedgerDesk {info.version}</h2>"))
        self.bar = QProgressBar()
        layout.addWidget(self.bar)
        self.detail = QLabel("Preparing download…")
        layout.addWidget(self.detail)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.cancel)
        layout.addWidget(cancel)
        self.worker = DownloadWorker(client, info, destination)
        self.worker.progress.connect(self.on_progress)
        self.worker.succeeded.connect(self.on_success)
        self.worker.failed.connect(self.on_failure)
        self.error = ""

    def start(self) -> None:
        self.worker.start()

    def on_progress(self, received: int, total: int) -> None:
        self.bar.setRange(0, total or 0)
        self.bar.setValue(received)
        mb, total_mb = received / 1_048_576, total / 1_048_576 if total else 0
        self.detail.setText(f"Downloading: {mb:.1f} MB" + (f" / {total_mb:.1f} MB" if total else ""))

    def cancel(self) -> None:
        self.worker.cancelled = True

    def on_success(self, path: str) -> None:
        self.downloaded.emit(path)
        self.accept()

    def on_failure(self, message: str) -> None:
        self.error = message
        self.reject()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.worker.isRunning():
            self.worker.cancelled = True
            event.ignore()
            return
        super().closeEvent(event)

