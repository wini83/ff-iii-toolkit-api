from datetime import date
from decimal import Decimal

from services.domain.match_result import MatchResult
from services.domain.transaction import Currency, Transaction, TxType

DEFAULT_CURRENCY = Currency(code="PLN", symbol="zl", decimals=2)


def test_match_result_holds_tx_and_matches():
    tx = Transaction(
        id=1,
        date=date(2024, 1, 1),
        amount=Decimal("5.00"),
        type=TxType.WITHDRAWAL,
        description="blik",
        tags=set(),
        notes=None,
        category=None,
        currency=DEFAULT_CURRENCY,
    )
    result = MatchResult(tx=tx, matches=[tx])

    assert result.tx is tx
    assert result.matches == [tx]
