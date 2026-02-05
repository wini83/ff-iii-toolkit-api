from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
