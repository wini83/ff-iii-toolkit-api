from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from services.allegro_stats.manager import AllegroMetricsManager
from services.domain.allegro import (
    AllegroApplyJob,
    AllegroPageMatchCacheEntry,
    AllegroPageRequest,
)
from services.domain.job_base import JobStatus
from services.domain.match_result import MatchResult


class AllegroApplyJobManager:
    def __init__(self) -> None:
        self._jobs: dict[UUID, AllegroApplyJob] = {}

    def create(self, *, secret_id: UUID, total: int) -> AllegroApplyJob:
        job = AllegroApplyJob(
            id=uuid4(),
            secret_id=secret_id,
            total=total,
            status=JobStatus.PENDING,
            started_at=datetime.now(UTC),
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: UUID) -> AllegroApplyJob | None:
        return self._jobs.get(job_id)


@dataclass
class AllegroStateStore:
    page_matches_cache: dict[
        str, dict[AllegroPageRequest, AllegroPageMatchCacheEntry]
    ] = field(default_factory=dict)
    job_manager: AllegroApplyJobManager = field(default_factory=AllegroApplyJobManager)
    metrics_manager: AllegroMetricsManager | None = None

    def put_page_matches(
        self,
        *,
        secret_id: UUID,
        entry: AllegroPageMatchCacheEntry,
    ) -> None:
        secret_key = str(secret_id)
        if secret_key not in self.page_matches_cache:
            self.page_matches_cache[secret_key] = {}
        self.page_matches_cache[secret_key][entry.page] = entry

    def get_page_matches(
        self, *, secret_id: UUID, page: AllegroPageRequest
    ) -> list[MatchResult] | None:
        page_cache = self.page_matches_cache.get(str(secret_id), {})
        entry = page_cache.get(page)
        if entry is None:
            return None
        return entry.matches

    def get_all_matches(self, *, secret_id: UUID) -> list[MatchResult]:
        page_cache = self.page_matches_cache.get(str(secret_id), {})
        matches: list[MatchResult] = []
        for entry in page_cache.values():
            matches.extend(entry.matches)
        return matches

    def invalidate_page(self, *, secret_id: UUID, page: AllegroPageRequest) -> bool:
        secret_key = str(secret_id)
        page_cache = self.page_matches_cache.get(secret_key)
        if page_cache is None or page not in page_cache:
            return False
        del page_cache[page]
        if not page_cache:
            del self.page_matches_cache[secret_key]
        return True

    def invalidate_secret(self, *, secret_id: UUID) -> bool:
        secret_key = str(secret_id)
        if secret_key not in self.page_matches_cache:
            return False
        del self.page_matches_cache[secret_key]
        return True

    def invalidate_all(self) -> None:
        self.page_matches_cache.clear()


_state_store = AllegroStateStore()


def get_allegro_state_store() -> AllegroStateStore:
    return _state_store
