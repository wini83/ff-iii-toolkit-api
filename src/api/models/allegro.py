from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from api.models.tx import SimplifiedTx


class AllegroMetricsResultResponse(BaseModel):
    total_transactions: int
    allegro_transactions: int
    not_processed__allegro_transactions: int
    not_processed_by_month: dict[str, int]
    time_stamp: datetime
    fetch_seconds: float


class AllegroMetricsStatusResponse(BaseModel):
    status: str
    progress: str | None
    result: AllegroMetricsResultResponse | None
    error: str | None


class AllegroFetchPayload(BaseModel):
    secrets: list[str]


class AllegroPayment(BaseModel):
    amount: float
    date: date
    details: list[str]
    is_balanced: bool
    allegro_login: str
    external_id: str
    external_short_id: str


class MatchResult(BaseModel):
    tx: SimplifiedTx
    matches: list[AllegroPayment]


class AllegroMatchResponse(BaseModel):
    login: str
    payments_fetched: int
    transactions_found: int
    transactions_not_matched: int
    transactions_with_one_match: int
    transactions_with_many_matches: int
    fetch_seconds: float
    content: list[MatchResult]


class ApplyDecision(BaseModel):
    payment_id: str  # allegro payment id
    transaction_id: int  # firefly tx id
    strategy: Literal["auto", "manual", "force"] = "auto"


class ApplyPayload(BaseModel):
    decisions: list[ApplyDecision]


class ApplyJobStatusResponse(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class ApplyJobResponse(BaseModel):
    id: UUID
    status: ApplyJobStatusResponse
    total: int
    applied: int
    failed: int
