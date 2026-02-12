from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from services.allegro_stats.manager import AllegroMetricsManager
from services.domain.allegro import AllegroApplyJob, ApplyJobStatus
from services.domain.match_result import MatchResult


class AllegroApplyJobManager:
    def __init__(self):
        self._jobs: dict[UUID, AllegroApplyJob] = {}

    def create(self, *, secret_id: UUID, total: int) -> AllegroApplyJob:
        job = AllegroApplyJob(
            id=uuid4(),
            secret_id=secret_id,
            total=total,
            status=ApplyJobStatus.PENDING,
            started_at=datetime.now(UTC),
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: UUID) -> AllegroApplyJob | None:
        return self._jobs.get(job_id)


@dataclass
class AllegroStateStore:
    matches_cache: dict[str, list[MatchResult]] = field(default_factory=dict)
    job_manager: AllegroApplyJobManager = field(default_factory=AllegroApplyJobManager)
    metrics_manager: AllegroMetricsManager | None = None


_state_store = AllegroStateStore()


def get_allegro_state_store() -> AllegroStateStore:
    return _state_store
