from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from services.domain.bank_record import BankRecord


@dataclass(slots=True)
class ParsedCitiTransaction:
    date: date
    payee: str
    amount_text: str
    amount_currency: str
    amount_value: str


@dataclass(slots=True)
class CitiImportFile:
    file_id: str
    records: list[BankRecord]
    warnings: list[str] = field(default_factory=list)
    chunk_size: int = 60
    include_positive: bool = False
    source_name: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
