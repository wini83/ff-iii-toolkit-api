import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from services.domain.bank_record import BankRecord
from services.domain.transaction import (
    Currency,
    Transaction,
    TransactionUpdate,
    TxTag,
    TxType,
)
from services.firefly_enrichment_service import FireflyEnrichmentService

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


def test_match_filters_and_does_not_update_transactions():
    service = FireflyEnrichmentService(MagicMock())
    service.fetch_transactions = AsyncMock()
    service.update_transaction = AsyncMock()

    tx_match = Transaction(
        id=1,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="blik payment",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx_tagged = Transaction(
        id=2,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="blik payment",
        tags={TxTag.blik_done},
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    tx_other = Transaction(
        id=3,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="other",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    service.fetch_transactions.return_value = [tx_match, tx_tagged, tx_other]

    record = BankRecord(
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        details="BLIK payment",
        recipient="ACME",
        operation_amount=Decimal("10.00"),
    )

    results = asyncio.run(
        service.match([record], filter_text="blik", tag_done=TxTag.blik_done)
    )

    service.fetch_transactions.assert_awaited_once_with(
        start_date=date(2024, 1, 5),
        end_date=date(2024, 1, 5),
        exclude_categorized=True,
    )
    service.update_transaction.assert_not_awaited()

    assert len(results) == 1
    assert results[0].tx is tx_match
    assert results[0].matches == [record]


def test_apply_match_calls_update_transaction():
    service = FireflyEnrichmentService(MagicMock())
    service.update_transaction = AsyncMock()

    tx = Transaction(
        id=1,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    payload = TransactionUpdate(description="updated")
    evidence = MagicMock()
    evidence.build_tx_update.return_value = payload

    asyncio.run(service.apply_match(tx, evidence))

    service.update_transaction.assert_awaited_once_with(tx, payload=payload)
