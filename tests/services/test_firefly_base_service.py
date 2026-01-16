import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ff_iii_luciferin.api import FireflyAPIError

from services.domain.transaction import Transaction, TransactionUpdate
from services.firefly_base_service import FireflyBaseService, FireflyServiceError


def test_fetch_transactions_excludes_categorized():
    firefly_client = MagicMock()
    firefly_client.fetch_transactions = AsyncMock(
        return_value=[
            SimpleNamespace(
                id=1,
                date=date(2024, 1, 1),
                amount=Decimal("10.00"),
                description="A",
                tags=[],
                notes=None,
                category=None,
            ),
            SimpleNamespace(
                id=2,
                date=date(2024, 1, 2),
                amount=Decimal("20.00"),
                description="B",
                tags=[],
                notes=None,
                category="Food",
            ),
        ]
    )
    service = FireflyBaseService(firefly_client)

    result = asyncio.run(
        service.fetch_transactions(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            exclude_categorized=True,
        )
    )

    firefly_client.fetch_transactions.assert_awaited_once_with(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        page_size=1000,
        max_pages=None,
    )
    assert [t.id for t in result] == [1]
    assert all(isinstance(t, Transaction) for t in result)


def test_fetch_transactions_raises_firefly_service_error():
    firefly_client = MagicMock()
    firefly_client.fetch_transactions = AsyncMock(
        side_effect=FireflyAPIError("boom", status_code=500)
    )
    service = FireflyBaseService(firefly_client)

    with pytest.raises(FireflyServiceError):
        asyncio.run(service.fetch_transactions())


def test_update_transaction_delegates_to_client():
    firefly_client = MagicMock()
    firefly_client.update_transaction = AsyncMock()
    service = FireflyBaseService(firefly_client)
    tx = Transaction(
        id=7,
        date=date(2024, 1, 1),
        amount=Decimal("10.00"),
        description="Test",
        tags=set(),
        notes=None,
        category=None,
    )
    payload = TransactionUpdate(description="Updated")

    asyncio.run(service.update_transaction(tx, payload=payload))

    firefly_client.update_transaction.assert_awaited_once()


def test_fetch_transactions_with_metrics_maps_stats():
    firefly_client = MagicMock()
    service = FireflyBaseService(firefly_client)
    ff_txs = [
        SimpleNamespace(
            id=1,
            date=date(2024, 1, 1),
            amount=Decimal("10.00"),
            description="A",
            tags=[],
            notes=None,
            category=None,
        )
    ]
    stats = SimpleNamespace(total=5, duration_ms=123, invalid=1, multipart=2)

    with patch(
        "services.firefly_base_service.fetch_transactions_with_stats",
        new=AsyncMock(return_value=(ff_txs, stats)),
    ):
        result_txs, metrics = asyncio.run(service.fetch_transactions_with_metrics())

    assert len(result_txs) == 1
    assert metrics.total_transactions == 5
    assert metrics.fetching_duration_ms == 123
    assert metrics.invalid == 1
    assert metrics.multipart == 2
