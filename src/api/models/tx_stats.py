from datetime import datetime

from pydantic import BaseModel


class RunResponse(BaseModel):
    job_id: str


class TxMetricsResultResponse(BaseModel):
    single_part_transactions: int
    uncategorized_transactions: int
    blik_not_ok: int
    action_req: int
    allegro_not_ok: int
    categorizable: int
    categorizable_by_month: dict[str, int]
    time_stamp: datetime


class TxMetricsStatusResponse(BaseModel):
    status: str
    progress: str | None
    result: TxMetricsResultResponse | None
    error: str | None
