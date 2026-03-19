import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

import services.blik_stats.manager as manager_module
from services.blik_stats.manager import BlikMetricsManager
from services.domain.job_base import JobStatus


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_refresh_when_running_does_not_schedule(monkeypatch):
    mgr = BlikMetricsManager(provider=MagicMock())
    mgr._state.status = JobStatus.RUNNING

    called = {"create_task": False}

    def fake_create_task(arg, **kwargs):
        called["create_task"] = True
        return "task"

    monkeypatch.setattr(manager_module.asyncio, "create_task", fake_create_task)

    state = await mgr.refresh()

    assert state is mgr.get_state()
    assert called["create_task"] is False


@pytest.mark.anyio
async def test_ensure_current_queues_non_forced_job_and_clears_error(monkeypatch):
    provider = MagicMock()
    provider.get_cached_snapshot_timestamp = AsyncMock(
        return_value=datetime(2024, 1, 1, tzinfo=UTC)
    )
    mgr = BlikMetricsManager(provider=provider)
    mgr._state.status = JobStatus.PENDING
    mgr._state.error = "old"
    mgr._state.progress = "old"

    captured = {}
    sentinel = object()

    def fake_recompute(state, svc, *, force_refresh=False):
        captured["args"] = (state, svc, force_refresh)
        return sentinel

    task = MagicMock()

    def fake_create_task(arg, **kwargs):
        captured["task_arg"] = arg
        captured["task_kwargs"] = kwargs
        return task

    monkeypatch.setattr(manager_module, "recompute_metrics", fake_recompute)
    monkeypatch.setattr(manager_module.asyncio, "create_task", fake_create_task)

    state = await mgr.ensure_current()

    assert state.progress == "queued"
    assert state.error is None
    assert captured["args"][0] is mgr.get_state()
    assert captured["args"][1] is provider
    assert captured["args"][2] is False
    assert captured["task_arg"] is sentinel
    assert captured["task_kwargs"]["name"] == "blik-metrics-refresh"
    task.add_done_callback.assert_called_once()


@pytest.mark.anyio
async def test_ensure_current_returns_existing_state_when_snapshot_matches():
    provider = MagicMock()
    provider.get_cached_snapshot_timestamp = AsyncMock(
        return_value=datetime(2024, 1, 1, tzinfo=UTC)
    )
    mgr = BlikMetricsManager(provider=provider)
    mgr._state.status = JobStatus.DONE
    mgr._state.result = MagicMock(time_stamp=datetime(2024, 1, 1, tzinfo=UTC))

    state = await mgr.ensure_current()

    assert state is mgr.get_state()


@pytest.mark.anyio
async def test_refresh_queues_forced_job(monkeypatch):
    mgr = BlikMetricsManager(provider=MagicMock())
    captured = {}
    sentinel = object()

    def fake_recompute(state, svc, *, force_refresh=False):
        captured["args"] = (state, svc, force_refresh)
        return sentinel

    task = MagicMock()

    def fake_create_task(arg, **kwargs):
        captured["task_arg"] = arg
        captured["task_kwargs"] = kwargs
        return task

    monkeypatch.setattr(manager_module, "recompute_metrics", fake_recompute)
    monkeypatch.setattr(manager_module.asyncio, "create_task", fake_create_task)

    await mgr.refresh()

    assert captured["args"][2] is True
    assert captured["task_arg"] is sentinel
    assert captured["task_kwargs"]["name"] == "blik-metrics-refresh"
    task.add_done_callback.assert_called_once()


@pytest.mark.anyio
async def test_refresh_deduplicates_concurrent_calls(monkeypatch):
    mgr = BlikMetricsManager(provider=MagicMock())
    created = {"count": 0}
    task = MagicMock()
    task.done.return_value = False

    def fake_create_task(arg, **kwargs):
        created["count"] += 1
        arg.close()
        return task

    monkeypatch.setattr(manager_module.asyncio, "create_task", fake_create_task)

    first, second = await asyncio.gather(mgr.refresh(), mgr.refresh())

    assert first is second
    assert created["count"] == 1


@pytest.mark.anyio
async def test_ensure_current_does_not_schedule_when_task_already_active(monkeypatch):
    provider = MagicMock()
    provider.get_cached_snapshot_timestamp = AsyncMock(return_value=None)
    mgr = BlikMetricsManager(provider=provider)
    active_task = MagicMock()
    active_task.done.return_value = False
    mgr._task = active_task

    called = {"create_task": False}

    def fake_create_task(arg, **kwargs):
        called["create_task"] = True
        arg.close()
        return MagicMock()

    monkeypatch.setattr(manager_module.asyncio, "create_task", fake_create_task)

    state = await mgr.ensure_current()

    assert state is mgr.get_state()
    assert called["create_task"] is False


def test_on_task_done_logs_cancellation_and_clears_active_task(monkeypatch):
    mgr = BlikMetricsManager(provider=MagicMock())
    task = MagicMock()
    task.result.side_effect = asyncio.CancelledError()
    mgr._task = task
    logger = MagicMock()

    monkeypatch.setattr(manager_module, "logger", logger)

    mgr._on_task_done(task)

    logger.warning.assert_called_once_with("BLIK metrics refresh task was cancelled")
    assert mgr._task is None


def test_on_task_done_logs_unexpected_error_and_clears_active_task(monkeypatch):
    mgr = BlikMetricsManager(provider=MagicMock())
    task = MagicMock()
    task.result.side_effect = RuntimeError("boom")
    mgr._task = task
    logger = MagicMock()

    monkeypatch.setattr(manager_module, "logger", logger)

    mgr._on_task_done(task)

    logger.exception.assert_called_once_with(
        "BLIK metrics refresh task failed unexpectedly"
    )
    assert mgr._task is None
