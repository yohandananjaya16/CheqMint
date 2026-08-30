from __future__ import annotations
import html, shutil, zipfile
from datetime import date, datetime
from pathlib import Path
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (QComboBox,QDateEdit,QDialog,QDoubleSpinBox,QFileDialog,QFormLayout,QFrame,QHBoxLayout,QInputDialog,QLabel,QLineEdit,QListWidget,QMessageBox,QPushButton,QSpinBox,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget)
from app.services.bank_accounts import BankAccount,BankAccountStore,CalibrationStore,PrinterCalibration
from app.services.cheque_templates import TemplateStore
from app.services.print_history import PrintHistoryStore
from app.services.profile import ProfileStore,UserProfile

class ProfilePage(QWidget):
    def __init__(self,store:ProfileStore,parent=None):
        super().__init__(parent);self.store=store;l=QVBoxLayout(self);l.setContentsMargins(44,38,44,38);l.addWidget(QLabel("User Profile",objectName="pageTitle"));card=QFrame(objectName="card");f=QFormLayout(card);p=store.load();self.user=QLineEdit(p.user_name);self.full=QLineEdit(p.full_name);self.company=QLineEdit(p.company_name);self.email=QLineEdit(p.email)
        for a,b in (("User name *",self.user),("Full name",self.full),("Company",self.company),("Email",self.email)):f.addRow(a,b)
        save=QPushButton("Save Profile");save.clicked.connect(self.save);f.addRow(save);l.addWidget(card);l.addStretch()
    def save(self):
        name=self.user.text().strip()
        if not name:QMessageBox.warning(self,"Profile","Enter a user name.");return
        self.store.save(UserProfile(name,self.full.text().strip(),self.company.text().strip(),self.email.text().strip()));QMessageBox.information(self,"Profile","Profile saved.")

class AccountDialog(QDialog):
    def __init__(self,banks:TemplateStore,item:BankAccount|None=None,parent=None):
        super().__init__(parent); self.setWindowTitle("Bank Account"); f=QFormLayout(self); item=item or BankAccount("","Generic Bank Cheque")
        self.name=QLineEdit(item.name); self.bank=QComboBox(); [self.bank.addItem(x.name) for x in banks.list()]; self.bank.setCurrentText(item.bank_template); self.number=QLineEdit(item.account_number); self.branch=QLineEdit(item.branch); self.currency=QLineEdit(item.currency); self.next=QSpinBox(); self.next.setRange(1,999999999); self.next.setValue(item.next_cheque_number); self.leaves=QSpinBox(); self.leaves.setRange(0,10000); self.leaves.setValue(item.remaining_leaves)
        for a,b in (("Account name *",self.name),("Cheque format",self.bank),("Account number",self.number),("Branch",self.branch),("Currency",self.currency),("Next cheque number",self.next),("Remaining leaves",self.leaves)):f.addRow(a,b)
        save=QPushButton("Save"); save.clicked.connect(self.accept); f.addRow(save)
    def result(self):return BankAccount(self.name.text().strip(),self.bank.currentText(),self.number.text().strip(),self.branch.text().strip(),self.currency.text().strip() or "LKR",self.next.value(),self.leaves.value())

class BankAccountsPage(QWidget):
    def __init__(self,store,banks,calibrations,changed,parent=None):
        super().__init__(parent); self.store,self.banks,self.calibrations,self.changed=store,banks,calibrations,changed; l=QVBoxLayout(self); l.setContentsMargins(44,38,44,38); l.addWidget(QLabel("Bank Accounts & Cheque Books",objectName="pageTitle")); self.items=QListWidget(); l.addWidget(self.items); a=QHBoxLayout()
        for text,fn,obj in (("Add Account",self.add,""),("Edit",self.edit,"secondary"),("Delete",self.delete,"danger"),("Printer Calibration",self.calibrate,"secondary")):
            b=QPushButton(text,objectName=obj); b.clicked.connect(fn); a.addWidget(b)
        l.addLayout(a); self.reload()
    def reload(self):
        self.items.clear()
        for x in self.store.list(): self.items.addItem(f"{x.name} | {x.bank_template} | ••••{x.account_number[-4:]} | Next: {x.next_cheque_number} | Leaves: {x.remaining_leaves}"); self.items.item(self.items.count()-1).setData(Qt.UserRole,x)
    def add(self):
        d=AccountDialog(self.banks,parent=self)
        if d.exec() and d.result().name:self.store.save(d.result());self.reload();self.changed()
    def edit(self):
        if not self.items.currentItem():return
        old=self.items.currentItem().data(Qt.UserRole);d=AccountDialog(self.banks,old,self)
        if d.exec() and d.result().name:self.store.save(d.result(),old.name);self.reload();self.changed()
    def delete(self):
        if not self.items.currentItem():return
        x=self.items.currentItem().data(Qt.UserRole)
        if QMessageBox.question(self,"Delete",f"Delete account '{x.name}'?")==QMessageBox.Yes:self.store.delete(x.name);self.reload();self.changed()
    def calibrate(self):
        name,ok=QInputDialog.getText(self,"Printer Calibration","Printer name (exact Windows name):")
        if not ok or not name:return
        old=self.calibrations.get(name); x,ok=QInputDialog.getDouble(self,"Horizontal Offset","X offset (mm):",old.x_offset_mm,-50,50,1)
        if not ok:return
        y,ok=QInputDialog.getDouble(self,"Vertical Offset","Y offset (mm):",old.y_offset_mm,-50,50,1)
        if ok:
            self.calibrations.save(PrinterCalibration(name,x,y))
            if QMessageBox.question(self,"Calibration Saved","Create a plain-paper calibration test PDF now?")==QMessageBox.Yes:
                p,_=QFileDialog.getSaveFileName(self,"Calibration Test","calibration-test.pdf","PDF (*.pdf)")
                if p:
                    doc=QTextDocument();doc.setDefaultFont(QFont("DejaVu Sans"));doc.setHtml("<h1>CheqMint Printer Calibration</h1><p>Print at 100% / Actual Size.</p><hr><h2>TOP LEFT REFERENCE</h2><p>Measure the horizontal and vertical difference from the expected cheque origin, then enter those millimetres as offsets.</p><hr><p>Printer: "+html.escape(name)+f"</p><p>Current offset: X {x:.1f} mm, Y {y:.1f} mm</p>");pr=QPrinter();pr.setOutputFormat(QPrinter.PdfFormat);pr.setOutputFileName(p);doc.print_(pr)

