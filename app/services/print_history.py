from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass
class PrintRecord:
    printed_at: str
    cheque_date: str
    bank: str
    payee: str
    amount: float
    cheque_number: str = ""
    account: str = ""
    status: str = "Issued"
    printed_by: str = ""
    payment_type: str = "A/C Payee"


class PrintHistoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path; path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists(): self._write([])

    def list(self) -> list[PrintRecord]:
        try:
            return [PrintRecord(**item) for item in json.loads(self.path.read_text(encoding="utf-8"))]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return []

    def record(self, bank: str, payee: str, amount: float, cheque_date: str, cheque_number: str="", account: str="", printed_by: str="", payment_type: str="A/C Payee") -> PrintRecord:
        item = PrintRecord(datetime.now().isoformat(timespec="seconds"), cheque_date, bank, payee, float(amount),cheque_number,account,"Issued",printed_by,payment_type)
        records = self.list(); records.append(item); self._write(records); return item

    def for_day(self, day: date) -> list[PrintRecord]:
        prefix = day.isoformat()
        return [item for item in self.list() if item.printed_at.startswith(prefix)]

    def summary(self, day: date | None = None) -> dict[str, object]:
        all_records = self.list(); today_records = self.for_day(day or date.today()); by_bank: dict[str, int] = {}
        for item in all_records: by_bank[item.bank] = by_bank.get(item.bank, 0) + 1
        return {"today_count": len(today_records), "total_count": len(all_records),
                "today_amount": sum(item.amount for item in today_records), "by_bank": by_bank}

    def export_day_csv(self, target: Path, day: date) -> int:
        records = self.for_day(day); target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle); writer.writerow(("Printed At","Cheque Date","Bank","Account","Cheque No","Payee","Amount","Status","Printed By","Payment Type"))
            for item in records: writer.writerow((item.printed_at,item.cheque_date,item.bank,item.account,item.cheque_number,item.payee,f"{item.amount:.2f}",item.status,item.printed_by,item.payment_type))
        return len(records)

    def update_status(self, printed_at: str, status: str) -> None:
        items=self.list()
        for x in items:
            if x.printed_at==printed_at:x.status=status
        self._write(items)
    def update(self, record: PrintRecord) -> None:
        items=self.list();items=[record if x.printed_at==record.printed_at else x for x in items];self._write(items)
    def delete(self,printed_at): self._write([x for x in self.list() if x.printed_at!=printed_at])

    def _write(self, records: list[PrintRecord]) -> None:
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps([asdict(item) for item in records], indent=2), encoding="utf-8"); temp.replace(self.path)

