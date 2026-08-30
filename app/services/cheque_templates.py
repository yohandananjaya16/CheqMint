from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class FieldPosition:
    x_mm: float
    y_mm: float
    width_mm: float
    font_pt: float = 11.0


@dataclass
class ChequeTemplate:
    name: str
    width_mm: float = 203.0
    height_mm: float = 92.0
    fields: dict[str, FieldPosition] = field(default_factory=dict)
    date_style: str = "slash"

    @classmethod
    def default(cls, name: str = "Generic Bank Cheque") -> "ChequeTemplate":
        return cls(name=name, fields={
            "date": FieldPosition(157, 9, 39, 11),
            "payee": FieldPosition(28, 27, 158, 12),
            "amount_words_1": FieldPosition(16, 42, 170, 10),
            "amount_words_2": FieldPosition(16, 53, 137, 10),
            "amount": FieldPosition(154, 54, 42, 12),
            "account_payee": FieldPosition(10, 8, 72, 9),
        })

    @classmethod
    def builtins(cls) -> tuple["ChequeTemplate", ...]:
        """Calibration starting points; no customer or cheque data is stored."""
        return (
            cls.default(),
            cls(name="Commercial Bank - Standard", date_style="boxed", fields={
                "date": FieldPosition(157, 9, 39, 11),
                "payee": FieldPosition(45, 29, 145, 11),
                "amount_words_1": FieldPosition(45, 42, 143, 10),
                "amount_words_2": FieldPosition(45, 52, 105, 10),
                "amount": FieldPosition(154, 48, 42, 12),
                "account_payee": FieldPosition(10, 8, 72, 9),
            }),
            cls(name="Seylan Bank - Standard", date_style="boxed", fields={
                "date": FieldPosition(158, 9, 38, 11),
                "payee": FieldPosition(43, 30, 145, 11),
                "amount_words_1": FieldPosition(43, 43, 142, 10),
                "amount_words_2": FieldPosition(43, 53, 105, 10),
                "amount": FieldPosition(155, 47, 40, 12),
                "account_payee": FieldPosition(10, 8, 72, 9),
            }),
        )


class TemplateStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory; directory.mkdir(parents=True, exist_ok=True)
        marker = directory / ".banks_initialized"
        if not marker.exists():
            for template in ChequeTemplate.builtins():
                if not self._path(template.name).exists():
                    self.save(template)
            marker.write_text("1", encoding="ascii")

    def _path(self, name: str) -> Path:
        safe = "".join(ch for ch in name if ch.isalnum() or ch in " -_").strip() or "template"
        return self.directory / f"{safe}.json"

    def list(self) -> list[ChequeTemplate]:
        result = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                raw["fields"] = {key: FieldPosition(**value) for key, value in raw["fields"].items()}
                result.append(ChequeTemplate(**raw))
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                continue
        return result

    def save(self, template: ChequeTemplate) -> None:
        path = self._path(template.name); temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(template), indent=2), encoding="utf-8"); temporary.replace(path)

    def delete(self, name: str) -> None:
        path = self._path(name)
        if path.exists():
            path.unlink()

    def rename_save(self, original_name: str, template: ChequeTemplate) -> None:
        self.save(template)
        if original_name != template.name:
            self.delete(original_name)

