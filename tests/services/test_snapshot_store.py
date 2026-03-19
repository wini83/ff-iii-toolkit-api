import asyncio
from datetime import UTC, datetime, timedelta

from services.domain.metrics import FetchMetrics
from services.snapshot.models import TransactionSnapshot
from services.snapshot.store import InMemorySnapshotStore


def build_snapshot(*, fetched_at: datetime) -> TransactionSnapshot:
    return TransactionSnapshot(
        transactions=[],
        metrics=FetchMetrics(
            total_transactions=0,
            fetching_duration_ms=1,
            invalid=0,
            multipart=0,
        ),
        fetched_at=fetched_at,
    )


def test_in_memory_snapshot_store_returns_none_when_empty():
    store = InMemorySnapshotStore()

    assert asyncio.run(store.get_snapshot()) is None
    assert asyncio.run(store.is_stale(300)) is True


def test_in_memory_snapshot_store_replaces_snapshot_and_invalidates():
    store = InMemorySnapshotStore()
    snapshot = build_snapshot(fetched_at=datetime.now(UTC))

    asyncio.run(store.set_snapshot(snapshot))

    assert asyncio.run(store.get_snapshot()) is snapshot
    assert asyncio.run(store.is_stale(300)) is False

    asyncio.run(store.invalidate())

    assert asyncio.run(store.get_snapshot()) is None
    assert asyncio.run(store.is_stale(300)) is True


def test_in_memory_snapshot_store_current_utc_snapshot_is_not_stale():
    store = InMemorySnapshotStore()
    snapshot = build_snapshot(fetched_at=datetime.now(UTC))

    asyncio.run(store.set_snapshot(snapshot))

    assert asyncio.run(store.is_stale(300)) is False


def test_in_memory_snapshot_store_marks_old_snapshot_as_stale():
    store = InMemorySnapshotStore()
    snapshot = build_snapshot(fetched_at=datetime.now(UTC) - timedelta(seconds=301))

    asyncio.run(store.set_snapshot(snapshot))

    assert asyncio.run(store.is_stale(300)) is True
