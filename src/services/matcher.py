from collections.abc import Iterable

from services.domain.base import Matchable
from services.domain.match_result import MatchResult


def match_transactions(
    txs: Iterable[Matchable],
    items: Iterable[Matchable],
) -> list[MatchResult]:
    """
    Match each transaction against all candidate records
    using domain-level `compare` logic.
    """
    item_list = list(items)

    return [
        MatchResult(
            tx=tx,
            matches=[r for r in item_list if r.compare(tx)],
        )
        for tx in txs
    ]
