from datetime import date
from decimal import Decimal

from services.domain.bank_record import BankRecord
from services.domain.match_result import MatchProcessingStatus
from services.domain.transaction import Currency, Transaction, TxTag, TxType
from services.matcher import match_transactions

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


def test_match_transactions_returns_matches_and_unmatched_items():
    tx = Transaction(
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

    matched_item = BankRecord(
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        details="BLIK payment",
        recipient="ACME",
        operation_amount=Decimal("10.00"),
    )
    unmatched_item = BankRecord(
        date=date(2024, 1, 6),
        amount=Decimal("12.00"),
        details="BLIK payment",
        recipient="SHOP",
        operation_amount=Decimal("12.00"),
    )

    results, unmatched_items = match_transactions(
        txs=[tx],
        items=[matched_item, unmatched_item],
        tag_done=TxTag.blik_done,
    )

    assert len(results) == 1
    assert results[0].tx is tx
    assert results[0].status == MatchProcessingStatus.NEW
    assert results[0].matches == [matched_item]
    assert unmatched_items == [unmatched_item]
