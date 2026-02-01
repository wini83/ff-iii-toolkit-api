from datetime import UTC, date, datetime

from ff_iii_luciferin.api import FireflyAPIError, FireflyClient

from services.domain.metrics import TXStatisticsMetrics
from services.domain.transaction import (
    Category,
    Transaction,
    TransactionUpdate,
    TxTag,
)
from services.firefly_base_service import (
    FireflyBaseService,
    FireflyServiceError,
    filter_by_description,
    filter_out_categorized,
)
from services.mappers.firefly import category_from_ff_category, tx_from_ff_tx
from services.tx_stats.helpers import group_tx_by_month


class FireflyTxService(FireflyBaseService):
    def __init__(
        self,
        firefly_client: FireflyClient,
        filter_desc_blik: str,
        filter_desc_allegro: str,
    ):
        super().__init__(firefly_client)
        self.filter_desc_blik = filter_desc_blik
        self.filter_desc_allegro = filter_desc_allegro

    async def get_txs_for_screening(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[Transaction]:
        domain_txs = await self.fetch_transactions(
            start_date=start_date, end_date=end_date, exclude_categorized=True
        )
        filtered = filter_by_description(
            domain_txs, self.filter_desc_blik, exact_match=True, exclude=True
        )
        filtered = [t for t in filtered if TxTag.action_req not in t.tags]
        filtered = [
            t
            for t in filtered
            if not (
                self.filter_desc_allegro in t.description.lower()
                and TxTag.allegro_done not in t.tags
            )
        ]
        return filtered

    async def get_categories(self) -> list[Category]:
        """Retrieve categories from Firefly III."""
        try:
            ff_cats = await self.firefly_client.fetch_categories()
        except FireflyAPIError as e:
            raise FireflyServiceError(
                message="Failed to fetch categories from Firefly iii",
                status_code=e.status_code,
            ) from e
        return [category_from_ff_category(cat) for cat in ff_cats]

    async def get_transaction(self, tx_id: int) -> Transaction:
        """Retrieve a single transaction from Firefly III."""
        try:
            ff_tx = await self.firefly_client.get_transaction(tx_id)
        except FireflyAPIError as e:
            raise FireflyServiceError(
                message=f"Failed to fetch transaction {tx_id}",
                status_code=e.status_code,
            ) from e
        return tx_from_ff_tx(ff_tx)

    async def apply_category(self, tx: Transaction, category_id: int) -> None:
        payload = TransactionUpdate(category_id=category_id)
        await self.update_transaction(tx, payload=payload)

    async def add_tag(self, tx: Transaction, tag: str) -> None:
        tx.tags.add(tag)
        paytoad = TransactionUpdate(tags=list(tx.tags))
        await self.update_transaction(tx, paytoad)

    async def apply_category_by_id(self, tx_id: int, category_id: int) -> None:
        tx = await self.get_transaction(tx_id)
        await self.apply_category(tx=tx, category_id=category_id)

    async def add_tag_by_id(self, tx_id: int, tag: str) -> None:
        tx = await self.get_transaction(tx_id)
        await self.add_tag(tx=tx, tag=tag)

    async def fetch_metrics(self):
        domain_txs, metrics = await self.fetch_transactions_with_metrics()
        txs_uncategorized = filter_out_categorized(domain_txs)
        txs_blik_ok = filter_by_description(
            txs_uncategorized, self.filter_desc_blik, exact_match=True, exclude=True
        )
        txs_action_not_req = [t for t in txs_blik_ok if TxTag.action_req not in t.tags]
        txs_allegro_ok = [
            t
            for t in txs_action_not_req
            if not (
                self.filter_desc_allegro in t.description.lower()
                and TxTag.allegro_done not in t.tags
            )
        ]
        categorizable_by_month = await group_tx_by_month(txs_allegro_ok)
        return TXStatisticsMetrics(
            total_transactions=metrics.total_transactions,
            single_part_transactions=len(domain_txs),
            uncategorized_transactions=len(txs_uncategorized),
            blik_not_ok=len(txs_uncategorized) - len(txs_blik_ok),
            action_req=len(txs_blik_ok) - len(txs_action_not_req),
            allegro_not_ok=len(txs_action_not_req) - len(txs_allegro_ok),
            categorizable=len(txs_allegro_ok),
            categorizable_by_month=categorizable_by_month,
            time_stamp=datetime.now(UTC),
            fetching_duration_ms=metrics.fetching_duration_ms,
        )
