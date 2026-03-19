from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from api.models.job_base import JobStatus
from api.models.tx import MatchProcessingStatus, SimplifiedItem, SimplifiedTx


class SimplifiedRecord(SimplifiedItem):
    match_id: str | None = None
    details: str
    recipient: str
    operation_amount: float
    sender: str = ""
    operation_currency: str = "PLN"
    account_currency: str = "PLN"
    sender_account: str = ""
    recipient_account: str = ""


class MatchResult(BaseModel):
    tx: SimplifiedTx
    matches: list[SimplifiedRecord]
    status: MatchProcessingStatus = MatchProcessingStatus.NEW


class UploadResponse(BaseModel):
    message: str
    count: int
    id: str


class ApplyDecision(BaseModel):
    transaction_id: int
    selected_match_id: str


class ApplyDecisionsPayload(BaseModel):
    decisions: list[ApplyDecision]


class FilePreviewResponse(BaseModel):
    file_id: str
    decoded_name: str
    size: int
    content: list[SimplifiedRecord]


class FileMatchResponse(BaseModel):
    file_id: str
    decoded_name: str
    records_in_file: int
    transactions_found: int
    transactions_not_matched: int
    transactions_with_one_match: int
    transactions_with_many_matches: int
    content: list[MatchResult]


class ApplyOutcomeResponse(BaseModel):
    transaction_id: int
    selected_match_id: str | None = None
    status: Literal["success", "failed"]
    reason: str | None = None


class ApplyJobResponse(BaseModel):
    id: UUID
    file_id: str
    status: JobStatus
    total: int
    applied: int
    failed: int
    started_at: datetime
    finished_at: datetime | None
    results: list[ApplyOutcomeResponse]
