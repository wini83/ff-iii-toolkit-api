from collections.abc import Sequence

from ff_iii_luciferin.api import FireflyClient

from services.domain.base import BaseMatchItem
from services.domain.evidence import Evidence
from services.domain.transaction import Transaction
from services.firefly_base_service import (
    FireflyBaseService,
    filter_by_description,
    filter_out_by_tag,
)
from services.matcher import match_transactions


class FireflyEnrichmentService(FireflyBaseService):
    def __init__(self, firefly_client: FireflyClient):
        super().__init__(firefly_client)

    async def match(
        self, candidates: Sequence[BaseMatchItem], filter_text: str, tag_done: str
    ):
        min_date = min(r.date for r in candidates)
        max_date = max(r.date for r in candidates)
        domain_txs = await self.fetch_transaction(
            start_date=min_date, end_date=max_date, exclude_categorized=True
        )
        filtered = filter_by_description(domain_txs, filter_text, exact_match=False)
        filtered = filter_out_by_tag(filtered, tag_done)

        return match_transactions(
            txs=filtered,
            items=candidates,
        )

    async def apply_match(self, tx: Transaction, evidence: Evidence) -> None:
        payload = evidence.build_tx_update(tx)
        await self.update_transaction(tx, payload=payload)
