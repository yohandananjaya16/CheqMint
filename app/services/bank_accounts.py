from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path

@dataclass
class BankAccount:
    name: str; bank_template: str; account_number: str = ""; branch: str = ""; currency: str = "LKR"
    next_cheque_number: int = 1; remaining_leaves: int = 0

class BankAccountStore:
    def __init__(self, path: Path): self.path=path; path.parent.mkdir(parents=True,exist_ok=True); (not path.exists()) and self._write([])
    def list(self):
        try: return sorted([BankAccount(**x) for x in json.loads(self.path.read_text(encoding="utf-8"))],key=lambda x:x.name.casefold())
        except (OSError,ValueError,TypeError,json.JSONDecodeError): return []
    def save(self,item:BankAccount,original:str|None=None):
        key=(original or item.name).casefold(); items=[x for x in self.list() if x.name.casefold() not in (key,item.name.casefold())]; items.append(item); self._write(items)
    def delete(self,name): self._write([x for x in self.list() if x.name.casefold()!=name.casefold()])
    def use_cheque(self,name):
        items=self.list()
        for x in items:
            if x.name==name: x.next_cheque_number+=1; x.remaining_leaves=max(0,x.remaining_leaves-1)
        self._write(items)
    def _write(self,items):
        t=self.path.with_suffix(".tmp"); t.write_text(json.dumps([asdict(x) for x in items],indent=2),encoding="utf-8"); t.replace(self.path)

@dataclass
class PrinterCalibration:
    printer: str; x_offset_mm: float=0; y_offset_mm: float=0

class CalibrationStore:
    def __init__(self,path:Path): self.path=path; path.parent.mkdir(parents=True,exist_ok=True)
    def list(self):
        try:return [PrinterCalibration(**x) for x in json.loads(self.path.read_text(encoding="utf-8"))]
        except (OSError,ValueError,TypeError,json.JSONDecodeError):return []
    def get(self,name): return next((x for x in self.list() if x.printer==name),PrinterCalibration(name))
    def save(self,item):
        items=[x for x in self.list() if x.printer!=item.printer]+[item]; t=self.path.with_suffix(".tmp"); t.write_text(json.dumps([asdict(x) for x in items],indent=2),encoding="utf-8"); t.replace(self.path)

