from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.domain.job_base import JobStatus
from services.domain.metrics import BaseMetrics


@dataclass(slots=True)
class MetricsState[T: BaseMetrics]:
    status: JobStatus
    result: T | None
    error: str | None
    progress: str | None
    last_updated_at: datetime | None
