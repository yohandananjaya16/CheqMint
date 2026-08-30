from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Supplier:
    name: str
    reference: str = ""
    notes: str = ""


class SupplierStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            self._write([])

    def list(self) -> list[Supplier]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return sorted((Supplier(**item) for item in raw), key=lambda item: item.name.casefold())
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return []

    def save(self, supplier: Supplier, original_name: str | None = None) -> None:
        suppliers = self.list()
        key = (original_name or supplier.name).casefold()
        suppliers = [item for item in suppliers if item.name.casefold() != key]
        suppliers = [item for item in suppliers if item.name.casefold() != supplier.name.casefold()]
        suppliers.append(supplier)
        self._write(sorted(suppliers, key=lambda item: item.name.casefold()))

    def delete(self, name: str) -> None:
        self._write([item for item in self.list() if item.name.casefold() != name.casefold()])

    def _write(self, suppliers: list[Supplier]) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps([asdict(item) for item in suppliers], indent=2), encoding="utf-8")
        temporary.replace(self.path)

