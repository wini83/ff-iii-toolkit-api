from __future__ import annotations

from datetime import date, datetime

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
