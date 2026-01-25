import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from ff_iii_luciferin.api import FireflyAPIError

from services.domain.transaction import Currency, Transaction, TxTag, TxType
from services.firefly_base_service import FireflyServiceError
from services.firefly_tx_service import FireflyTxService

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


def test_get_txs_for_screening_filters_transactions():
    service = FireflyTxService(
        MagicMock(), filter_desc_blik="blik", filter_desc_allegro="allegro"
    )
    service.fetch_transactions = AsyncMock()

    tx_blik = Transaction(
        id=1,
        date=date(2024, 1, 1),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx_action_req = Transaction(
        id=2,
        date=date(2024, 1, 2),
        amount=Decimal("20.00"),
        type=TxType.WITHDRAWAL,
        description="other",
        tags={TxTag.action_req},
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx_allegro_pending = Transaction(
        id=3,
        date=date(2024, 1, 3),
        amount=Decimal("30.00"),
        type=TxType.WITHDRAWAL,
        description="allegro order",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx_allegro_done = Transaction(
        id=4,
        date=date(2024, 1, 4),
        amount=Decimal("40.00"),
        type=TxType.WITHDRAWAL,
        description="allegro order",
        tags={TxTag.allegro_done},
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx_ok = Transaction(
        id=5,
        date=date(2024, 1, 5),
        amount=Decimal("50.00"),
        type=TxType.WITHDRAWAL,
        description="groceries",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )

    service.fetch_transactions.return_value = [
        tx_blik,
        tx_action_req,
        tx_allegro_pending,
        tx_allegro_done,
        tx_ok,
    ]

    result = asyncio.run(
        service.get_txs_for_screening(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
    )

    service.fetch_transactions.assert_awaited_once_with(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        exclude_categorized=True,
    )
    assert result == [tx_allegro_done, tx_ok]


def test_get_categories_maps_results():
    firefly_client = MagicMock()
    firefly_client.fetch_categories = AsyncMock(
        return_value=[
            SimpleNamespace(id=1, name="Food"),
            SimpleNamespace(id=2, name="Transport"),
        ]
    )
    service = FireflyTxService(
        firefly_client, filter_desc_blik="blik", filter_desc_allegro="allegro"
    )

    result = asyncio.run(service.get_categories())

    firefly_client.fetch_categories.assert_awaited_once_with()
    assert [c.id for c in result] == [1, 2]
    assert [c.name for c in result] == ["Food", "Transport"]


def test_get_categories_raises_firefly_service_error():
    firefly_client = MagicMock()
    firefly_client.fetch_categories = AsyncMock(
        side_effect=FireflyAPIError("boom", status_code=500)
    )
    service = FireflyTxService(
        firefly_client, filter_desc_blik="blik", filter_desc_allegro="allegro"
    )

    with pytest.raises(FireflyServiceError):
        asyncio.run(service.get_categories())


def test_apply_category_by_id_delegates_to_helpers():
    service = FireflyTxService(
        MagicMock(), filter_desc_blik="blik", filter_desc_allegro="allegro"
    )
    tx = Transaction(
        id=9,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="test",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    service.get_transaction = AsyncMock(return_value=tx)
    service.apply_category = AsyncMock()

    asyncio.run(service.apply_category_by_id(tx_id=9, category_id=33))

    service.get_transaction.assert_awaited_once_with(9)
    service.apply_category.assert_awaited_once_with(tx=tx, category_id=33)
