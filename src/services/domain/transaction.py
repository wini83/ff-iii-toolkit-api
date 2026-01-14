from dataclasses import dataclass
from enum import Enum

from services.domain.base import BaseMatchItem


@dataclass(slots=True)
class Transaction(BaseMatchItem):
    id: int
    description: str
    tags: set[str]
    notes: str | None
    category: str | None
    currency: str | None = "PLN"


class TxTag(str, Enum):
    blik_done = "blik_done"
    allegro_done = "allegro_done"
    rule_p = "rule_potential"
    action_req = "action_req"


@dataclass
class Category:
    id: int
    name: str


@dataclass
class TransactionUpdate:
    description: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    category_id: int | None = None