class HistoryPage(QWidget):
    def __init__(self,store:PrintHistoryStore,reprint,parent=None):
        super().__init__(parent);self.store,self.reprint=store,reprint;l=QVBoxLayout(self);l.setContentsMargins(30,28,30,28);l.addWidget(QLabel("Cheque History",objectName="pageTitle")); filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText("Search bank, account, cheque no, payee or user");self.search.textChanged.connect(self.reload);self.status=QComboBox();self.status.addItems(("All Statuses","Issued","Cleared","Cancelled"));self.status.currentTextChanged.connect(self.reload);filters.addWidget(self.search);filters.addWidget(self.status);l.addLayout(filters);self.table=QTableWidget(0,10);self.table.setHorizontalHeaderLabels(("Printed","Cheque Date","Bank","Account","Cheque No","Payee","Amount","Payment Type","Status","Printed By"));l.addWidget(self.table);a=QHBoxLayout();
        for text,fn,obj in (("Edit Record",self.edit,"secondary"),("Change Status",self.change,"secondary"),("Reprint",self.do_reprint,""),("Delete Record",self.delete,"danger")):
            b=QPushButton(text,objectName=obj);b.clicked.connect(fn);a.addWidget(b)
        l.addLayout(a);self.reload()
    def reload(self):
        q=self.search.text().casefold() if hasattr(self,"search") else ""; status=self.status.currentText() if hasattr(self,"status") else "All Statuses";items=[]
        for x in reversed(self.store.list()):
            if q not in " ".join((x.bank,x.account,x.cheque_number,x.payee,x.printed_by)).casefold() or (status!="All Statuses" and x.status!=status):continue
            items.append(x)
        self.table.setRowCount(len(items))
        for r,x in enumerate(items):
            vals=(x.printed_at,x.cheque_date,x.bank,x.account,x.cheque_number,x.payee,f"{x.amount:,.2f}",x.payment_type,x.status,x.printed_by)
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem(str(v)))
            self.table.item(r,0).setData(Qt.UserRole,x)
    def selected(self):return self.table.item(self.table.currentRow(),0).data(Qt.UserRole) if self.table.currentRow()>=0 else None
    def change(self):
        x=self.selected();
        if not x:return
        status,ok=QInputDialog.getItem(self,"Cheque Status","Status:",( "Issued","Cleared","Cancelled"),editable=False)
        if ok:self.store.update_status(x.printed_at,status);self.reload()
    def edit(self):
        x=self.selected()
        if not x:return
        payee,ok=QInputDialog.getText(self,"Edit Cheque","Payee:",text=x.payee)
        if not ok:return
        amount,ok=QInputDialog.getDouble(self,"Edit Cheque","Amount:",x.amount,0,999999999,2)
        if not ok:return
        number,ok=QInputDialog.getText(self,"Edit Cheque","Cheque number:",text=x.cheque_number)
        if ok:x.payee=payee.strip();x.amount=amount;x.cheque_number=number.strip();self.store.update(x);self.reload()
    def delete(self):
        x=self.selected();
        if x and QMessageBox.question(self,"Delete Record","Delete this history record?")==QMessageBox.Yes:self.store.delete(x.printed_at);self.reload()
    def do_reprint(self):
        x=self.selected()
        if x:self.reprint(x)

