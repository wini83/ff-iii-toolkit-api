import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ff_iii_luciferin.api import FireflyAPIError

from services.domain.transaction import (
    AccountRef,
    AccountType,
    Currency,
    Transaction,
    TransactionUpdate,
    TxType,
)
from services.firefly_base_service import (
    FireflyBaseService,
    FireflyServiceError,
    filter_by_description,
    filter_out_by_tag,
)

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


def test_fetch_transactions_excludes_categorized():
    firefly_client = MagicMock()
    firefly_client.fetch_transactions = AsyncMock(
        return_value=[
            SimpleNamespace(
                id=1,
                date=date(2024, 1, 1),
                amount=Decimal("10.00"),
                type=SimpleNamespace(value="withdrawal"),
                description="A",
                tags=[],
                notes=None,
                category=None,
                currency=SimpleNamespace(code="PLN", symbol="zl", decimals=2),
                fx=None,
                source_account=SimpleNamespace(
                    id=11,
                    name="Main account",
                    type=SimpleNamespace(value="asset"),
                    iban="PL123",
                ),
                destination_account=None,
            ),
            SimpleNamespace(
                id=2,
                date=date(2024, 1, 2),
                amount=Decimal("20.00"),
                type=SimpleNamespace(value="withdrawal"),
                description="B",
                tags=[],
                notes=None,
                category=SimpleNamespace(id=1, name="Food"),
                currency=SimpleNamespace(code="PLN", symbol="zl", decimals=2),
                fx=None,
                source_account=None,
                destination_account=None,
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
    assert result[0].source_account == AccountRef(
        id=11,
        name="Main account",
        type=AccountType.ASSET,
        iban="PL123",
    )
    assert result[0].destination_account is None


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
        type=TxType.WITHDRAWAL,
        description="Test",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
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
            type=SimpleNamespace(value="withdrawal"),
            description="A",
            tags=[],
            notes=None,
            category=None,
            currency=SimpleNamespace(code="PLN", symbol="zl", decimals=2),
            fx=None,
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


def test_filter_by_description_supports_partial_matching_and_exclude():
    tx1 = Transaction(
        id=1,
        date=date(2024, 1, 1),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="Allegro order",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx2 = Transaction(
        id=2,
        date=date(2024, 1, 2),
        amount=Decimal("20.00"),
        type=TxType.WITHDRAWAL,
        description="Groceries",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )

    included = filter_by_description([tx1, tx2], "allegro", exact_match=False)
    excluded = filter_by_description(
        [tx1, tx2], "allegro", exact_match=False, exclude=True
    )

    assert included == [tx1]
    assert excluded == [tx2]


def test_filter_out_by_tag_returns_transactions_without_tag():
    tagged = Transaction(
        id=1,
        date=date(2024, 1, 1),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="Tagged",
        tags={"done"},
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    clean = Transaction(
        id=2,
        date=date(2024, 1, 2),
        amount=Decimal("20.00"),
        type=TxType.WITHDRAWAL,
        description="Clean",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )

    result = filter_out_by_tag([tagged, clean], "done")

    assert result == [clean]


def test_update_transaction_raises_firefly_service_error():
    firefly_client = MagicMock()
    firefly_client.update_transaction = AsyncMock(
        side_effect=FireflyAPIError("boom", status_code=409)
    )
    service = FireflyBaseService(firefly_client)
    tx = Transaction(
        id=7,
        date=date(2024, 1, 1),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="Test",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    payload = TransactionUpdate(description="Updated")

    with pytest.raises(FireflyServiceError, match="Failed to update transaction 7"):
        asyncio.run(service.update_transaction(tx, payload=payload))


def test_fetch_transactions_with_metrics_raises_firefly_service_error():
    firefly_client = MagicMock()
    service = FireflyBaseService(firefly_client)

    with (
        patch(
            "services.firefly_base_service.fetch_transactions_with_stats",
            new=AsyncMock(side_effect=FireflyAPIError("boom", status_code=503)),
        ),
        pytest.raises(
            FireflyServiceError, match="Failed to fetch transactions from Firefly iii"
        ),
    ):
        asyncio.run(service.fetch_transactions_with_metrics())
