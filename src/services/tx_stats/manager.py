from __future__ import annotations

import asyncio

from services.domain.metrics import TXStatisticsMetrics
from services.firefly_tx_service import FireflyTxService
from services.tx_stats.models import JobStatus, MetricsState
from services.tx_stats.runner import recompute_metrics


class TxMetricsManager:
    def __init__(self, *, tx_service: FireflyTxService) -> None:
        self._tx_service = tx_service
        self._state: MetricsState[TXStatisticsMetrics] = MetricsState(
            status=JobStatus.PENDING,
            result=None,
            error=None,
            progress=None,
            last_updated_at=None,
        )
        self._lock = asyncio.Lock()

    def get_state(self) -> MetricsState[TXStatisticsMetrics]:
        return self._state

    async def refresh(self) -> MetricsState[TXStatisticsMetrics]:
        async with self._lock:
            if self._state.status == JobStatus.RUNNING:
                return self._state

            # only progress changes here; status is owned by runner
            self._state.progress = "queued"
            self._state.error = None

            asyncio.create_task(recompute_metrics(self._state, self._tx_service))

            return self._state
