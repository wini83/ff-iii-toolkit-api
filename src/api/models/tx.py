from datetime import date
from enum import Enum

from pydantic import BaseModel


class SimplifiedItem(BaseModel):
    date: date
    amount: float


class SimplifiedTx(SimplifiedItem):
    """Simplified representation of a Firefly III transaction."""

    id: int
    description: str
    tags: list[str]
    notes: str
    category: str


class SimplifiedCategory(BaseModel):
    """Simplified representation of a Firefly III Category."""

    id: int
    name: str


class ScreeningResponse(BaseModel):
    tx: SimplifiedTx
    categories: list[SimplifiedCategory]


class ScreeningMonthResponse(BaseModel):
    year: int
    month: int
    remaining: int
    transactions: list[SimplifiedTx]
    categories: list[SimplifiedCategory]


class TxTag(str, Enum):
    blik_done = "blik_done"
    allegro_done = "allegro_done"
    rule_p = "rule_potential"
    action_req = "action_req"
