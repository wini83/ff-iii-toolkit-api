import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from services.domain.metrics import FetchMetrics
from services.domain.transaction import Currency, Transaction, TxType
from services.snapshot.models import TransactionSnapshot
from services.snapshot.service import TransactionSnapshotService
from services.snapshot.store import InMemorySnapshotStore

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


def build_transaction() -> Transaction:
    return Transaction(
        id=1,
        date=date(2024, 1, 1),
        amount=Decimal("12.34"),
        type=TxType.WITHDRAWAL,
        description="Test",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )


def build_metrics() -> FetchMetrics:
    return FetchMetrics(
        total_transactions=1,
        fetching_duration_ms=25,
        invalid=0,
        multipart=0,
    )


def test_get_snapshot_returns_cached_snapshot_when_fresh():
    store = InMemorySnapshotStore()
    tx = build_transaction()
    snapshot = TransactionSnapshot(
        transactions=[tx],
        metrics=build_metrics(),
        fetched_at=datetime.now(UTC),
    )
    firefly_service = MagicMock()
    firefly_service.fetch_transactions_with_metrics = AsyncMock()
    service = TransactionSnapshotService(
        store=store,
        firefly_service=firefly_service,
        max_age_seconds=300,
    )

    asyncio.run(store.set_snapshot(snapshot))
    result = asyncio.run(service.get_snapshot())

    assert result is snapshot
    assert result.transaction_count == 1
    firefly_service.fetch_transactions_with_metrics.assert_not_awaited()


def test_get_snapshot_refreshes_when_missing():
    store = InMemorySnapshotStore()
    tx = build_transaction()
    metrics = build_metrics()
    firefly_service = MagicMock()
    firefly_service.fetch_transactions_with_metrics = AsyncMock(
        return_value=([tx], metrics)
    )
    service = TransactionSnapshotService(
        store=store,
        firefly_service=firefly_service,
        max_age_seconds=300,
    )

    result = asyncio.run(service.get_snapshot())
    stored = asyncio.run(store.get_snapshot())

    assert result is stored
    assert result.transactions == [tx]
    assert result.metrics == metrics
    assert result.transaction_count == 1
    firefly_service.fetch_transactions_with_metrics.assert_awaited_once()


def test_get_snapshot_refreshes_when_stale():
    store = InMemorySnapshotStore()
    stale_snapshot = TransactionSnapshot(
        transactions=[build_transaction()],
        metrics=build_metrics(),
        fetched_at=datetime.now(UTC) - timedelta(seconds=301),
    )
    refreshed_tx = build_transaction()
    refreshed_metrics = build_metrics()
    firefly_service = MagicMock()
    firefly_service.fetch_transactions_with_metrics = AsyncMock(
        return_value=([refreshed_tx], refreshed_metrics)
    )
    service = TransactionSnapshotService(
        store=store,
        firefly_service=firefly_service,
        max_age_seconds=300,
    )

    asyncio.run(store.set_snapshot(stale_snapshot))
    result = asyncio.run(service.get_snapshot())

    assert result is not stale_snapshot
    assert result.transactions == [refreshed_tx]
    assert result.metrics == refreshed_metrics
    firefly_service.fetch_transactions_with_metrics.assert_awaited_once()


def test_refresh_snapshot_replaces_store_contents():
    store = InMemorySnapshotStore()
    tx = build_transaction()
    metrics = build_metrics()
    firefly_service = MagicMock()
    firefly_service.fetch_transactions_with_metrics = AsyncMock(
        return_value=([tx], metrics)
    )
    service = TransactionSnapshotService(store=store, firefly_service=firefly_service)

    result = asyncio.run(service.refresh_snapshot())
    stored = asyncio.run(store.get_snapshot())

    assert stored is result
    assert stored is not None
    assert stored.transactions[0] is tx
    assert stored.metrics is metrics


def test_get_snapshot_uses_single_refresh_for_concurrent_calls():
    async def run_test() -> None:
        store = InMemorySnapshotStore()
        tx = build_transaction()
        metrics = build_metrics()
        firefly_service = MagicMock()

        async def fetch_transactions_with_metrics() -> tuple[
            list[Transaction], FetchMetrics
        ]:
            await asyncio.sleep(0.01)
            return [tx], metrics

        firefly_service.fetch_transactions_with_metrics = AsyncMock(
            side_effect=fetch_transactions_with_metrics
        )
        service = TransactionSnapshotService(
            store=store,
            firefly_service=firefly_service,
            max_age_seconds=300,
        )

        first_result, second_result = await asyncio.gather(
            service.get_snapshot(),
            service.get_snapshot(),
        )

        assert first_result is second_result
        assert first_result.transactions == [tx]
        assert first_result.metrics == metrics
        firefly_service.fetch_transactions_with_metrics.assert_awaited_once()

    asyncio.run(run_test())


def test_refresh_snapshot_uses_single_fetch_for_concurrent_calls():
    async def run_test() -> None:
        store = InMemorySnapshotStore()
        tx = build_transaction()
        metrics = build_metrics()
        firefly_service = MagicMock()

        async def fetch_transactions_with_metrics() -> tuple[
            list[Transaction], FetchMetrics
        ]:
            await asyncio.sleep(0.01)
            return [tx], metrics

        firefly_service.fetch_transactions_with_metrics = AsyncMock(
            side_effect=fetch_transactions_with_metrics
        )
        service = TransactionSnapshotService(
            store=store,
            firefly_service=firefly_service,
            max_age_seconds=300,
        )

        first_result, second_result = await asyncio.gather(
            service.refresh_snapshot(),
            service.refresh_snapshot(),
        )

        assert first_result is second_result
        firefly_service.fetch_transactions_with_metrics.assert_awaited_once()

    asyncio.run(run_test())


def test_get_cached_snapshot_timestamp_returns_none_for_stale_snapshot():
    async def run_test() -> None:
        store = InMemorySnapshotStore()
        snapshot = TransactionSnapshot(
            transactions=[build_transaction()],
            metrics=build_metrics(),
            fetched_at=datetime.now(UTC) - timedelta(seconds=301),
        )
        service = TransactionSnapshotService(
            store=store,
            firefly_service=MagicMock(),
            max_age_seconds=300,
        )

        await store.set_snapshot(snapshot)

        assert await service.get_cached_snapshot_timestamp() is None

    asyncio.run(run_test())
