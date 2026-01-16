import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.domain.transaction import Category, Transaction
from services.exceptions import ExternalServiceFailed
from services.firefly_base_service import FireflyServiceError
from services.firefly_tx_service import FireflyTxService
from services.tx_application_service import TxApplicationService


def test_get_screening_month_returns_data_and_calls_services():
    tx = Transaction(
        id=1,
        date=date(2024, 2, 5),
        amount=Decimal("12.50"),
        description="Coffee",
        tags=set(),
        notes=None,
        category=None,
    )
    categories = [Category(id=10, name="Food")]

    tx_service = MagicMock(spec=FireflyTxService)
    tx_service.get_categories = AsyncMock(return_value=categories)
    tx_service.get_txs_for_screening = AsyncMock(return_value=[tx])

    service = TxApplicationService(tx_service=tx_service)

    response = asyncio.run(service.get_screening_month(year=2024, month=2))

    tx_service.get_categories.assert_awaited_once_with()
    tx_service.get_txs_for_screening.assert_awaited_once_with(
        start_date=date(2024, 2, 1),
        end_date=date(2024, 2, 29),
    )
    assert response.year == 2024
    assert response.month == 2
    assert response.remaining == 1
    assert response.transactions[0].id == tx.id
    assert response.categories[0].id == 10


def test_get_screening_month_returns_none_when_no_transactions():
    tx_service = MagicMock(spec=FireflyTxService)
    tx_service.get_categories = AsyncMock(return_value=[])
    tx_service.get_txs_for_screening = AsyncMock(return_value=[])

    service = TxApplicationService(tx_service=tx_service)

    response = asyncio.run(service.get_screening_month(year=2024, month=2))

    tx_service.get_categories.assert_awaited_once_with()
    tx_service.get_txs_for_screening.assert_awaited_once()
    assert response is None


def test_get_screening_month_propagates_firefly_error():
    tx_service = MagicMock(spec=FireflyTxService)
    tx_service.get_categories = AsyncMock(side_effect=FireflyServiceError("boom"))

    service = TxApplicationService(tx_service=tx_service)

    with pytest.raises(ExternalServiceFailed):
        asyncio.run(service.get_screening_month(year=2024, month=2))
