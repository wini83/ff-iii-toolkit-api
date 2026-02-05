from datetime import UTC, datetime

from ff_iii_luciferin.api import FireflyClient

from services.domain.metrics import AllegroMetrics
from services.domain.transaction import TxTag
from services.firefly_base_service import (
    filter_by_description,
)
from services.firefly_enrichment_service import FireflyEnrichmentService
from services.tx_stats.helpers import group_tx_by_month


class FireflyAllegroService(FireflyEnrichmentService):
    """Logika przetwarzania i aktualizacji transakcji"""

    def __init__(self, firefly_client: FireflyClient, filter_desc_allegro: str):
        super().__init__(firefly_client)
        self.filter_desc_allegro = filter_desc_allegro

    async def fetch_metrics(self) -> AllegroMetrics:
        domain_txs, metrics = await self.fetch_transactions_with_metrics()

        filtered_by_desc_partial = filter_by_description(
            domain_txs, self.filter_desc_allegro, exact_match=False
        )

        not_processed = [
            tx
            for tx in filtered_by_desc_partial
            if not tx.tags or TxTag.allegro_done not in tx.tags
        ]

        not_processed_by_month = await group_tx_by_month(not_processed)

        time_stamp: datetime = datetime.now(UTC)

        return AllegroMetrics(
            total_transactions=metrics.total_transactions,
            fetching_duration_ms=metrics.fetching_duration_ms,
            allegro_transactions=len(filtered_by_desc_partial),
            not_processed_allegro_transactions=len(not_processed),
            not_processed_by_month=not_processed_by_month,
            time_stamp=time_stamp,
        )
