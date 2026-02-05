from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from services.domain.metrics import BaseMetrics
from services.tx_stats.models import JobStatus, MetricsState


class MetricsProvider[T: BaseMetrics](Protocol):
    async def fetch_metrics(self) -> T: ...


async def recompute_metrics[T: BaseMetrics](
    state: MetricsState[T],
    provider: MetricsProvider[T],
) -> None:
    state.status = JobStatus.RUNNING
    state.progress = "fetching"
    state.error = None
    try:
        result = await provider.fetch_metrics()
        state.result = result
        state.status = JobStatus.DONE
        state.last_updated_at = datetime.now(UTC)
        state.progress = None
    except Exception as exc:
        state.status = JobStatus.FAILED
        state.error = str(exc)
        state.progress = None
