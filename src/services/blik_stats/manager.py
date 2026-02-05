from __future__ import annotations

import asyncio

from services.domain.metrics import BlikStatisticsMetrics
from services.firefly_blik_service import FireflyBlikService
from services.tx_stats.models import JobStatus, MetricsState
from services.tx_stats.runner import recompute_metrics


class BlikMetricsManager:
    def __init__(self, *, blik_service: FireflyBlikService) -> None:
        self._blik_service = blik_service
        self._state: MetricsState[BlikStatisticsMetrics] = MetricsState(
            status=JobStatus.PENDING,
            result=None,
            error=None,
            progress=None,
            last_updated_at=None,
        )
        self._lock = asyncio.Lock()

    def get_state(self) -> MetricsState[BlikStatisticsMetrics]:
        return self._state

    async def refresh(self) -> MetricsState[BlikStatisticsMetrics]:
        async with self._lock:
            if self._state.status == JobStatus.RUNNING:
                return self._state

            self._state.progress = "queued"
            self._state.error = None

            asyncio.create_task(recompute_metrics(self._state, self._blik_service))

            return self._state
