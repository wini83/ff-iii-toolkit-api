from datetime import datetime

import pytest

from services.domain.metrics import BaseMetrics
from services.tx_stats.models import JobStatus, MetricsState
from services.tx_stats.runner import recompute_metrics


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


class DummyProvider:
    def __init__(self, result=None, exc: Exception | None = None):
        self._result = result
        self._exc = exc

    async def fetch_metrics(self):
        if self._exc:
            raise self._exc
        return self._result


@pytest.mark.anyio
async def test_recompute_metrics_success():
    metrics = BaseMetrics(total_transactions=1, fetching_duration_ms=5)
    state = MetricsState(
        status=JobStatus.PENDING,
        result=None,
        error=None,
        progress=None,
        last_updated_at=None,
    )
    provider = DummyProvider(result=metrics)

    await recompute_metrics(state, provider)

    assert state.status == JobStatus.DONE
    assert state.result == metrics
    assert state.error is None
    assert state.progress is None
    assert isinstance(state.last_updated_at, datetime)


@pytest.mark.anyio
async def test_recompute_metrics_failure():
    state = MetricsState(
        status=JobStatus.PENDING,
        result=None,
        error=None,
        progress=None,
        last_updated_at=None,
    )
    provider = DummyProvider(exc=RuntimeError("boom"))

    await recompute_metrics(state, provider)

    assert state.status == JobStatus.FAILED
    assert state.result is None
    assert state.error == "boom"
    assert state.progress is None
