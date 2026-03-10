from collections.abc import Iterable
from typing import TypeVar

from services.domain.base import Matchable
from services.domain.match_result import MatchProcessingStatus, MatchResult
from services.domain.transaction import Transaction, TxTag

TMatchable = TypeVar("TMatchable", bound=Matchable)


def match_transactions[TMatchable: Matchable](
    txs: Iterable[Transaction], items: Iterable[TMatchable], tag_done: TxTag
) -> tuple[list[MatchResult], list[TMatchable]]:
    """
    Match each transaction against all candidate records
    using domain-level `compare` logic.
    """
    item_list = list(items)
    matched_indexes: set[int] = set()

    results: list[MatchResult] = []
    for tx in txs:
        tx_matches: list[Matchable] = []
        for index, item in enumerate(item_list):
            if item.compare(tx):
                tx_matches.append(item)
                matched_indexes.add(index)
        results.append(
            MatchResult(
                tx=tx,
                matches=tx_matches,
                status=MatchProcessingStatus.ALREADY_PROCESSED
                if tx.has_tag(tag_done)
                else MatchProcessingStatus.NEW,
            )
        )

    unmatched_items = [
        item for index, item in enumerate(item_list) if index not in matched_indexes
    ]
    return results, unmatched_items
