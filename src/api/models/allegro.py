from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from api.models.job_base import JobStatus
from api.models.tx import MatchProcessingStatus, SimplifiedTx


class AllegroMetricsResultResponse(BaseModel):
    total_transactions: int
    allegro_transactions: int
    not_processed__allegro_transactions: int
    not_processed_by_month: dict[str, int]
    time_stamp: datetime
    fetch_seconds: float


class AllegroMetricsStatusResponse(BaseModel):
    status: JobStatus
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
    status: MatchProcessingStatus = MatchProcessingStatus.NEW


class AllegroMatchResponse(BaseModel):
    login: str
    payments_fetched: int
    transactions_found: int
    transactions_not_matched: int
    transactions_with_one_match: int
    transactions_with_many_matches: int
    fetch_seconds: float
    content: list[MatchResult]
    unmatched_payments: list[AllegroPayment]


class ApplyDecision(BaseModel):
    payment_id: str  # allegro payment id
    transaction_id: int  # firefly tx id
    strategy: Literal["auto", "manual", "force"] = "auto"


class ApplyPayload(BaseModel):
    decisions: list[ApplyDecision]


class ApplyOutcomeResponse(BaseModel):
    transaction_id: int
    status: Literal["success", "failed"]
    reason: str | None = None


class ApplyJobResponse(BaseModel):
    id: UUID
    secret_id: UUID
    status: JobStatus
    total: int
    applied: int
    failed: int
    started_at: datetime
    finished_at: datetime | None
    results: list[ApplyOutcomeResponse]
