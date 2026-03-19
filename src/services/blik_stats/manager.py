from __future__ import annotations

import asyncio
import logging

from services.domain.job_base import JobStatus
from services.domain.metrics import BlikStatisticsMetrics
from services.tx_stats.models import MetricsState
from services.tx_stats.runner import MetricsProvider, recompute_metrics

logger = logging.getLogger(__name__)


class BlikMetricsManager:
    def __init__(self, *, provider: MetricsProvider[BlikStatisticsMetrics]) -> None:
        self._provider = provider
        self._state: MetricsState[BlikStatisticsMetrics] = MetricsState(
            status=JobStatus.PENDING,
            result=None,
            error=None,
            progress=None,
            last_updated_at=None,
        )
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    def get_state(self) -> MetricsState[BlikStatisticsMetrics]:
        return self._state

    async def ensure_current(self) -> MetricsState[BlikStatisticsMetrics]:
        if self._state.status == JobStatus.RUNNING:
            return self._state
        current_snapshot_timestamp = (
            await self._provider.get_cached_snapshot_timestamp()
        )
        if (
            self._state.status == JobStatus.DONE
            and self._state.result is not None
            and current_snapshot_timestamp is not None
            and self._state.result.time_stamp == current_snapshot_timestamp
        ):
            return self._state
        return await self._start(force_refresh=False)

    async def refresh(self) -> MetricsState[BlikStatisticsMetrics]:
        return await self._start(force_refresh=True)

    async def _start(
        self, *, force_refresh: bool
    ) -> MetricsState[BlikStatisticsMetrics]:
        async with self._lock:
            if self._state.status == JobStatus.RUNNING:
                return self._state
            if self._task is not None and not self._task.done():
                return self._state
            self._state.status = JobStatus.RUNNING
            self._state.progress = "queued"
            self._state.error = None
            self._state.result = None

            task = asyncio.create_task(
                recompute_metrics(
                    self._state,
                    self._provider,
                    force_refresh=force_refresh,
                ),
                name="blik-metrics-refresh",
            )
            task.add_done_callback(self._on_task_done)
            self._task = task

            return self._state

    def _on_task_done(self, task: asyncio.Task[None]) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            logger.warning("BLIK metrics refresh task was cancelled")
        except Exception:
            logger.exception("BLIK metrics refresh task failed unexpectedly")
        finally:
            if self._task is task:
                self._task = None
