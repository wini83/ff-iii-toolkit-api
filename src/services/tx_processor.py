from datetime import date
from typing import cast

import pandas as pd
from anyio import to_thread
from fireflyiii_enricher_core.firefly_client import (
    FireflyClient,
    SimplifiedCategory,
    SimplifiedItem,
    SimplifiedTx,
    filter_by_description,
    filter_single_part,
    filter_without_category,
    filter_without_tag,
    simplify_transactions,
)
from fireflyiii_enricher_core.matcher import TransactionMatcher

from api.models.blik_files import MatchResult, SimplifiedRecord, StatisticsResponse
from settings import settings


def add_line(existing: str | None, new_line: str) -> str:
    if existing:
        return existing + "\n" + new_line
    return new_line


def txs_to_df(txs: list[SimplifiedTx]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": tx.date,
            "tags": tx.tags,
        }
        for tx in txs
    )


def _group_not_processed_sync(txs: list[SimplifiedTx]) -> dict[str, int]:
    if not txs:
        return {}
    df = txs_to_df(txs)

    # YYYY-MM z daty
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["month"] = df["date"].dt.to_period("M").astype(str)  # type: ignore[attr-defined]

    return df.groupby("month").size().sort_index().to_dict()


async def group_not_processed_by_month(
    txs: list[SimplifiedTx],
) -> dict[str, int]:
    return await to_thread.run_sync(_group_not_processed_sync, txs)


class CategoryApplyError(RuntimeError):
    """Failed to assign category to transaction."""


class TransactionProcessor:
    """Logika przetwarzania i aktualizacji transakcji"""

    def __init__(self, firefly_client: FireflyClient):
        self.firefly_client = firefly_client

    def match(
        self,
        bank_records: list[SimplifiedRecord],
        filter_text: str,
        exact_match: bool = True,
        tag: str = "blik_done",
    ):
        min_date = min(r.date for r in bank_records)
        max_date = max(r.date for r in bank_records)
        raw = self.firefly_client.fetch_transactions(
            start_date=min_date, end_date=max_date
        )
        single = filter_single_part(raw)
        uncategorized = filter_without_category(single)
        filtered = filter_by_description(uncategorized, filter_text, exact_match)
        filtered = filter_without_tag(filtered, tag)
        firefly_transactions = simplify_transactions(filtered)

        txs: list[MatchResult] = []

        for tx in firefly_transactions:
            matches = TransactionMatcher.match(
                tx, cast(list[SimplifiedItem], bank_records)
            )
            txs.append(
                MatchResult(tx=tx, matches=cast(list[SimplifiedRecord], matches))
            )
        return txs

    def apply_match(self, tx: SimplifiedTx, record: SimplifiedRecord):
        if record.details.lower() not in (tx.description).lower():
            new_description = f"{tx.description};{record.details}"
            self.firefly_client.update_transaction_description(
                int(tx.id), new_description
            )
        notes = add_line(tx.notes, record.pretty_print(only_meaningful=True))
        self.firefly_client.update_transaction_notes(int(tx.id), notes)
        self.firefly_client.add_tag_to_transaction(int(tx.id), "blik_done")

    async def get_stats(
        self, description_filter: str, tag_done: str
    ) -> StatisticsResponse:
        raw_txs = self.firefly_client.fetch_transactions()
        single = filter_single_part(raw_txs)
        uncategorized = filter_without_category(single)
        filtered_by_desc_exact = filter_by_description(
            uncategorized, description_filter, True
        )
        filtered_by_desc_partial = filter_by_description(
            uncategorized, description_filter, False
        )

        incomplete_procesed = simplify_transactions(filtered_by_desc_partial)
        simplified = simplify_transactions(filtered_by_desc_exact)

        not_processed = [
            tx
            for tx in simplified
            if not tx.tags or settings.TAG_BLIK_DONE not in tx.tags
        ]

        incomplete_procesed = [
            tx
            for tx in incomplete_procesed
            if not tx.tags or settings.TAG_BLIK_DONE not in tx.tags
        ]

        not_processed_by_month = await group_not_processed_by_month(not_processed)
        incomplete_procesed_by_month = await group_not_processed_by_month(
            incomplete_procesed
        )

        return StatisticsResponse(
            total_transactions=len(raw_txs),
            single_part_transactions=len(single),
            uncategorized_transactions=len(uncategorized),
            filtered_by_description_exact=len(not_processed),
            filtered_by_description_partial=len(incomplete_procesed),
            not_processed_transactions=len(not_processed),
            not_processed_by_month=not_processed_by_month,
            inclomplete_procesed_by_month=incomplete_procesed_by_month,
        )

    async def get_txs_for_screening(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[SimplifiedTx]:
        txs = self.firefly_client.fetch_transactions(
            start_date=start_date, end_date=end_date
        )
        non_categorized = filter_without_category(filter_single_part(txs))
        txs_simplified = simplify_transactions(non_categorized)
        txs_simplified = [
            t
            for t in txs_simplified
            if (t.description != "BLIK - płatność w internecie")
        ]
        txs_simplified = [
            t
            for t in txs_simplified
            if not ("allegro" in t.description.lower() and "allegro_done" not in t.tags)
        ]
        return txs_simplified

    async def get_categories(self) -> list[SimplifiedCategory]:
        """Retrieve categories from Firefly III."""
        cats = self.firefly_client.fetch_categories(simplified=True)
        return cast(list[SimplifiedCategory], cats)

    async def apply_category(self, tx_id: int, category_id: int) -> None:
        try:
            self.firefly_client.assign_transaction_category(tx_id, category_id)
        except RuntimeError as e:
            raise CategoryApplyError(
                f"Failed to assign category {category_id} to tx {tx_id}"
            ) from e