class ReportsPage(QWidget):
    def __init__(self,history:PrintHistoryStore,profile:ProfileStore,parent=None):
        super().__init__(parent);self.history,self.profile=history,profile;l=QVBoxLayout(self);l.setContentsMargins(44,38,44,38);l.addWidget(QLabel("Reports & Export",objectName="pageTitle"));f=QFormLayout();self.start=QDateEdit(QDate.currentDate().addMonths(-1));self.end=QDateEdit(QDate.currentDate());self.start.dateChanged.connect(self.refresh);self.end.dateChanged.connect(self.refresh);f.addRow("From",self.start);f.addRow("To",self.end);l.addLayout(f);self.summary=QLabel();self.summary.setWordWrap(True);self.summary.setObjectName("amountWords");l.addWidget(self.summary);a=QHBoxLayout();csv=QPushButton("Export CSV");csv.clicked.connect(self.csv);pdf=QPushButton("Export PDF");pdf.clicked.connect(self.pdf);a.addWidget(csv);a.addWidget(pdf);l.addLayout(a);l.addStretch();self.refresh()
    def records(self):return [x for x in self.history.list() if self.start.date().toString("yyyy-MM-dd")<=x.cheque_date<=self.end.date().toString("yyyy-MM-dd")]
    def refresh(self):
        items=self.records();banks={};suppliers={}
        for x in items:banks[x.bank]=banks.get(x.bank,0)+x.amount;suppliers[x.payee]=suppliers.get(x.payee,0)+x.amount
        self.summary.setText(f"Cheques: {len(items)}    Total: Rs. {sum(x.amount for x in items):,.2f}\nBanks: "+", ".join(f"{k} ({v:,.2f})" for k,v in sorted(banks.items()))+"\nSuppliers: "+", ".join(f"{k} ({v:,.2f})" for k,v in sorted(suppliers.items())))
    def csv(self):
        p,_=QFileDialog.getSaveFileName(self,"Export Report","cheque-report.csv","CSV (*.csv)");
        if not p:return
        import csv
        with open(p,"w",newline="",encoding="utf-8-sig") as f:w=csv.writer(f);w.writerow(("Date","Bank","Account","Cheque No","Payee","Amount","Payment Type","Status","Printed By"));[w.writerow((x.cheque_date,x.bank,x.account,x.cheque_number,x.payee,f"{x.amount:.2f}",x.payment_type,x.status,x.printed_by or self.profile.load().user_name)) for x in self.records()]
    def pdf(self):
        p,_=QFileDialog.getSaveFileName(self,"Export PDF","cheque-report.pdf","PDF (*.pdf)");
        if not p:return
        rows="".join(f"<tr><td>{html.escape(x.cheque_date)}</td><td>{html.escape(x.bank)}</td><td>{html.escape(x.cheque_number)}</td><td>{html.escape(x.payee)}</td><td>{x.amount:,.2f}</td><td>{html.escape(x.status)}</td><td>{html.escape(x.printed_by or self.profile.load().user_name)}</td></tr>" for x in self.records());doc=QTextDocument();doc.setDefaultFont(QFont("DejaVu Sans"));doc.setHtml(f"<h1>CheqMint Cheque Report</h1><p>Exported by: {html.escape(self.profile.load().user_name)}</p><p>{self.start.date().toString('yyyy-MM-dd')} to {self.end.date().toString('yyyy-MM-dd')}</p><table border='1' cellspacing='0' cellpadding='5'><tr><th>Date</th><th>Bank</th><th>No</th><th>Payee</th><th>Amount</th><th>Status</th><th>User</th></tr>{rows}</table>");pr=QPrinter();pr.setOutputFormat(QPrinter.PdfFormat);pr.setOutputFileName(p);doc.print_(pr);QMessageBox.information(self,"Exported",f"PDF report saved to:\n{p}")

class BackupPage(QWidget):
    def __init__(self,data_dir:Path,parent=None):
        super().__init__(parent);self.data_dir=data_dir;l=QVBoxLayout(self);l.setContentsMargins(44,38,44,38);l.addWidget(QLabel("Backup & Restore",objectName="pageTitle"));l.addWidget(QLabel("Backup banks, accounts, suppliers, templates, settings and cheque history."));b=QPushButton("Create Backup");b.clicked.connect(self.backup);r=QPushButton("Restore Backup",objectName="danger");r.clicked.connect(self.restore);l.addWidget(b);l.addWidget(r);l.addStretch()
    def backup(self):
        p,_=QFileDialog.getSaveFileName(self,"Create Backup",f"CheqMint-backup-{date.today()}.zip","ZIP (*.zip)");
        if not p:return
        with zipfile.ZipFile(p,"w",zipfile.ZIP_DEFLATED) as z:
            for x in self.data_dir.rglob("*"):
                if x.is_file() and "logs" not in x.parts and "updates" not in x.parts:z.write(x,x.relative_to(self.data_dir))
        QMessageBox.information(self,"Backup Complete",p)
    def restore(self):
        p,_=QFileDialog.getOpenFileName(self,"Restore Backup","","ZIP (*.zip)");
        if not p:return
        if QMessageBox.question(self,"Restore","Replace current local data with this backup? Restart CheqMint afterwards.")!=QMessageBox.Yes:return
        with zipfile.ZipFile(p) as z:
            if any(Path(n).is_absolute() or ".." in Path(n).parts for n in z.namelist()):raise ValueError("Unsafe backup")
            z.extractall(self.data_dir)
        QMessageBox.information(self,"Restore Complete","Backup restored. Restart CheqMint.")

