from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class CitiImportTextRequest(BaseModel):
    text: str
    include_positive: bool = False
    chunk_size: int = Field(default=60, ge=1, le=1000)


class CitiImportRecord(BaseModel):
    date: date
    amount: float
    details: str
    recipient: str
    operation_amount: float
    sender: str = ""
    operation_currency: str = "PLN"
    account_currency: str = "PLN"
    sender_account: str = ""
    recipient_account: str = ""


class CitiImportParseResponse(BaseModel):
    file_id: str
    record_count: int
    preview: list[CitiImportRecord]
    warnings: list[str] = Field(default_factory=list)
