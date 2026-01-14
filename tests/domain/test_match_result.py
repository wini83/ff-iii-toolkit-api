from datetime import date
from decimal import Decimal

from services.domain.match_result import MatchResult
from services.domain.transaction import Transaction


def test_match_result_holds_tx_and_matches():
    tx = Transaction(
        id=1,
        date=date(2024, 1, 1),
        amount=Decimal("5.00"),
        description="blik",
        tags=set(),
        notes=None,
        category=None,
    )
    result = MatchResult(tx=tx, matches=[tx])

    assert result.tx is tx
    assert result.matches == [tx]
