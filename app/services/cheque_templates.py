from __future__ import annotations

import json
from copy import deepcopy
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
    rotation_degrees: int = 0
    date_digit_spacing_mm: float = 4.5
    omit_year_century: bool = True

    @classmethod
    def default(cls, name: str = "Generic Bank Cheque") -> "ChequeTemplate":
        return cls(name=name, fields={
            "date": FieldPosition(157, 9, 39, 11),
            "payee": FieldPosition(28, 27, 158, 12),
            "amount_words_1": FieldPosition(16, 42, 170, 10),
            "amount_words_2": FieldPosition(16, 53, 137, 10),
            "amount": FieldPosition(154, 54, 42, 12),
            "account_payee": FieldPosition(7, 13, 62, 9),
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
                "account_payee": FieldPosition(7, 13, 62, 9),
            }),
            cls(name="Seylan Bank - Standard", date_style="boxed", fields={
                "date": FieldPosition(158, 9, 38, 11),
                "payee": FieldPosition(43, 30, 145, 11),
                "amount_words_1": FieldPosition(43, 43, 142, 10),
                "amount_words_2": FieldPosition(43, 53, 105, 10),
                "amount": FieldPosition(155, 47, 40, 12),
                "account_payee": FieldPosition(7, 13, 62, 9),
            }),
            cls(name="Canon LBP6030 - 180x90 mm Cheque", width_mm=180.0, height_mm=90.0,
                date_style="boxed", rotation_degrees=90, fields={
                "date": FieldPosition(139, 9, 35, 10),
                "payee": FieldPosition(38, 28, 132, 11),
                "amount_words_1": FieldPosition(38, 41, 130, 9),
                "amount_words_2": FieldPosition(38, 51, 96, 9),
                "amount": FieldPosition(137, 48, 38, 11),
                "account_payee": FieldPosition(6, 13, 56, 8),
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
        canon_marker = directory / ".canon_lbp6030_180x90_added"
        canon_name = "Canon LBP6030 - 180x90 mm Cheque"
        if not canon_marker.exists():
            preset = next(item for item in ChequeTemplate.builtins() if item.name == canon_name)
            if not self._path(canon_name).exists():
                self.save(preset)
            canon_marker.write_text("1", encoding="ascii")
        commercial_marker = directory / ".commercial_format_applied_to_all_v1"
        if not commercial_marker.exists():
            templates = self.list()
            commercial = next((item for item in templates if item.name.casefold() == "commercial bank - standard"), None)
            if commercial is None:
                commercial = next(item for item in ChequeTemplate.builtins() if item.name == "Commercial Bank - Standard")
            for template in templates:
                template.fields = deepcopy(commercial.fields)
                template.date_style = "boxed"
                template.date_digit_spacing_mm = commercial.date_digit_spacing_mm
                template.omit_year_century = True
                self.save(template)
            commercial_marker.write_text("1", encoding="ascii")

    def commercial_base(self, name: str) -> ChequeTemplate:
        templates = self.list()
        source = next((item for item in templates if item.name.casefold() == "commercial bank - standard"), None)
        if source is None:
            source = next(item for item in ChequeTemplate.builtins() if item.name == "Commercial Bank - Standard")
        result = deepcopy(source); result.name = name; result.omit_year_century = True
        return result

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

