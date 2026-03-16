from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from services.domain.job_base import JobStatus


@dataclass(frozen=True, slots=True)
class MatchDecision:
    transaction_id: int
    selected_match_id: str


@dataclass(slots=True)
class ApplyOutcome:
    transaction_id: int
    selected_match_id: str | None
    status: Literal["success", "failed"]
    reason: str | None = None


@dataclass(slots=True)
class BlikApplyJob:
    id: UUID
    file_id: str
    total: int
    status: JobStatus
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    applied: int = 0
    failed: int = 0
    results: list[ApplyOutcome] = field(default_factory=list)
    finished_at: datetime | None = None
