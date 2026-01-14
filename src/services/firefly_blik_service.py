from datetime import UTC, datetime

import pandas as pd
from anyio import to_thread
from ff_iii_luciferin.api import FireflyClient

from services.domain.metrics import BlikStatisticsMetrics
from services.domain.transaction import Transaction, TxTag
from services.firefly_base_service import (
    filter_by_description,
    filter_out_categorized,
)
from services.firefly_enrichment_service import FireflyEnrichmentService


def txs_to_df(txs: list[Transaction]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": tx.date,
            "tags": tx.tags,
        }
        for tx in txs
    )


def _group_tx_by_month_sync(txs: list[Transaction]) -> dict[str, int]:
    if not txs:
        return {}
    df = txs_to_df(txs)

    # YYYY-MM z daty
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["month"] = df["date"].dt.to_period("M").astype(str)  # type: ignore[attr-defined]

    return df.groupby("month").size().sort_index().to_dict()


async def group_tx_by_month(
    txs: list[Transaction],
) -> dict[str, int]:
    return await to_thread.run_sync(_group_tx_by_month_sync, txs)


class FireflyBlikService(FireflyEnrichmentService):
    """Logika przetwarzania i aktualizacji transakcji"""

    def __init__(self, firefly_client: FireflyClient, filter_desc_blik: str):
        super().__init__(firefly_client)
        self.filter_desc_blik = filter_desc_blik

    async def fetch_blik_metrics(self) -> BlikStatisticsMetrics:
        domain_txs, metrics = await self.fetch_transaction_with_metrics()
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
