import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from services.domain.metrics import FetchMetrics
from services.domain.transaction import Category, Currency, Transaction, TxTag, TxType
from services.snapshot.metrics import (
    SnapshotAllegroMetricsService,
    SnapshotBlikMetricsService,
    SnapshotTxMetricsService,
)
from services.snapshot.models import TransactionSnapshot

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


def _tx(
    tx_id: int,
    *,
    tx_date: date,
    description: str,
    tags: set[str] | None = None,
    category: Category | None = None,
) -> Transaction:
    return Transaction(
        id=tx_id,
        date=tx_date,
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description=description,
        tags=tags or set(),
        notes=None,
        category=category,
        currency=DEFAULT_CURRENCY,
    )


def _snapshot(
    transactions: list[Transaction], *, fetched_at: datetime | None = None
) -> TransactionSnapshot:
    return TransactionSnapshot(
        transactions=transactions,
        metrics=FetchMetrics(
            total_transactions=50,
            fetching_duration_ms=250,
            invalid=0,
            multipart=0,
        ),
        fetched_at=fetched_at or datetime.now(UTC),
    )


def test_snapshot_blik_metrics_aggregates_counts_and_months():
    transactions = [
        _tx(1, tx_date=date(2024, 1, 5), description="blik"),
        _tx(
            2,
            tx_date=date(2024, 1, 15),
            description="blik",
            tags={TxTag.blik_done},
        ),
        _tx(3, tx_date=date(2024, 2, 1), description="blik groceries"),
        _tx(4, tx_date=date(2024, 2, 10), description="other"),
        _tx(
            5,
            tx_date=date(2024, 2, 12),
            description="blik",
            category=Category(id=1, name="Food"),
        ),
    ]
    fetched_at = datetime(2024, 3, 1, 10, 30, tzinfo=UTC)
    snapshot_service = MagicMock()
    snapshot_service.get_snapshot = AsyncMock(
        return_value=_snapshot(transactions, fetched_at=fetched_at)
    )
    service = SnapshotBlikMetricsService(
        snapshot_service=snapshot_service,
        filter_desc_blik="blik",
    )

    stats = asyncio.run(service.fetch_metrics())

    assert stats.total_transactions == 50
    assert stats.single_part_transactions == 5
    assert stats.uncategorized_transactions == 4
    assert stats.filtered_by_description_exact == 1
    assert stats.filtered_by_description_partial == 2
    assert stats.not_processed_transactions == 1
    assert stats.not_processed_by_month == {"2024-01": 1}
    assert stats.inclomplete_procesed_by_month == {"2024-01": 1, "2024-02": 1}
    assert stats.time_stamp == fetched_at


def test_snapshot_allegro_metrics_aggregates_counts_and_months():
    transactions = [
        _tx(1, tx_date=date(2024, 1, 5), description="allegro order"),
        _tx(
            2,
            tx_date=date(2024, 1, 20),
            description="allegro order",
            tags={TxTag.allegro_done},
        ),
        _tx(3, tx_date=date(2024, 2, 8), description="other"),
    ]
    fetched_at = datetime(2024, 3, 2, 9, 15, tzinfo=UTC)
    snapshot_service = MagicMock()
    snapshot_service.get_snapshot = AsyncMock(
        return_value=_snapshot(transactions, fetched_at=fetched_at)
    )
    service = SnapshotAllegroMetricsService(
        snapshot_service=snapshot_service,
        filter_desc_allegro="allegro",
    )

    stats = asyncio.run(service.fetch_metrics())

    assert stats.total_transactions == 50
    assert stats.allegro_transactions == 2
    assert stats.not_processed_allegro_transactions == 1
    assert stats.not_processed_by_month == {"2024-01": 1}
    assert stats.time_stamp == fetched_at


def test_snapshot_tx_metrics_aggregates_categorizable_counts():
    transactions = [
        _tx(1, tx_date=date(2024, 1, 1), description="blik"),
        _tx(
            2,
            tx_date=date(2024, 1, 2),
            description="other",
            tags={TxTag.action_req},
        ),
        _tx(3, tx_date=date(2024, 1, 3), description="allegro order"),
        _tx(
            4,
            tx_date=date(2024, 1, 4),
            description="allegro order",
            tags={TxTag.allegro_done},
        ),
        _tx(5, tx_date=date(2024, 1, 5), description="groceries"),
    ]
    fetched_at = datetime(2024, 3, 3, 8, 0, tzinfo=UTC)
    snapshot_service = MagicMock()
    snapshot_service.get_snapshot = AsyncMock(
        return_value=_snapshot(transactions, fetched_at=fetched_at)
    )
    service = SnapshotTxMetricsService(
        snapshot_service=snapshot_service,
        filter_desc_blik="blik",
        filter_desc_allegro="allegro",
    )

    stats = asyncio.run(service.fetch_metrics())

    assert stats.total_transactions == 50
    assert stats.single_part_transactions == 5
    assert stats.uncategorized_transactions == 5
    assert stats.blik_not_ok == 1
    assert stats.action_req == 1
    assert stats.allegro_not_ok == 1
    assert stats.categorizable == 2
    assert stats.categorizable_by_month == {"2024-01": 2}
    assert stats.time_stamp == fetched_at


def test_snapshot_blik_refresh_metrics_uses_forced_snapshot_refresh():
    fetched_at = datetime(2024, 3, 4, 12, 0, tzinfo=UTC)
    snapshot_service = MagicMock()
    snapshot_service.get_snapshot = AsyncMock()
    snapshot_service.refresh_snapshot = AsyncMock(
        return_value=_snapshot(
            [_tx(1, tx_date=date(2024, 1, 5), description="blik")],
            fetched_at=fetched_at,
        )
    )
    service = SnapshotBlikMetricsService(
        snapshot_service=snapshot_service,
        filter_desc_blik="blik",
    )

    stats = asyncio.run(service.refresh_metrics())

    snapshot_service.get_snapshot.assert_not_awaited()
    snapshot_service.refresh_snapshot.assert_awaited_once()
    assert stats.time_stamp == fetched_at
