from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from services.domain.blik import BlikApplyJob
from services.domain.job_base import JobStatus
from services.domain.match_result import MatchResult


class BlikApplyJobManager:
    def __init__(self) -> None:
        self._jobs: dict[UUID, BlikApplyJob] = {}

    def create(self, *, file_id: str, total: int) -> BlikApplyJob:
        job = BlikApplyJob(
            id=uuid4(),
            file_id=file_id,
            total=total,
            status=JobStatus.PENDING,
            started_at=datetime.now(UTC),
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: UUID) -> BlikApplyJob | None:
        return self._jobs.get(job_id)


@dataclass
class BlikStateStore:
    matches_cache: dict[str, list[MatchResult]] = field(default_factory=dict)
    job_manager: BlikApplyJobManager = field(default_factory=BlikApplyJobManager)

    def put_matches(self, *, file_id: str, matches: list[MatchResult]) -> None:
        self.matches_cache[file_id] = matches

    def get_matches(self, *, file_id: str) -> list[MatchResult]:
        return self.matches_cache.get(file_id, [])


_state_store = BlikStateStore()


def get_blik_state_store() -> BlikStateStore:
    return _state_store
