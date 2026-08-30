import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QApplication

from app.services.amount_words import amount_to_words
from app.services.cheque_templates import ChequeTemplate, TemplateStore
from app.services.suppliers import Supplier, SupplierStore
from app.services.print_history import PrintHistoryStore
from app.services.bank_accounts import BankAccount, BankAccountStore, CalibrationStore, PrinterCalibration
from app.services.profile import ProfileStore,UserProfile
from app.services.preferences import Preferences
from app.ui.cheque_page import ChequeCanvas, format_cheque_date, split_words


class ChequeTests(unittest.TestCase):
    def test_amount_to_words(self) -> None:
        self.assertEqual(amount_to_words(1250), "One Thousand Two Hundred Fifty Rupees Only")
        self.assertEqual(amount_to_words(10.25), "Ten Rupees and Twenty Five Cents Only")

    def test_words_split_without_losing_text(self) -> None:
        text = amount_to_words(123456789.50)
        first, second = split_words(text, 50)
        self.assertEqual(f"{first} {second}".strip(), text)

    def test_bank_templates_are_installed_without_overwriting_edits(self) -> None:
        with TemporaryDirectory() as directory:
            store = TemplateStore(Path(directory))
            names = {template.name for template in store.list()}
            self.assertTrue({"Generic Bank Cheque", "Commercial Bank - Standard", "Seylan Bank - Standard"} <= names)
            edited = ChequeTemplate.default("Commercial Bank - Standard")
            edited.width_mm = 210
            store.save(edited)
            TemplateStore(Path(directory))
            loaded = {template.name: template for template in store.list()}
            self.assertEqual(loaded["Commercial Bank - Standard"].width_mm, 210)

    def test_boxed_date_has_eight_spaced_digits(self) -> None:
        self.assertEqual(format_cheque_date(QDate(2026, 8, 29), "boxed"), "2  9  0  8  2  0  2  6")

    def test_cheque_canvas_can_render_a_pdf_print_job(self) -> None:
        app = QApplication.instance() or QApplication([])
        with TemporaryDirectory() as directory:
            target = Path(directory) / "cheque.pdf"
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(str(target))
            canvas = ChequeCanvas()
            canvas.set_content(ChequeTemplate.default(), {"payee": "Test Payee", "amount": "1,250.00"})
            self.assertTrue(canvas.print_to(printer))
            self.assertGreater(target.stat().st_size, 100)
        self.assertIsNotNone(app)

    def test_bank_delete_remains_deleted_after_restart(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory)
            store = TemplateStore(path); store.delete("Seylan Bank - Standard")
            names = {item.name for item in TemplateStore(path).list()}
            self.assertNotIn("Seylan Bank - Standard", names)

    def test_supplier_add_edit_delete_persistence(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "suppliers.json"
            store = SupplierStore(path); store.save(Supplier("ABC Traders", "SUP-01", "Colombo"))
            self.assertEqual(SupplierStore(path).list()[0].reference, "SUP-01")
            store.save(Supplier("ABC Trading", "SUP-02"), "ABC Traders")
            self.assertEqual([item.name for item in store.list()], ["ABC Trading"])
            store.delete("ABC Trading")
            self.assertEqual(store.list(), [])

    def test_print_history_summary_and_daily_csv(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory); store = PrintHistoryStore(root / "history.json")
            store.record("Commercial Bank", "ABC Traders", 1250.50, "2026-08-30")
            store.record("Commercial Bank", "XYZ Supplies", 500, "2026-08-30")
            summary = store.summary(date.today())
            self.assertEqual(summary["today_count"], 2); self.assertEqual(summary["total_count"], 2)
            self.assertEqual(summary["by_bank"], {"Commercial Bank": 2})
            target = root / "daily.csv"; self.assertEqual(store.export_day_csv(target, date.today()), 2)
            content = target.read_text(encoding="utf-8-sig"); self.assertIn("ABC Traders", content); self.assertIn("1250.50", content)

    def test_cheque_book_and_printer_calibration_persistence(self) -> None:
        with TemporaryDirectory() as directory:
            root=Path(directory); accounts=BankAccountStore(root/"accounts.json")
            accounts.save(BankAccount("Main Account","Commercial Bank", "123456",next_cheque_number=100,remaining_leaves=25));accounts.use_cheque("Main Account")
            item=BankAccountStore(root/"accounts.json").list()[0];self.assertEqual((item.next_cheque_number,item.remaining_leaves),(101,24))
            calibration=CalibrationStore(root/"calibration.json");calibration.save(PrinterCalibration("Test Printer",1.5,-2.0));self.assertEqual(calibration.get("Test Printer").y_offset_mm,-2.0)

    def test_user_profile_and_printed_by_csv(self) -> None:
        with TemporaryDirectory() as directory:
            root=Path(directory);profiles=ProfileStore(root/"profile.json");profiles.save(UserProfile("Nimal","Nimal Silva","ABC Pvt Ltd"));self.assertEqual(ProfileStore(root/"profile.json").load().user_name,"Nimal")
            history=PrintHistoryStore(root/"history.json");history.record("Bank","Supplier",100,"2026-08-30",printed_by="Nimal");target=root/"report.csv";history.export_day_csv(target,date.today());self.assertIn("Nimal",target.read_text(encoding="utf-8-sig"))

    def test_supplier_suggestions_default_and_cash_payment_export(self) -> None:
        with TemporaryDirectory() as directory:
            root=Path(directory);self.assertTrue(Preferences(root/"settings.json").get_bool("supplier_auto_suggest"))
            history=PrintHistoryStore(root/"history.json");history.record("Bank","CASH",500,"2026-08-30",printed_by="Nimal",payment_type="Cash / Bearer");target=root/"cash.csv";history.export_day_csv(target,date.today());content=target.read_text(encoding="utf-8-sig");self.assertIn("Cash / Bearer",content);self.assertIn("Printed By",content)


if __name__ == "__main__": unittest.main()

