from datetime import UTC, datetime

from ff_iii_luciferin.api import FireflyClient

from services.domain.metrics import BlikStatisticsMetrics
from services.domain.transaction import TxTag
from services.firefly_base_service import (
    filter_by_description,
    filter_out_categorized,
)
from services.firefly_enrichment_service import FireflyEnrichmentService
from services.tx_stats.helpers import group_tx_by_month


class FireflyBlikService(FireflyEnrichmentService):
    """Logika przetwarzania i aktualizacji transakcji"""

    def __init__(self, firefly_client: FireflyClient, filter_desc_blik: str):
        super().__init__(firefly_client)
        self.filter_desc_blik = filter_desc_blik

    async def fetch_metrics(self) -> BlikStatisticsMetrics:
        domain_txs, metrics = await self.fetch_transactions_with_metrics()
        uncategorized = filter_out_categorized(domain_txs)
        filtered_by_desc_exact = filter_by_description(
            uncategorized, self.filter_desc_blik, exact_match=True
        )
        filtered_by_desc_partial = filter_by_description(
            uncategorized, self.filter_desc_blik, exact_match=False
        )

        not_processed = [
            tx
            for tx in filtered_by_desc_exact
            if not tx.tags or TxTag.blik_done not in tx.tags
        ]

        incomplete_procesed = [
            tx
            for tx in filtered_by_desc_partial
            if not tx.tags or TxTag.blik_done not in tx.tags
        ]

        not_processed_by_month = await group_tx_by_month(not_processed)
        incomplete_procesed_by_month = await group_tx_by_month(incomplete_procesed)

        time_stamp: datetime = datetime.now(UTC)

        return BlikStatisticsMetrics(
            total_transactions=metrics.total_transactions,
            single_part_transactions=len(domain_txs),
            uncategorized_transactions=len(uncategorized),
            filtered_by_description_exact=len(not_processed),
            filtered_by_description_partial=len(incomplete_procesed),
            not_processed_transactions=len(not_processed),
            not_processed_by_month=not_processed_by_month,
            inclomplete_procesed_by_month=incomplete_procesed_by_month,
            time_stamp=time_stamp,
            fetching_duration_ms=metrics.fetching_duration_ms,
        )
