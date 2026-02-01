from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from services.tx_stats.models import JobStatus, TxStatsJob


@dataclass(slots=True)
class TxStatsJobRegistry:
    """In-memory registry for stats jobs."""

    _jobs: dict[str, TxStatsJob] = field(default_factory=dict)

    def create(self) -> TxStatsJob:
        job_id = str(uuid4())
        job = TxStatsJob(job_id=job_id, status=JobStatus.PENDING)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> TxStatsJob | None:
        return self._jobs.get(job_id)
