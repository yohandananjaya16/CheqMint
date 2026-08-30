from __future__ import annotations

import logging
import os
import zipfile
import shutil
from datetime import date
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from app.config import AppConfig
from app.services.preferences import Preferences
from app.services.cheque_templates import TemplateStore
from app.services.suppliers import SupplierStore
from app.services.print_history import PrintHistoryStore
from app.services.bank_accounts import BankAccountStore, CalibrationStore
from app.services.profile import ProfileStore
from app.updater import UpdateClient, UpdateError, UpdateInfo
from app.updater.launcher import launch_installer
from app.ui.cheque_page import ChequePage
from app.ui.management_pages import BankManagementPage, SupplierManagementPage
from app.ui.advanced_pages import BankAccountsPage, HistoryPage, ReportsPage, BackupPage,ProfilePage
from app.ui.style import DARK_STYLE, LIGHT_STYLE
from app.ui.update_dialogs import DownloadDialog, UpdateDialog

LOGGER = logging.getLogger(__name__)


class BankChart(QWidget):
    def __init__(self) -> None:
        super().__init__(); self.data: dict[str, int] = {}; self.setMinimumHeight(230)

    def set_data(self, data: dict[str, int]) -> None:
        self.data = data; self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        if not self.data:
            painter.setPen(QColor("#98a2b3")); painter.drawText(self.rect(), Qt.AlignCenter, "No printed cheques yet"); return
        items = sorted(self.data.items(), key=lambda item: (-item[1], item[0]))[:8]; maximum = max(value for _, value in items)
        row_h = max(24, min(38, (self.height()-18)//len(items)))
        label_w = min(180, max(90, self.width()//4)); bar_w = max(80, self.width()-label_w-55)
        for row, (name, value) in enumerate(items):
            y = 10 + row*row_h; painter.setPen(QColor("#667085")); painter.drawText(QRectF(4, y, label_w-8, row_h-4), Qt.AlignVCenter | Qt.AlignRight, name)
            width = bar_w * value / maximum; painter.fillRect(QRectF(label_w, y+6, width, row_h-12), QColor("#0b6fa4")); painter.setPen(QColor("#344054")); painter.drawText(QRectF(label_w+width+8, y, 40, row_h-4), Qt.AlignVCenter, str(value))


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
        self.template_store = TemplateStore(config.data_dir / "templates")
        self.supplier_store = SupplierStore(config.data_dir / "suppliers.json")
        self.history_store = PrintHistoryStore(config.data_dir / "print_history.json")
        self.account_store=BankAccountStore(config.data_dir/"bank_accounts.json");self.calibration_store=CalibrationStore(config.data_dir/"printer_calibrations.json")
        self.profile_store=ProfileStore(config.data_dir/"profile.json")
        self.setWindowTitle(config.application_name)
        self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1120, 760)
        self.setMinimumSize(760, 520)
        self.statusBar().showMessage("Ready")
        self._build_ui()
        self._automatic_backup()
        QTimer.singleShot(1800,self._show_due_reminder)
        pending = str(preferences.values.get("pending_update_version", ""))
        if pending == version:
            preferences.set("pending_update_version", "")
            QTimer.singleShot(700, lambda: QMessageBox.information(self, "Update Complete", f"CheqMint was updated successfully to version {version}."))
        if config.update_check_enabled and preferences.get_bool("automatic_update_check"):
            QTimer.singleShot(1400, lambda: self.check_updates(False))

    def _build_ui(self) -> None:
        root = QWidget(objectName="root")
        outer = QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        side = QFrame(objectName="sidebar"); side.setFixedWidth(190)
        nav = QVBoxLayout(side); nav.setContentsMargins(20, 30, 20, 24)
        nav.addWidget(QLabel("CheqMint", objectName="brand")); nav.addSpacing(30)
        for index, label in enumerate(("Dashboard","Cheque Printing","Cheque History","Bank Formats","Bank Accounts","Supplier Register","User Profile","Reports","Backup / Restore","Settings","About")):
            button = QPushButton(label, objectName="nav")
            button.clicked.connect(lambda _=False, i=index: self.show_page(i))
            nav.addWidget(button)
        nav.addStretch()
        self.pages = QStackedWidget()
        self.pages.addWidget(self._dashboard())
        self.cheque_page = ChequePage(self.template_store,self.supplier_store,self.history_store,self.account_store,self.calibration_store,self.profile_store,self.preferences); self.pages.addWidget(self.cheque_page)
        self.history_page=HistoryPage(self.history_store,self.reprint_record);self.pages.addWidget(self.history_page)
        self.bank_page = BankManagementPage(self.template_store, self.refresh_cheque_lists); self.pages.addWidget(self.bank_page)
        self.account_page=BankAccountsPage(self.account_store,self.template_store,self.calibration_store,self.refresh_cheque_lists);self.pages.addWidget(self.account_page)
        self.supplier_page = SupplierManagementPage(self.supplier_store, self.refresh_cheque_lists); self.pages.addWidget(self.supplier_page)
        self.profile_page=ProfilePage(self.profile_store);self.pages.addWidget(self.profile_page)
        self.pages.addWidget(ReportsPage(self.history_store,self.profile_store));self.pages.addWidget(BackupPage(self.config.data_dir))
        self.pages.addWidget(self._settings()); self.pages.addWidget(self._about())
        outer.addWidget(side); outer.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self.refresh_dashboard()

    def _page(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(44, 38, 44, 38); layout.setSpacing(20)
        layout.addWidget(QLabel(title, objectName="pageTitle")); return page, layout

    def _card(self, title: str, body: str) -> QFrame:
        card = QFrame(objectName="card"); layout = QVBoxLayout(card); layout.setContentsMargins(24, 22, 24, 22)
        layout.addWidget(QLabel(f"<h3>{title}</h3>")); layout.addWidget(QLabel(body, objectName="muted")); return card

    def _dashboard(self) -> QWidget:
        page, layout = self._page("Dashboard")
        row = QHBoxLayout(); self.today_value = self._metric(row, "Printed Today"); self.total_value = self._metric(row, "Total Cheques"); self.amount_value = self._metric(row, "Today's Amount"); layout.addLayout(row)
        due=QHBoxLayout();self.due_today=self._metric(due,"Due Today");self.due_week=self._metric(due,"Due Next 7 Days");self.overdue=self._metric(due,"Overdue");layout.addLayout(due)
        chart_card = QFrame(objectName="card"); chart_box = QVBoxLayout(chart_card); chart_box.setContentsMargins(22, 18, 22, 18); chart_box.addWidget(QLabel("Printed cheques by bank", objectName="sectionTitle")); self.bank_chart = BankChart(); chart_box.addWidget(self.bank_chart); layout.addWidget(chart_card, 1)
        export = QPushButton("Export Today's CSV"); export.clicked.connect(self.export_today); layout.addWidget(export)
        return page

    def _metric(self, row: QHBoxLayout, title: str) -> QLabel:
        card = QFrame(objectName="card"); box = QVBoxLayout(card); box.setContentsMargins(18, 16, 18, 16); box.addWidget(QLabel(title, objectName="muted")); value = QLabel("0", objectName="metricValue"); box.addWidget(value); row.addWidget(card); return value

    def refresh_dashboard(self) -> None:
        summary = self.history_store.summary(); self.today_value.setText(str(summary["today_count"])); self.total_value.setText(str(summary["total_count"])); self.amount_value.setText(f"Rs. {summary['today_amount']:,.2f}"); self.bank_chart.set_data(summary["by_bank"])
        today=date.today();active=[x for x in self.history_store.list() if x.status=="Issued"];self.due_today.setText(str(sum(x.cheque_date==today.isoformat() for x in active)));self.due_week.setText(str(sum(today.isoformat()<x.cheque_date<=(today.fromordinal(today.toordinal()+7)).isoformat() for x in active)));self.overdue.setText(str(sum(x.cheque_date<today.isoformat() for x in active)))

    def export_today(self) -> None:
        suggested = str(Path.home() / "Documents" / f"CheqMint-cheques-{date.today().isoformat()}.csv")
        target, _ = QFileDialog.getSaveFileName(self, "Export Today's Cheques", suggested, "CSV files (*.csv)")
        if not target: return
        count = self.history_store.export_day_csv(Path(target), date.today()); QMessageBox.information(self, "CSV Exported", f"Saved {count} cheque record(s) to:\n{target}")

    def show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        if index == 0: self.refresh_dashboard()
        elif index == 1: self.refresh_cheque_lists()
        elif index == 2: self.history_page.reload()
        elif index == 3: self.bank_page.reload()
        elif index == 4: self.account_page.reload()
        elif index == 5: self.supplier_page.reload()

    def refresh_cheque_lists(self) -> None:
        self.cheque_page.reload_templates(); self.cheque_page.reload_suppliers();self.cheque_page.reload_accounts();self.cheque_page.refresh_preview()

    def reprint_record(self,record):
        self.cheque_page.load_record(record);self.pages.setCurrentIndex(1)

    def _settings(self) -> QWidget:
        page, layout = self._page("Settings")
        card = QFrame(objectName="card"); box = QVBoxLayout(card); box.setContentsMargins(24, 22, 24, 22)
        box.addWidget(QLabel("Appearance", objectName="sectionTitle"))
        self.theme_label = QLabel("Dark Mode" if self.preferences.get_bool("dark_mode") else "Light Mode")
        box.addWidget(self.theme_label)
        dark = QCheckBox("Switch between Light Mode and Dark Mode", objectName="themeSwitch"); dark.setChecked(self.preferences.get_bool("dark_mode")); dark.toggled.connect(self.set_dark_mode); box.addWidget(dark)
        suggest=QCheckBox("Supplier name auto-suggestions");suggest.setChecked(self.preferences.get_bool("supplier_auto_suggest"));suggest.toggled.connect(self.set_supplier_suggestions);box.addWidget(suggest)
        box.addSpacing(12);box.addWidget(QLabel("Google Drive Backup",objectName="sectionTitle"));self.drive_label=QLabel(str(self.preferences.values.get("google_drive_folder", "No folder selected")),objectName="muted");self.drive_label.setWordWrap(True);box.addWidget(self.drive_label)
        choose_drive=QPushButton("Choose Google Drive Folder",objectName="secondary");choose_drive.clicked.connect(self.choose_drive_folder);box.addWidget(choose_drive)
        drive_sync=QCheckBox("Copy automatic backups to this folder");drive_sync.setChecked(self.preferences.get_bool("google_drive_backup"));drive_sync.toggled.connect(lambda value:self.preferences.set("google_drive_backup",value));box.addWidget(drive_sync)
        data = QPushButton("Open Data Folder", objectName="secondary"); data.clicked.connect(lambda: self.open_folder(self.config.data_dir)); box.addWidget(data)
        logs = QPushButton("Open Log Folder", objectName="secondary"); logs.clicked.connect(lambda: self.open_folder(self.config.logs_dir)); box.addWidget(logs)
        layout.addWidget(card); layout.addStretch(); return page

    def set_dark_mode(self, enabled: bool) -> None:
        self.preferences.set("dark_mode", enabled); QApplication.instance().setStyleSheet(DARK_STYLE if enabled else LIGHT_STYLE)
        self.theme_label.setText("Dark Mode" if enabled else "Light Mode")

    def set_supplier_suggestions(self,enabled:bool)->None:
        self.preferences.set("supplier_auto_suggest",enabled);self.cheque_page.refresh_supplier_suggestions()

    def choose_drive_folder(self)->None:
        folder=QFileDialog.getExistingDirectory(self,"Choose your Google Drive folder",str(Path.home()))
        if folder:self.preferences.set("google_drive_folder",folder);self.drive_label.setText(folder)

    def _about(self) -> QWidget:
        page, layout = self._page("About")
        info = QFrame(objectName="card"); box = QVBoxLayout(info); box.setContentsMargins(24, 22, 24, 22)
        box.addWidget(QLabel(self.config.application_name, objectName="sectionTitle")); box.addWidget(QLabel(f"Application Version {self.version}\n{self.config.company_name}\n{self.config.copyright}", objectName="muted"))
        box.addSpacing(12); box.addWidget(QLabel("Application Updates", objectName="sectionTitle"))
        creator=QLabel('Software created by <b>Yohan Dananjaya</b><br><a href="https://github.com/yohandananjaya16">github.com/yohandananjaya16</a>');creator.setOpenExternalLinks(True);box.addWidget(creator)
        auto = QCheckBox("Check automatically when CheqMint starts"); auto.setChecked(self.preferences.get_bool("automatic_update_check")); auto.toggled.connect(lambda value: self.preferences.set("automatic_update_check", value)); box.addWidget(auto)
        check = QPushButton("Check for Updates"); check.clicked.connect(lambda: self.check_updates(True)); box.addWidget(check)
        layout.addWidget(info); layout.addStretch(); return page

    def open_folder(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True); QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _automatic_backup(self) -> None:
        folder=self.config.data_dir/"backups";folder.mkdir(parents=True,exist_ok=True);target=folder/f"automatic-{date.today().isoformat()}.zip"
        try:
            if not target.exists():
                with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as archive:
                    for item in self.config.data_dir.rglob("*"):
                        if item.is_file() and "backups" not in item.parts and "logs" not in item.parts and "updates" not in item.parts:archive.write(item,item.relative_to(self.config.data_dir))
            for old in sorted(folder.glob("automatic-*.zip"))[:-30]:old.unlink()
            drive=Path(str(self.preferences.values.get("google_drive_folder","")))
            if self.preferences.get_bool("google_drive_backup") and drive.is_dir():drive.mkdir(parents=True,exist_ok=True);shutil.copy2(target,drive/target.name)
        except OSError: LOGGER.exception("Automatic backup failed")

    def _show_due_reminder(self) -> None:
        today=date.today().isoformat();active=[x for x in self.history_store.list() if x.status=="Issued"];due=sum(x.cheque_date==today for x in active);overdue=sum(x.cheque_date<today for x in active)
        if due or overdue:QMessageBox.information(self,"Cheque Reminder",f"Due today: {due}\nOverdue: {overdue}\nOpen Cheque History to review them.")

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
            answer = QMessageBox.question(self, "Ready to Install", "The update was verified. CheqMint will close, install the update, and restart. Continue?")
            if answer == QMessageBox.Yes:
                LOGGER.info("Launching verified installer %s", target)
                self.preferences.set("pending_update_version", info.version)
                launch_installer(target)
                QApplication.instance().quit()
        elif dialog.error:
            LOGGER.error("Update download failed: %s", dialog.error)
            QMessageBox.critical(self, "Update Failed", dialog.error + "\n\nCheqMint was not changed.")

