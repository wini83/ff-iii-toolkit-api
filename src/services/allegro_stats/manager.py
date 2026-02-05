from __future__ import annotations

import asyncio

from services.domain.metrics import AllegroMetrics
from services.firefly_allegro_service import FireflyAllegroService
from services.tx_stats.models import JobStatus, MetricsState
from services.tx_stats.runner import recompute_metrics


class AllegroMetricsManager:
    def __init__(self, *, ff_allegro_service: FireflyAllegroService) -> None:
        self._ff_allegro_service = ff_allegro_service
        self._state: MetricsState[AllegroMetrics] = MetricsState(
            status=JobStatus.PENDING,
            result=None,
            error=None,
            progress=None,
            last_updated_at=None,
        )
        self._lock = asyncio.Lock()

    def get_state(self) -> MetricsState[AllegroMetrics]:
        return self._state

    async def refresh(self) -> MetricsState[AllegroMetrics]:
        async with self._lock:
            if self._state.status == JobStatus.RUNNING:
                return self._state

            self._state.progress = "queued"
            self._state.error = None

            asyncio.create_task(
                recompute_metrics(self._state, self._ff_allegro_service)
            )

            return self._state
