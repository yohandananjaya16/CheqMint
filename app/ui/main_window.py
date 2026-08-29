from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QThread, Signal, QTimer
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from app.config import AppConfig
from app.services.preferences import Preferences
from app.updater import UpdateClient, UpdateError, UpdateInfo
from app.updater.launcher import launch_installer
from app.ui.update_dialogs import DownloadDialog, UpdateDialog

LOGGER = logging.getLogger(__name__)


class CheckWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, client: UpdateClient, current: str) -> None:
        super().__init__()
        self.client, self.current = client, current

    def run(self) -> None:
        try:
            self.completed.emit(self.client.check(self.current))
        except UpdateError as exc:
            LOGGER.exception("Update check failed")
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, version: str, preferences: Preferences, icon_path: Path) -> None:
        super().__init__()
        self.config, self.version, self.preferences = config, version, preferences
        self.client = UpdateClient(config.github_owner, config.github_repository)
        self.setWindowTitle(config.application_name)
        self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1050, 680)
        self.setMinimumSize(820, 540)
        self.statusBar().showMessage("Ready")
        self._build_ui()
        pending = str(preferences.values.get("pending_update_version", ""))
        if pending == version:
            preferences.set("pending_update_version", "")
            QTimer.singleShot(700, lambda: QMessageBox.information(self, "Update Complete", f"LedgerDesk was updated successfully to version {version}."))
        if config.update_check_enabled and preferences.get_bool("automatic_update_check"):
            QTimer.singleShot(1400, lambda: self.check_updates(False))

    def _build_ui(self) -> None:
        root = QWidget(objectName="root")
        outer = QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        side = QFrame(objectName="sidebar"); side.setFixedWidth(230)
        nav = QVBoxLayout(side); nav.setContentsMargins(20, 30, 20, 24)
        nav.addWidget(QLabel("LedgerDesk", objectName="brand")); nav.addSpacing(30)
        for index, label in enumerate(("Dashboard", "Settings", "About")):
            button = QPushButton(label, objectName="nav")
            button.clicked.connect(lambda _=False, i=index: self.pages.setCurrentIndex(i))
            nav.addWidget(button)
        nav.addStretch(); nav.addWidget(QLabel(f"Version {self.version}", objectName="brand"))
        self.pages = QStackedWidget()
        self.pages.addWidget(self._dashboard()); self.pages.addWidget(self._settings()); self.pages.addWidget(self._about())
        outer.addWidget(side); outer.addWidget(self.pages, 1)
        self.setCentralWidget(root)

    def _page(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(44, 38, 44, 38); layout.setSpacing(20)
        layout.addWidget(QLabel(title, objectName="pageTitle")); return page, layout

    def _card(self, title: str, body: str) -> QFrame:
        card = QFrame(objectName="card"); layout = QVBoxLayout(card); layout.setContentsMargins(24, 22, 24, 22)
        layout.addWidget(QLabel(f"<h3>{title}</h3>")); layout.addWidget(QLabel(body, objectName="muted")); return card

    def _dashboard(self) -> QWidget:
        page, layout = self._page("Dashboard")
        layout.addWidget(self._card("Welcome to LedgerDesk", "A secure, local workspace ready for your business workflows."))
        row = QHBoxLayout(); row.addWidget(self._card("Application status", "Running normally\nYour data stays in your Windows profile.")); row.addWidget(self._card("Updates", "Protected by HTTPS and SHA-256 verification.")); layout.addLayout(row); layout.addStretch()
        return page

    def _settings(self) -> QWidget:
        page, layout = self._page("Settings")
        card = QFrame(objectName="card"); box = QVBoxLayout(card); box.setContentsMargins(24, 22, 24, 22)
        box.addWidget(QLabel(f"<h3>Application version</h3><p>{self.version}</p>"))
        auto = QCheckBox("Check automatically when LedgerDesk starts"); auto.setChecked(self.preferences.get_bool("automatic_update_check")); auto.toggled.connect(lambda value: self.preferences.set("automatic_update_check", value)); box.addWidget(auto)
        check = QPushButton("Check for Updates"); check.clicked.connect(lambda: self.check_updates(True)); box.addWidget(check)
        data = QPushButton("Open Data Folder", objectName="secondary"); data.clicked.connect(lambda: self.open_folder(self.config.data_dir)); box.addWidget(data)
        logs = QPushButton("Open Log Folder", objectName="secondary"); logs.clicked.connect(lambda: self.open_folder(self.config.logs_dir)); box.addWidget(logs)
        layout.addWidget(card); layout.addStretch(); return page

    def _about(self) -> QWidget:
        page, layout = self._page("About")
        layout.addWidget(self._card(self.config.application_name, f"Version {self.version}\n{self.config.company_name}\n{self.config.copyright}\n\nUpdate status: automatic checks are available.")); layout.addStretch(); return page

    def open_folder(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True); QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def check_updates(self, interactive: bool) -> None:
        if self.config.github_owner == "YOUR_ORG":
            if interactive: QMessageBox.information(self, "Updates", "Set github_owner in config.json before publishing releases.")
            return
        self.statusBar().showMessage("Checking for updates…")
        self.check_worker = CheckWorker(self.client, self.version)
        self.check_worker.completed.connect(lambda info: self._checked(info, interactive))
        self.check_worker.failed.connect(lambda message: self._check_failed(message, interactive))
        self.check_worker.start()

    def _checked(self, info: UpdateInfo | None, interactive: bool) -> None:
        self.statusBar().showMessage("Update check complete", 4000)
        if info is None:
            if interactive: QMessageBox.information(self, "Updates", "You're up to date.")
            return
        if UpdateDialog(self.version, info, self).exec(): self.download_update(info)

    def _check_failed(self, message: str, interactive: bool) -> None:
        self.statusBar().showMessage("Unable to check for updates (offline use is unaffected).", 6000)
        if interactive: QMessageBox.warning(self, "Unable to Check for Updates", "Please check your internet connection and try again.\n\n" + message)

    def download_update(self, info: UpdateInfo) -> None:
        target = self.config.data_dir / "updates" / info.filename
        dialog = DownloadDialog(self.client, info, target, self); dialog.start()
        if dialog.exec():
            answer = QMessageBox.question(self, "Ready to Install", "The update was verified. LedgerDesk will close, install the update, and restart. Continue?")
            if answer == QMessageBox.Yes:
                LOGGER.info("Launching verified installer %s", target)
                self.preferences.set("pending_update_version", info.version)
                launch_installer(target)
                QApplication.instance().quit()
        elif dialog.error:
            LOGGER.error("Update download failed: %s", dialog.error)
            QMessageBox.critical(self, "Update Failed", dialog.error + "\n\nLedgerDesk was not changed.")

