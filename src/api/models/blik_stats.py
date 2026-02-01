from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BlikMetricsResultResponse(BaseModel):
    single_part_transactions: int
    uncategorized_transactions: int
    filtered_by_description_exact: int
    filtered_by_description_partial: int
    not_processed_transactions: int
    not_processed_by_month: dict[str, int]
    inclomplete_procesed_by_month: dict[str, int]
    time_stamp: datetime


class BlikMetricsStatusResponse(BaseModel):
    status: str
    progress: str | None
    result: BlikMetricsResultResponse | None
    error: str | None
