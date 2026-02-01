from __future__ import annotations

from typing import Protocol

from services.domain.metrics import BaseMetrics
from services.firefly_base_service import FireflyServiceError
from services.tx_stats.models import TxStatsJob


class TxService(Protocol):
    async def fetch_metrics(self) -> BaseMetrics: ...


async def run_tx_stats_job(job: TxStatsJob, tx_service: TxService) -> None:
    """Run a stats job asynchronously using the provided transaction service."""

    job.mark_running()
    try:
        result = await tx_service.fetch_metrics()
        job.mark_done(result)
    except FireflyServiceError as exc:
        job.mark_failed(str(exc))
