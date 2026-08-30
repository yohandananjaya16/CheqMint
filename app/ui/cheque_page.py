from __future__ import annotations

import logging
from datetime import date

from PySide6.QtCore import QDate, QMarginsF, QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPageLayout, QPageSize, QPen
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import (QCheckBox, QComboBox, QCompleter, QDateEdit, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                               QGroupBox, QHeaderView, QLabel, QLineEdit, QListWidget, QMessageBox,
                               QPlainTextEdit, QPushButton, QRadioButton, QScrollArea, QSizePolicy, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from app.services.amount_words import amount_to_words
from app.services.cheque_templates import ChequeTemplate, FieldPosition, TemplateStore
from app.services.suppliers import Supplier, SupplierStore
from app.services.print_history import PrintHistoryStore
from app.services.bank_accounts import BankAccountStore, CalibrationStore
from app.services.profile import ProfileStore
from app.services.preferences import Preferences

LOGGER = logging.getLogger(__name__)
FIELD_LABELS = {"date": "Date", "payee": "Payee", "amount_words_1": "Amount words line 1",
                "amount_words_2": "Amount words line 2", "amount": "Numeric amount",
                "account_payee": "A/C Payee marking"}


def format_cheque_date(value: QDate, style: str) -> str:
    digits = value.toString("ddMMyyyy")
    return "  ".join(digits) if style == "boxed" else value.toString("dd/MM/yyyy")


def split_words(text: str, limit: int = 66) -> tuple[str, str]:
    if len(text) <= limit: return text, ""
    point = text.rfind(" ", 0, limit)
    if point < 1: point = limit
    return text[:point], text[point:].strip()


class ChequeCanvas(QWidget):
    def __init__(self) -> None:
        super().__init__(); self.template = ChequeTemplate.default(); self.values: dict[str, str] = {}; self.print_offset=(0.0,0.0); self.setMinimumHeight(300)

    def set_content(self, template: ChequeTemplate, values: dict[str, str]) -> None:
        self.template, self.values = template, values; self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        margin = 18; scale = min((self.width()-2*margin)/self.template.width_mm, (self.height()-2*margin)/self.template.height_mm)
        left = (self.width()-self.template.width_mm*scale)/2; top = (self.height()-self.template.height_mm*scale)/2
        painter.fillRect(QRectF(left, top, self.template.width_mm*scale, self.template.height_mm*scale), QColor("white"))
        painter.setPen(QPen(QColor("#aab4c3"), 1)); painter.drawRoundedRect(QRectF(left, top, self.template.width_mm*scale, self.template.height_mm*scale), 7, 7)
        painter.setPen(QColor("#98a2b3")); label_font = QFont("Segoe UI"); label_font.setPixelSize(max(8, round(2.5*scale))); painter.setFont(label_font)
        painter.drawText(QRectF(left+8*scale, top+21*scale, 20*scale, 6*scale), Qt.AlignLeft, "PAY")
        painter.drawText(QRectF(left+8*scale, top+36*scale, 35*scale, 6*scale), Qt.AlignLeft, "RUPEES")
        painter.drawText(QRectF(left+145*scale, top+48*scale, 12*scale, 6*scale), Qt.AlignLeft, "Rs.")
        self._draw(painter, left, top, scale, show_guides=True, physical_print=False)

    def _draw(self, painter: QPainter, left: float, top: float, scale: float,
              show_guides: bool, physical_print: bool) -> None:
        for key, position in self.template.fields.items():
            value = self.values.get(key, "")
            font_pixels = max(1, round(position.font_pt * scale * 25.4 / 72.0))
            rect = QRectF(left+position.x_mm*scale, top+position.y_mm*scale, position.width_mm*scale, font_pixels*1.35)
            font = QFont("DejaVu Sans")
            font.setPixelSize(font_pixels)
            font.setWeight(QFont.Medium)
            painter.setFont(font)
            painter.setPen(QColor("#101828"))
            if physical_print:
                # Convert text to vector outlines so every Windows printer/PDF driver renders it identically.
                path = QPainterPath(); path.addText(rect.left(), rect.top() + font_pixels, font, value)
                painter.fillPath(path, QColor("#101828"))
            else:
                painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, value)
            if show_guides:
                painter.setPen(QPen(QColor(21,169,161,90), 1, Qt.DashLine)); painter.drawRect(rect)

    def print_to(self, printer: QPrinter) -> bool:
        painter = QPainter()
        if not painter.begin(printer):
            LOGGER.error("Printer painter could not be started")
            return False
        dpi = printer.resolution(); scale = dpi / 25.4
        self._draw(painter, self.print_offset[0]*scale, self.print_offset[1]*scale, scale, show_guides=False, physical_print=True)
        return painter.end()


