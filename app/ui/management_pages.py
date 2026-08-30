from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView,QFrame,QHeaderView,QHBoxLayout,QLabel,QListWidget,QMessageBox,
                               QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget)

from app.services.cheque_templates import ChequeTemplate, TemplateStore
from app.services.suppliers import SupplierStore
from app.ui.cheque_page import SupplierDialog, TemplateDialog


class BankManagementPage(QWidget):
    def __init__(self, store: TemplateStore, changed, parent=None) -> None:
        super().__init__(parent); self.store = store; self.changed = changed
        layout = QVBoxLayout(self); layout.setContentsMargins(44, 38, 44, 38); layout.setSpacing(16)
        layout.addWidget(QLabel("Bank Cheque Formats", objectName="pageTitle"))
        subtitle = QLabel("Add each bank once, then calibrate its cheque size and print positions in millimetres.", objectName="muted"); subtitle.setWordWrap(True); layout.addWidget(subtitle)
        card = QFrame(objectName="card"); box = QVBoxLayout(card); box.setContentsMargins(22, 20, 22, 20)
        self.items = QListWidget(); self.items.itemDoubleClicked.connect(lambda _: self.edit_bank()); box.addWidget(self.items)
        actions = QHBoxLayout(); add = QPushButton("Add Bank"); add.clicked.connect(self.add_bank); edit = QPushButton("Edit Format", objectName="secondary"); edit.clicked.connect(self.edit_bank); delete = QPushButton("Delete Bank", objectName="danger"); delete.clicked.connect(self.delete_bank)
        actions.addWidget(add); actions.addWidget(edit); actions.addWidget(delete); box.addLayout(actions); layout.addWidget(card, 1); self.reload()

    def reload(self, selected: str = "") -> None:
        self.items.clear()
        for template in self.store.list(): self.items.addItem(template.name); self.items.item(self.items.count()-1).setData(Qt.UserRole, template)
        matches = self.items.findItems(selected, Qt.MatchExactly)
        if matches: self.items.setCurrentItem(matches[0])

    def add_bank(self) -> None:
        dialog = TemplateDialog(ChequeTemplate.default("New Bank"), self)
        if not dialog.exec(): return
        result = dialog.result_template()
        if not result.name: QMessageBox.warning(self, "Bank", "Enter the bank name."); return
        if any(item.name.casefold() == result.name.casefold() for item in self.store.list()): QMessageBox.warning(self, "Bank", "A bank with this name already exists."); return
        self.store.save(result); self.reload(result.name); self.changed()

    def edit_bank(self) -> None:
        item = self.items.currentItem()
        if not item: return
        original = item.data(Qt.UserRole); dialog = TemplateDialog(original, self)
        if not dialog.exec(): return
        result = dialog.result_template()
        if not result.name: QMessageBox.warning(self, "Bank", "Enter the bank name."); return
        self.store.rename_save(original.name, result); self.reload(result.name); self.changed()

    def delete_bank(self) -> None:
        item = self.items.currentItem()
        if not item: return
        name = item.text()
        if QMessageBox.question(self, "Delete Bank", f"Delete bank format '{name}'?") != QMessageBox.Yes: return
        self.store.delete(name); self.reload(); self.changed()


class SupplierManagementPage(QWidget):
    def __init__(self, store: SupplierStore, changed, parent=None) -> None:
        super().__init__(parent); self.store = store; self.changed = changed
        layout = QVBoxLayout(self); layout.setContentsMargins(44, 38, 44, 38); layout.setSpacing(16)
        layout.addWidget(QLabel("Supplier Register", objectName="pageTitle"))
        layout.addWidget(QLabel("Save supplier names once and select them quickly when printing cheques.", objectName="muted"))
        card = QFrame(objectName="card"); box = QVBoxLayout(card); box.setContentsMargins(22, 20, 22, 20)
        self.items=QTableWidget(0,3);self.items.setHorizontalHeaderLabels(("Supplier Name","Reference / Code","Notes"));self.items.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.items.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeToContents);self.items.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch);self.items.setSelectionBehavior(QAbstractItemView.SelectRows);self.items.setAlternatingRowColors(True);self.items.verticalHeader().setVisible(False);box.addWidget(self.items)
        manage = QPushButton("Add / Edit / Delete Suppliers"); manage.clicked.connect(self.manage); box.addWidget(manage)
        layout.addWidget(card, 1); self.reload()

    def reload(self) -> None:
        suppliers=self.store.list();self.items.setRowCount(len(suppliers))
        for row,supplier in enumerate(suppliers):
            for col,value in enumerate((supplier.name,supplier.reference,supplier.notes)):self.items.setItem(row,col,QTableWidgetItem(value))

    def manage(self) -> None:
        SupplierDialog(self.store, self).exec(); self.reload(); self.changed()

