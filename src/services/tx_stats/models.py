from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from services.domain.metrics import BaseMetrics


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(slots=True)
class MetricsState[T: BaseMetrics]:
    status: JobStatus
    result: T | None
    error: str | None
    progress: str | None
    last_updated_at: datetime | None
