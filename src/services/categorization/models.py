from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True, frozen=True)
class CategorizationQuery:
    transaction_id: str | None
    title: str
    merchant: str | None
    notes: str | None
    amount: Decimal
    source_type: str = "bank"


@dataclass(slots=True, frozen=True)
class TransactionCategorizationQuery:
    transaction_id: str | None
    title: str
    merchant: str | None
    notes: str | None
    amount: Decimal
    amount_bucket: str
    source_type: str
