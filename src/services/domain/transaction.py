from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from services.domain.base import BaseMatchItem


class TxTag(str, Enum):
    blik_done = "blik_done"
    allegro_done = "allegro_done"
    rule_p = "rule_potential"
    action_req = "action_req"


class TxType(str, Enum):
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"
    TRANSFER = "transfer"


@dataclass
class Category:
    id: int
    name: str


@dataclass(slots=True, frozen=True)
class Currency:
    code: str
    symbol: str
    decimals: int


@dataclass(slots=True, frozen=True)
class FXContext:
    original_currency: Currency
    original_amount: Decimal


@dataclass(slots=True)
class Transaction(BaseMatchItem):
    id: int
    type: TxType
    description: str
    tags: set[str]
    notes: str | None
    category: Category | None
    currency: Currency
    fx: FXContext | None = None


@dataclass
class TransactionUpdate:
    description: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    category_id: int | None = None
