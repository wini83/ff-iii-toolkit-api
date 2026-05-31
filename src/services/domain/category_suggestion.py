from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True, frozen=True)
class CategorySuggestion:
    category_id: str
    category_name: str
    score: float
    reason: str


@dataclass(slots=True, frozen=True)
class TransactionCategorizationDocument:
    transaction_id: str
    user_id: str
    category_id: str
    category_name: str
    title: str
    merchant: str | None
    notes: str | None
    amount: Decimal
    amount_bucket: str
    source_type: str


@dataclass(slots=True, frozen=True)
class SimilarTransactionMatch:
    transaction_id: str
    category_id: str
    category_name: str
    similarity_score: float
    matched_by: str
