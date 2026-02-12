from unittest.mock import MagicMock

import pytest

import services.allegro_stats.manager as manager_module
from services.allegro_stats.manager import AllegroMetricsManager
from services.tx_stats.models import JobStatus


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_refresh_when_running_does_not_schedule(monkeypatch):
    mgr = AllegroMetricsManager(ff_allegro_service=MagicMock())
    mgr._state.status = JobStatus.RUNNING

    called = {"create_task": False}

    def fake_create_task(arg):
        called["create_task"] = True
        return "task"

    monkeypatch.setattr(manager_module.asyncio, "create_task", fake_create_task)

    state = await mgr.refresh()

    assert state is mgr.get_state()
    assert called["create_task"] is False


@pytest.mark.anyio
async def test_refresh_queues_job_and_clears_error(monkeypatch):
    ff_service = MagicMock()
    mgr = AllegroMetricsManager(ff_allegro_service=ff_service)
    mgr._state.status = JobStatus.PENDING
    mgr._state.error = "old"
    mgr._state.progress = "old"

    captured = {}
    sentinel = object()

    def fake_recompute(state, svc):
        captured["args"] = (state, svc)
        return sentinel

    def fake_create_task(arg):
        captured["task_arg"] = arg
        return "task"

    monkeypatch.setattr(manager_module, "recompute_metrics", fake_recompute)
    monkeypatch.setattr(manager_module.asyncio, "create_task", fake_create_task)

    state = await mgr.refresh()

    assert state.progress == "queued"
    assert state.error is None
    assert captured["args"][0] is mgr.get_state()
    assert captured["args"][1] is ff_service
    assert captured["task_arg"] is sentinel
