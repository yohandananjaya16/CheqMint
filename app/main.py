from __future__ import annotations

import logging
import sys
import traceback
import ctypes

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox

from app.config import load_config, load_version
from app.config.settings import resource_path
from app.services.preferences import Preferences
from app.ui.main_window import MainWindow
from app.ui.style import STYLE
from app.utils.logging import configure_logging


def main() -> int:
    config, version = load_config(), load_version()
    config.data_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(config.logs_dir)
    logging.info("Starting %s %s", config.application_name, version)
    app = QApplication(sys.argv)
    app.setApplicationName(config.application_name); app.setOrganizationName(config.company_name); app.setStyleSheet(STYLE)
    lock = QLockFile(str(config.data_dir / "application.lock"))
    lock.setStaleLockTime(30_000)
    if not lock.tryLock(100):
        handle = ctypes.windll.user32.FindWindowW(None, config.application_name)
        if handle:
            ctypes.windll.user32.ShowWindow(handle, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(handle)
        return 0

    def handle_exception(exc_type, exc_value, exc_tb) -> None:
        logging.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        QMessageBox.critical(None, "Unexpected Error", "LedgerDesk encountered an unexpected error. Details were saved to the log.")

    sys.excepthook = handle_exception
    preferences = Preferences(config.data_dir / "settings.json", config.update_check_enabled)
    window = MainWindow(config, version, preferences, resource_path("assets/app.ico"))
    window.show()
    result = app.exec(); lock.unlock(); return result


if __name__ == "__main__":
    raise SystemExit(main())

