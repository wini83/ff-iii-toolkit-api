from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from services.domain.metrics import BaseMetrics


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(slots=True)
class TxStatsJob:
    """Represents the lifecycle and outcome of a stats computation job."""

    job_id: str
    status: JobStatus
    result: BaseMetrics | None = None
    error: str | None = None
    progress: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def mark_running(self) -> None:
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now(UTC)
        self.progress = "running"

    def mark_done(self, result: BaseMetrics) -> None:
        self.status = JobStatus.DONE
        self.result = result
        self.finished_at = datetime.now(UTC)
        self.progress = "done"
        self.error = None

    def mark_failed(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.error = error
        self.finished_at = datetime.now(UTC)
        self.progress = "failed"
