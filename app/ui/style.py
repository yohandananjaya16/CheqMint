LIGHT_STYLE = """
QWidget, QDialog, QMessageBox { font-family: 'Segoe UI'; font-size: 10pt; color: #172033; background-color: #f4f7fb; }
QLabel { background: transparent; }
QMainWindow, QWidget#root { background: #f4f7fb; }
QFrame#sidebar { background: #0b2347; border-radius: 0px; }
QLabel#brand { color: white; font-size: 18pt; font-weight: 700; }
QLabel#muted { color: #667085; }
QLabel#pageTitle { font-size: 22pt; font-weight: 700; }
QLabel#metricValue { font-size: 20pt; font-weight: 750; color: #0b6fa4; }
QFrame#card { background: white; border: 1px solid #e6eaf0; border-radius: 14px; }
QDialog, QMessageBox { background: white; }
QListWidget, QTableWidget, QPlainTextEdit { background: white; color: #172033; border: 1px solid #cfd7e3; border-radius: 8px; }
QPushButton { background: #0b6fa4; color: white; border: 0; border-radius: 8px; padding: 9px 16px; font-weight: 600; }
QPushButton:hover { background: #095d8a; }
QPushButton:disabled { background: #a8b3c2; }
QPushButton#nav { background: transparent; text-align: left; padding: 11px 16px; color: #d6e3f5; }
QPushButton#nav:hover { background: #16365f; }
QPushButton#secondary { background: #e8eef5; color: #24324a; }
QProgressBar { border: 0; border-radius: 6px; background: #e8edf3; height: 12px; text-align: center; }
QProgressBar::chunk { border-radius: 6px; background: #15a9a1; }
QCheckBox { spacing: 8px; }
QCheckBox#themeSwitch::indicator { width: 46px; height: 24px; border-radius: 12px; background: #cbd5e1; }
QCheckBox#themeSwitch::indicator:checked { background: #0b6fa4; }
QGroupBox { border: 1px solid #e2e8f0; border-radius: 10px; margin-top: 12px; padding: 14px 10px 10px 10px; font-weight: 650; color: #344054; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; background: white; }
QLineEdit, QDateEdit, QDoubleSpinBox, QComboBox { background: #ffffff; color: #172033; border: 1px solid #cfd7e3; border-radius: 8px; padding: 9px 10px; min-height: 22px; selection-background-color: #0b6fa4; selection-color: white; }
QLineEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus, QComboBox:focus { border: 2px solid #0b6fa4; }
QComboBox QAbstractItemView { background: white; color: #172033; border: 1px solid #cfd7e3; selection-background-color: #dbeafe; selection-color: #172033; outline: 0; }
QComboBox::drop-down { border: 0; width: 28px; }
QCalendarWidget QWidget { background: white; color: #172033; }
QLabel#sectionTitle { font-size: 12pt; font-weight: 700; color: #344054; }
QLabel#amountWords { background: #f0f9ff; color: #075985; border: 1px solid #bae6fd; border-radius: 8px; padding: 11px; font-weight: 600; }
QLabel#warningNotice { background: #fff7ed; color: #9a3412; border: 1px solid #fed7aa; border-radius: 8px; padding: 10px 14px; font-weight: 650; }
QPushButton#primaryAction { background: #087f5b; }
QPushButton#primaryAction:hover { background: #066649; }
QPushButton#danger { background: #b42318; }
QPushButton#danger:hover { background: #912018; }
"""

DARK_STYLE = """
QWidget, QDialog, QMessageBox { font-family: 'Segoe UI'; font-size: 10pt; color: #e5e7eb; background-color: #111827; }
QLabel { background: transparent; }
QMainWindow, QWidget#root { background: #111827; }
QFrame#sidebar { background: #07152d; border-radius: 0px; }
QLabel#brand { color: white; font-size: 18pt; font-weight: 700; }
QLabel#muted { color: #9ca3af; }
QLabel#pageTitle { color: #f9fafb; font-size: 22pt; font-weight: 700; }
QLabel#metricValue { font-size: 20pt; font-weight: 750; color: #38bdf8; }
QFrame#card { background: #1f2937; border: 1px solid #374151; border-radius: 14px; }
QPushButton { background: #1677a8; color: white; border: 0; border-radius: 8px; padding: 9px 16px; font-weight: 600; }
QPushButton:hover { background: #238abc; }
QPushButton#nav { background: transparent; text-align: left; padding: 11px 16px; color: #d6e3f5; }
QPushButton#nav:hover { background: #16365f; }
QPushButton#secondary { background: #374151; color: #f3f4f6; }
QPushButton#danger { background: #b42318; }
QPushButton#primaryAction { background: #087f5b; }
QCheckBox#themeSwitch::indicator { width: 46px; height: 24px; border-radius: 12px; background: #4b5563; }
QCheckBox#themeSwitch::indicator:checked { background: #38bdf8; }
QGroupBox { border: 1px solid #4b5563; border-radius: 10px; margin-top: 12px; padding: 14px 10px 10px 10px; font-weight: 650; color: #e5e7eb; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; background: #1f2937; }
QLineEdit, QDateEdit, QDoubleSpinBox, QComboBox, QListWidget, QTableWidget, QPlainTextEdit { background: #111827; color: #f3f4f6; border: 1px solid #4b5563; border-radius: 8px; padding: 9px 10px; selection-background-color: #1677a8; selection-color: white; }
QComboBox QAbstractItemView { background: #1f2937; color: #f3f4f6; selection-background-color: #374151; selection-color: white; }
QCalendarWidget QWidget { background: #1f2937; color: #f3f4f6; }
QLabel#sectionTitle { font-size: 12pt; font-weight: 700; color: #e5e7eb; }
QLabel#amountWords { background: #0c4a6e; color: #e0f2fe; border-radius: 8px; padding: 11px; font-weight: 600; }
QLabel#warningNotice { background: #431407; color: #fed7aa; border-radius: 8px; padding: 10px 14px; }
"""

STYLE = LIGHT_STYLE