class TemplateDialog(QDialog):
    def __init__(self, template: ChequeTemplate, parent=None) -> None:
        super().__init__(parent); self.template = template; self.setWindowTitle("Cheque Template Designer"); self.resize(760, 520)
        layout = QVBoxLayout(self); form = QFormLayout()
        self.name = QLineEdit(template.name); self.width = self._spin(template.width_mm, 100, 400); self.height = self._spin(template.height_mm, 50, 200)
        self.date_style = QComboBox(); self.date_style.addItem("Boxed digits (D D M M Y Y Y Y)", "boxed"); self.date_style.addItem("Slash date (DD/MM/YYYY)", "slash")
        self.date_style.setCurrentIndex(max(0, self.date_style.findData(template.date_style)))
        form.addRow("Bank / template name", self.name); form.addRow("Cheque width (mm)", self.width); form.addRow("Cheque height (mm)", self.height); form.addRow("Printed date style", self.date_style); layout.addLayout(form)
        self.table = QTableWidget(len(template.fields), 5); self.table.setHorizontalHeaderLabels(("Field", "X mm", "Y mm", "Width mm", "Font pt")); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, (key, pos) in enumerate(template.fields.items()):
            item = QTableWidgetItem(FIELD_LABELS.get(key, key)); item.setData(Qt.UserRole, key); self.table.setItem(row, 0, item)
            for col, value in enumerate((pos.x_mm, pos.y_mm, pos.width_mm, pos.font_pt), 1): self.table.setCellWidget(row, col, self._spin(value, 0, 400))
        layout.addWidget(QLabel("Positions are measured from the cheque's top-left corner.")); layout.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    @staticmethod
    def _spin(value: float, minimum: float, maximum: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox(); spin.setRange(minimum, maximum); spin.setDecimals(1); spin.setValue(value); return spin

    def result_template(self) -> ChequeTemplate:
        fields = {}
        for row in range(self.table.rowCount()):
            key = self.table.item(row, 0).data(Qt.UserRole); values = [self.table.cellWidget(row, col).value() for col in range(1, 5)]
            fields[key] = FieldPosition(*values)
        return ChequeTemplate(self.name.text().strip(), self.width.value(), self.height.value(), fields, self.date_style.currentData())


class SupplierDialog(QDialog):
    def __init__(self, store: SupplierStore, parent=None) -> None:
        super().__init__(parent); self.store = store; self.original_name: str | None = None
        self.setWindowTitle("Manage Suppliers"); self.resize(720, 480)
        layout = QHBoxLayout(self)
        left = QVBoxLayout(); left.addWidget(QLabel("Saved suppliers")); self.list_widget = QListWidget(); self.list_widget.currentRowChanged.connect(self.load_selected); left.addWidget(self.list_widget)
        layout.addLayout(left, 1)
        right = QVBoxLayout(); form = QFormLayout(); form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.name = QLineEdit(); self.reference = QLineEdit(); self.notes = QPlainTextEdit(); self.notes.setMaximumHeight(100)
        form.addRow("Supplier name *", self.name); form.addRow("Reference / code", self.reference); form.addRow("Notes", self.notes); right.addLayout(form)
        actions = QGridLayout(); add = QPushButton("Add New"); add.clicked.connect(self.clear_form); save = QPushButton("Save Supplier", objectName="primaryAction"); save.clicked.connect(self.save_supplier); delete = QPushButton("Delete", objectName="danger"); delete.clicked.connect(self.delete_supplier)
        actions.addWidget(add, 0, 0); actions.addWidget(save, 0, 1); actions.addWidget(delete, 1, 0, 1, 2); right.addLayout(actions); right.addStretch()
        close = QPushButton("Done", objectName="secondary"); close.clicked.connect(self.accept); right.addWidget(close); layout.addLayout(right, 2)
        self.reload()

    def reload(self, select_name: str = "") -> None:
        self.list_widget.clear()
        for supplier in self.store.list():
            self.list_widget.addItem(supplier.name); self.list_widget.item(self.list_widget.count()-1).setData(Qt.UserRole, supplier)
        matches = self.list_widget.findItems(select_name, Qt.MatchExactly)
        if matches: self.list_widget.setCurrentItem(matches[0])

    def load_selected(self, row: int) -> None:
        item = self.list_widget.item(row)
        if not item: return
        supplier = item.data(Qt.UserRole); self.original_name = supplier.name
        self.name.setText(supplier.name); self.reference.setText(supplier.reference); self.notes.setPlainText(supplier.notes)

    def clear_form(self) -> None:
        self.list_widget.clearSelection(); self.original_name = None; self.name.clear(); self.reference.clear(); self.notes.clear(); self.name.setFocus()

    def save_supplier(self) -> None:
        name = self.name.text().strip()
        if not name: QMessageBox.warning(self, "Supplier", "Enter the supplier name."); return
        self.store.save(Supplier(name, self.reference.text().strip(), self.notes.toPlainText().strip()), self.original_name)
        self.original_name = name; self.reload(name)

    def delete_supplier(self) -> None:
        if not self.original_name: return
        if QMessageBox.question(self, "Delete Supplier", f"Delete supplier '{self.original_name}'?") != QMessageBox.Yes: return
        self.store.delete(self.original_name); self.clear_form(); self.reload()


class ChequePage(QWidget):
    def __init__(self, store: TemplateStore, supplier_store: SupplierStore, history: PrintHistoryStore, accounts: BankAccountStore, calibrations: CalibrationStore, profile:ProfileStore, preferences:Preferences, parent=None) -> None:
        super().__init__(parent); self.store,self.supplier_store,self.history,self.accounts,self.calibrations,self.profile,self.preferences=store,supplier_store,history,accounts,calibrations,profile,preferences; self._build(); self.reload_templates(); self.reload_suppliers(); self.reload_accounts(); self.refresh_preview()

    def _build(self) -> None:
        root_layout = QVBoxLayout(self); root_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page = QWidget(); scroll.setWidget(page); root_layout.addWidget(scroll)
        layout = QVBoxLayout(page); layout.setContentsMargins(32, 28, 32, 28); layout.setSpacing(16)
        heading = QHBoxLayout(); heading.addWidget(QLabel("Cheque Printing", objectName="pageTitle")); heading.addStretch()
        clear = QPushButton("Clear Form", objectName="secondary"); clear.clicked.connect(self.clear_form); heading.addWidget(clear); layout.addLayout(heading)
        subtitle = QLabel("Fill the cheque details, verify the live preview, then print using a calibrated bank template.", objectName="muted"); subtitle.setWordWrap(True); layout.addWidget(subtitle)
        form_card = QFrame(objectName="card"); form_box = QVBoxLayout(form_card); form_box.setContentsMargins(22, 20, 22, 20); form_box.setSpacing(14)
        bank_group = QGroupBox("1. Bank template"); bank_form = QFormLayout(bank_group); bank_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.templates = QComboBox(); self.templates.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon); self.templates.setMinimumContentsLength(18); self.templates.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); self.templates.currentIndexChanged.connect(self.refresh_preview); bank_form.addRow("Template", self.templates)
        form_box.addWidget(bank_group)
        details_group = QGroupBox("2. Cheque details"); form = QFormLayout(details_group); form.setSpacing(12); form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.account=QComboBox();self.account.currentIndexChanged.connect(self.select_account);form.addRow("Bank account",self.account)
        self.cheque_number=QLineEdit();form.addRow("Cheque number",self.cheque_number)
        self.suppliers = QComboBox(); self.suppliers.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon); self.suppliers.setMinimumContentsLength(18); self.suppliers.currentIndexChanged.connect(self.select_supplier); form.addRow("Saved supplier", self.suppliers)
        self.payee = QLineEdit(); self.payee.setMinimumWidth(0); self.payee.setPlaceholderText("Enter person or company name"); self.payee.setClearButtonEnabled(True); self.payee.textChanged.connect(self.refresh_preview); form.addRow("Payee name *", self.payee)
        payment=QHBoxLayout();self.ac_mode=QRadioButton("A/C Payee");self.cash_mode=QRadioButton("Cash / Bearer");self.ac_mode.setChecked(True);self.ac_mode.toggled.connect(self.set_payment_mode);payment.addWidget(self.ac_mode);payment.addWidget(self.cash_mode);form.addRow("Payment type",payment)
        self.date = QDateEdit(QDate.currentDate()); self.date.setDisplayFormat("dd / MM / yyyy"); self.date.setCalendarPopup(True); self.date.dateChanged.connect(self.refresh_preview); form.addRow("Cheque date *", self.date)
        self.amount = QDoubleSpinBox(); self.amount.setPrefix("Rs.  "); self.amount.setRange(0, 999_999_999.99); self.amount.setDecimals(2); self.amount.setGroupSeparatorShown(True); self.amount.valueChanged.connect(self.refresh_preview); form.addRow("Amount *", self.amount)
        self.ac_payee = QCheckBox("Print A/C PAYEE ONLY marking"); self.ac_payee.setChecked(True); self.ac_payee.toggled.connect(self.refresh_preview); form.addRow("Security", self.ac_payee); form_box.addWidget(details_group)
        words_group = QGroupBox("Amount in words"); words_layout = QVBoxLayout(words_group); self.words_label = QLabel("Zero Rupees Only"); self.words_label.setWordWrap(True); self.words_label.setObjectName("amountWords"); words_layout.addWidget(self.words_label); form_box.addWidget(words_group)
        actions = QHBoxLayout(); preview = QPushButton("Print Preview"); preview.clicked.connect(self.print_preview); actions.addWidget(preview)
        print_button = QPushButton("Print Cheque"); print_button.setObjectName("primaryAction"); print_button.clicked.connect(self.print_cheque); actions.addWidget(print_button); form_box.addLayout(actions); form_box.addStretch()
        preview_card = QFrame(objectName="card"); preview_box = QVBoxLayout(preview_card); preview_box.setContentsMargins(20, 18, 20, 18); preview_box.addWidget(QLabel("Live cheque preview", objectName="sectionTitle")); self.canvas = ChequeCanvas(); preview_box.addWidget(self.canvas, 1)
        form_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        preview_card.setMinimumHeight(350)
        layout.addWidget(form_card); layout.addWidget(preview_card)
        notice = QLabel("TEST FIRST — Print on plain paper and overlay it on the cheque before printing a real cheque."); notice.setWordWrap(True); notice.setObjectName("warningNotice"); layout.addWidget(notice)

    def reload_templates(self) -> None:
        selected = self.templates.currentText(); self.templates.blockSignals(True); self.templates.clear()
        for template in self.store.list(): self.templates.addItem(template.name, template)
        index = self.templates.findText(selected); self.templates.setCurrentIndex(max(0, index)); self.templates.blockSignals(False)

    def reload_suppliers(self) -> None:
        selected = self.suppliers.currentText() if self.suppliers.count() else ""
        self.suppliers.blockSignals(True); self.suppliers.clear(); self.suppliers.addItem("Select a saved supplier…", None)
        for supplier in self.supplier_store.list(): self.suppliers.addItem(supplier.name, supplier)
        index = self.suppliers.findText(selected); self.suppliers.setCurrentIndex(max(0, index)); self.suppliers.blockSignals(False)
        self.refresh_supplier_suggestions()

    def refresh_supplier_suggestions(self):
        if self.preferences.get_bool("supplier_auto_suggest"):
            completer=QCompleter([x.name for x in self.supplier_store.list()],self);completer.setCaseSensitivity(Qt.CaseInsensitive);completer.setFilterMode(Qt.MatchContains);self.payee.setCompleter(completer)
        else:self.payee.setCompleter(None)

    def set_payment_mode(self,account_payee:bool):
        self.ac_payee.setChecked(account_payee);self.ac_payee.setEnabled(account_payee);self.suppliers.setEnabled(account_payee)
        if not account_payee:self._previous_payee=self.payee.text() if self.payee.text().upper()!="CASH" else "";self.payee.setText("CASH");self.payee.setEnabled(False)
        else:self.payee.setEnabled(True);self.payee.setText(getattr(self,"_previous_payee","") if self.payee.text().upper()=="CASH" else self.payee.text())
        self.refresh_preview()

    def reload_accounts(self):
        selected=self.account.currentText() if self.account.count() else "";self.account.blockSignals(True);self.account.clear();self.account.addItem("Select bank account…",None)
        for x in self.accounts.list():self.account.addItem(x.name,x)
        self.account.setCurrentIndex(max(0,self.account.findText(selected)));self.account.blockSignals(False)
    def select_account(self,index):
        x=self.account.itemData(index)
        if x:self.templates.setCurrentText(x.bank_template);self.cheque_number.setText(str(x.next_cheque_number))

    def select_supplier(self, index: int) -> None:
        supplier = self.suppliers.itemData(index)
        if supplier: self.payee.setText(supplier.name)

    def manage_suppliers(self) -> None:
        SupplierDialog(self.supplier_store, self).exec(); self.reload_suppliers()

    def current_template(self) -> ChequeTemplate:
        return self.templates.currentData() or ChequeTemplate.default()

    def values(self) -> dict[str, str]:
        words = amount_to_words(self.amount.value()); first, second = split_words(words)
        return {"date": format_cheque_date(self.date.date(), self.current_template().date_style), "payee": self.payee.text().strip(),
                "amount_words_1": first, "amount_words_2": second, "amount": f"{self.amount.value():,.2f}",
                "account_payee": "A/C PAYEE ONLY" if self.ac_payee.isChecked() else ""}

    def refresh_preview(self) -> None:
        if hasattr(self, "canvas"):
            values = self.values(); self.canvas.set_content(self.current_template(), values)
            self.words_label.setText((values["amount_words_1"] + " " + values["amount_words_2"]).strip())

    def clear_form(self) -> None:
        self.ac_mode.setChecked(True);self.payee.clear(); self.amount.setValue(0); self.date.setDate(QDate.currentDate()); self.ac_payee.setChecked(True); self.payee.setFocus()

    def edit_template(self) -> None:
        original_name = self.current_template().name; dialog = TemplateDialog(self.current_template(), self)
        if dialog.exec():
            template = dialog.result_template()
            if not template.name: QMessageBox.warning(self, "Template", "Enter a template name."); return
            self.store.rename_save(original_name, template); self.reload_templates(); self.templates.setCurrentText(template.name); self.refresh_preview()

    def add_template(self) -> None:
        template = ChequeTemplate.default("New Bank")
        dialog = TemplateDialog(template, self)
        if dialog.exec():
            result = dialog.result_template()
            if not result.name: QMessageBox.warning(self, "Bank", "Enter the bank name."); return
            if self.templates.findText(result.name) >= 0: QMessageBox.warning(self, "Bank", "A bank with this name already exists."); return
            self.store.save(result); self.reload_templates(); self.templates.setCurrentText(result.name); self.refresh_preview()

    def delete_template(self) -> None:
        if self.templates.count() == 0: return
        name = self.current_template().name
        if QMessageBox.question(self, "Delete Bank", f"Delete bank template '{name}'?") != QMessageBox.Yes: return
        self.store.delete(name); self.reload_templates(); self.refresh_preview()

    def _printer(self) -> QPrinter:
        printer = QPrinter(QPrinter.HighResolution); template = self.current_template(); printer.setFullPage(True)
        printer.setPageSize(QPageSize(QSizeF(template.width_mm, template.height_mm), QPageSize.Millimeter, template.name))
        printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Millimeter); return printer

    def _print_error(self) -> None:
        QMessageBox.critical(self, "Printing Error", "Windows could not start this print job. Check that a printer is installed and online, then try again.")

    def _validate(self) -> bool:
        if not self.payee.text().strip(): QMessageBox.warning(self, "Cheque", "Enter the payee name."); return False
        if self.amount.value() <= 0: QMessageBox.warning(self, "Cheque", "Enter an amount greater than zero."); return False
        number=self.cheque_number.text().strip()
        if number and any(x.cheque_number==number and x.account==(self.account.currentText() if self.account.currentData() else "") for x in self.history.list()): QMessageBox.warning(self,"Duplicate Cheque Number","This cheque number is already recorded for the selected account.");return False
        return True

    def print_preview(self) -> None:
        if not self._validate(): return
        # Keep both objects alive for the entire modal session. A temporary QPrinter can be
        # garbage-collected while Qt's preview dialog still holds its native pointer.
        printer = self._printer()
        if not printer.isValid(): self._print_error(); return
        preview = QPrintPreviewDialog(printer, self); preview.setWindowTitle("Cheque Print Preview")
        preview.resize(1000, 700); preview.paintRequested.connect(self.canvas.print_to)
        self._active_preview = (printer, preview)
        try:
            preview.exec()
        except Exception:
            LOGGER.exception("Cheque print preview failed"); self._print_error()
        finally:
            self._active_preview = None

    def print_cheque(self) -> None:
        if not self._validate(): return
        printer = self._printer()
        if not printer.isValid(): self._print_error(); return
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            calibration=self.calibrations.get(printer.printerName()); self.canvas.print_offset=(calibration.x_offset_mm,calibration.y_offset_mm)
            if not self.canvas.print_to(printer): self._print_error(); return
            account=self.account.currentText() if self.account.currentData() else "";payment_type="A/C Payee" if self.ac_mode.isChecked() else "Cash / Bearer";self.history.record(self.current_template().name,self.payee.text().strip(),self.amount.value(),self.date.date().toString("yyyy-MM-dd"),self.cheque_number.text().strip(),account,self.profile.load().user_name,payment_type)
            if account:self.accounts.use_cheque(account);self.reload_accounts()
            LOGGER.info("Cheque printed using template %s", self.current_template().name)
            QMessageBox.information(self, "Cheque Printed", "The cheque was sent to the printer.")

    def load_record(self,record):
        self.templates.setCurrentText(record.bank);self.account.setCurrentText(record.account);self.cheque_number.setText(record.cheque_number);self.cash_mode.setChecked(record.payment_type=="Cash / Bearer");self.payee.setText(record.payee);self.amount.setValue(record.amount);self.date.setDate(QDate.fromString(record.cheque_date,"yyyy-MM-dd"));self.refresh_preview()

