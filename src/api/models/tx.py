from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class SimplifiedItem(BaseModel):
    date: date
    amount: float


class AccountType(StrEnum):
    ASSET = "asset"
    EXPENSE = "expense"
    REVENUE = "revenue"
    LIABILITY = "liability"
    LOAN = "loan"
    DEBT = "debt"
    MORTGAGE = "mortgage"
    INITIAL_BALANCE = "initial-balance"
    RECONCILIATION = "reconciliation"


class SimplifiedAccountRef(BaseModel):
    id: int
    name: str
    type: AccountType
    iban: str | None = None


class SimplifiedTx(SimplifiedItem):
    """Simplified representation of a Firefly III transaction."""

    id: int
    description: str
    tags: list[str]
    notes: str
    category: str | None
    currency_code: str
    currency_symbol: str
    type: Literal["withdrawal", "deposit", "transfer"]
    fx_amount: float | None = None
    fx_currency: str | None = None
    source_account: SimplifiedAccountRef | None = None
    destination_account: SimplifiedAccountRef | None = None


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


class TxTag(StrEnum):
    blik_done = "blik_done"
    allegro_done = "allegro_done"
    rule_p = "rule_potential"
    action_req = "action_req"


class MatchProcessingStatus(StrEnum):
    NEW = "new"
    ALREADY_PROCESSED = "already_processed"
