import asyncio
from datetime import UTC, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from services.domain.bank_record import BankRecord
from services.domain.metrics import FetchMetrics
from services.domain.transaction import Transaction, TransactionUpdate, TxTag
from services.firefly_blik_service import FireflyBlikService


def test_preview_matches_blik_transactions():
    service = FireflyBlikService(MagicMock(), filter_desc_blik="blik")
    service.fetch_transaction = AsyncMock()
    service.update_transaction = AsyncMock()

    tx_match = Transaction(
        id=1,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        description="blik payment",
        tags=set(),
        notes=None,
        category=None,
    )
    tx_tagged = Transaction(
        id=2,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        description="blik payment",
        tags={TxTag.blik_done},
        notes=None,
        category=None,
    )
    service.fetch_transaction.return_value = [tx_match, tx_tagged]

    record = BankRecord(
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        details="BLIK payment",
        recipient="ACME",
        operation_amount=Decimal("10.00"),
    )

    results = asyncio.run(
        service.match(
            [record], filter_text=service.filter_desc_blik, tag_done=TxTag.blik_done
        )
    )

    service.update_transaction.assert_not_awaited()
    assert len(results) == 1
    assert results[0].tx is tx_match
    assert results[0].matches == [record]


def test_get_blik_metrics_aggregates_counts_and_months():
    service = FireflyBlikService(MagicMock(), filter_desc_blik="blik")
    service.fetch_transaction_with_metrics = AsyncMock()

    txs = [
        Transaction(
            id=1,
            date=date(2024, 1, 5),
            amount=Decimal("10.00"),
            description="blik",
            tags=set(),
            notes=None,
            category=None,
        ),
        Transaction(
            id=2,
            date=date(2024, 1, 15),
            amount=Decimal("20.00"),
            description="blik",
            tags={TxTag.blik_done},
            notes=None,
            category=None,
        ),
        Transaction(
            id=3,
            date=date(2024, 2, 1),
            amount=Decimal("5.00"),
            description="blik groceries",
            tags=set(),
            notes=None,
            category=None,
        ),
        Transaction(
            id=4,
            date=date(2024, 2, 10),
            amount=Decimal("7.00"),
            description="other",
            tags=set(),
            notes=None,
            category=None,
        ),
        Transaction(
            id=5,
            date=date(2024, 2, 12),
            amount=Decimal("30.00"),
            description="blik",
            tags=set(),
            notes=None,
            category="Food",
        ),
    ]
    metrics = FetchMetrics(
        total_transactions=50,
        fetching_duration_ms=250,
        invalid=0,
        multipart=0,
    )
    service.fetch_transaction_with_metrics.return_value = (txs, metrics)

    stats = asyncio.run(service.get_blik_metrics())

    assert stats.total_transactions == 50
    assert stats.single_part_transactions == 5
    assert stats.uncategorized_transactions == 4
    assert stats.filtered_by_description_exact == 1
    assert stats.filtered_by_description_partial == 2
    assert stats.not_processed_transactions == 1
    assert stats.not_processed_by_month == {"2024-01": 1}
    assert stats.inclomplete_procesed_by_month == {"2024-01": 1, "2024-02": 1}
    assert stats.time_stamp.tzinfo is UTC


def test_apply_match_delegates_to_update_transaction():
    service = FireflyBlikService(MagicMock(), filter_desc_blik="blik")
    service.update_transaction = AsyncMock()

    tx = Transaction(
        id=9,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        description="blik",
        tags=set(),
        notes=None,
        category=None,
    )
    payload = TransactionUpdate(description="updated")
    evidence = MagicMock()
    evidence.build_tx_update.return_value = payload

    asyncio.run(service.apply_match(tx, evidence))

    service.update_transaction.assert_awaited_once_with(tx, payload=payload)
