import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.models.tx import TxTag
from services.domain.job_base import JobStatus
from services.domain.transaction import Category, Currency, Transaction, TxType
from services.exceptions import ExternalServiceFailed
from services.firefly_base_service import FireflyServiceError
from services.firefly_tx_service import FireflyTxService
from services.tx_application_service import TxApplicationService
from services.tx_stats.models import MetricsState

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


def test_get_screening_month_returns_data_and_calls_services():
    tx = Transaction(
        id=1,
        date=date(2024, 2, 5),
        amount=Decimal("12.50"),
        type=TxType.WITHDRAWAL,
        description="Coffee",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    categories = [Category(id=10, name="Food")]

    tx_service = MagicMock(spec=FireflyTxService)
    tx_service.get_categories = AsyncMock(return_value=categories)
    tx_service.get_txs_for_screening = AsyncMock(return_value=[tx])

    service = TxApplicationService(tx_service=tx_service, metrics_provider=MagicMock())

    response = asyncio.run(service.get_screening_month(year=2024, month=2))

    tx_service.get_categories.assert_awaited_once_with()
    tx_service.get_txs_for_screening.assert_awaited_once_with(
        start_date=date(2024, 2, 1),
        end_date=date(2024, 2, 29),
    )
    assert response is not None
    assert response.year == 2024
    assert response.month == 2
    assert response.remaining == 1
    assert response.transactions[0].id == tx.id
    assert response.categories[0].id == 10


def test_get_screening_month_returns_none_when_no_transactions():
    tx_service = MagicMock(spec=FireflyTxService)
    tx_service.get_categories = AsyncMock(return_value=[])
    tx_service.get_txs_for_screening = AsyncMock(return_value=[])

    service = TxApplicationService(tx_service=tx_service, metrics_provider=MagicMock())

    response = asyncio.run(service.get_screening_month(year=2024, month=2))

    tx_service.get_categories.assert_awaited_once_with()
    tx_service.get_txs_for_screening.assert_awaited_once()
    assert response is None


def test_get_screening_month_propagates_firefly_error():
    tx_service = MagicMock(spec=FireflyTxService)
    tx_service.get_categories = AsyncMock(side_effect=FireflyServiceError("boom"))

    service = TxApplicationService(tx_service=tx_service, metrics_provider=MagicMock())

    with pytest.raises(ExternalServiceFailed):
        asyncio.run(service.get_screening_month(year=2024, month=2))


def test_get_tx_metrics_triggers_refresh_when_pending():
    tx_service = MagicMock(spec=FireflyTxService)
    service = TxApplicationService(tx_service=tx_service, metrics_provider=MagicMock())
    expected_state = MetricsState(
        status=JobStatus.RUNNING,
        result=None,
        error=None,
        progress="queued",
        last_updated_at=None,
    )
    service.tx_metrics_manager = MagicMock()
    service.tx_metrics_manager.get_state.return_value = MetricsState(
        status=JobStatus.PENDING,
        result=None,
        error=None,
        progress=None,
        last_updated_at=None,
    )
    service.tx_metrics_manager.ensure_current = AsyncMock(return_value=expected_state)

    state = asyncio.run(service.get_tx_metrics())

    service.tx_metrics_manager.ensure_current.assert_awaited_once()
    assert state is expected_state


def test_apply_category_delegates_to_tx_service():
    tx_service = MagicMock(spec=FireflyTxService)
    tx_service.apply_category_by_id = AsyncMock()
    service = TxApplicationService(tx_service=tx_service, metrics_provider=MagicMock())

    asyncio.run(service.apply_category(tx_id=10, category_id=20))

    tx_service.apply_category_by_id.assert_awaited_once_with(tx_id=10, category_id=20)


def test_apply_category_maps_firefly_error():
    tx_service = MagicMock(spec=FireflyTxService)
    tx_service.apply_category_by_id = AsyncMock(side_effect=FireflyServiceError("boom"))
    service = TxApplicationService(tx_service=tx_service, metrics_provider=MagicMock())

    with pytest.raises(ExternalServiceFailed, match="boom"):
        asyncio.run(service.apply_category(tx_id=10, category_id=20))


def test_apply_tag_delegates_to_tx_service():
    tx_service = MagicMock(spec=FireflyTxService)
    tx_service.add_tag_by_id = AsyncMock()
    service = TxApplicationService(tx_service=tx_service, metrics_provider=MagicMock())

    asyncio.run(service.apply_tag(tx_id=10, tag=TxTag.blik_done))

    tx_service.add_tag_by_id.assert_awaited_once_with(tx_id=10, tag="blik_done")


def test_apply_tag_maps_firefly_error():
    tx_service = MagicMock(spec=FireflyTxService)
    tx_service.add_tag_by_id = AsyncMock(side_effect=FireflyServiceError("boom"))
    service = TxApplicationService(tx_service=tx_service, metrics_provider=MagicMock())

    with pytest.raises(ExternalServiceFailed, match="boom"):
        asyncio.run(service.apply_tag(tx_id=10, tag=TxTag.blik_done))


def test_refresh_tx_metrics_delegates_to_manager():
    tx_service = MagicMock(spec=FireflyTxService)
    service = TxApplicationService(tx_service=tx_service, metrics_provider=MagicMock())
    expected_state = MetricsState(
        status=JobStatus.RUNNING,
        result=None,
        error=None,
        progress="queued",
        last_updated_at=None,
    )
    service.tx_metrics_manager = MagicMock()
    service.tx_metrics_manager.refresh = AsyncMock(return_value=expected_state)

    state = asyncio.run(service.refresh_tx_metrics())

    service.tx_metrics_manager.refresh.assert_awaited_once()
    assert state is expected_state
