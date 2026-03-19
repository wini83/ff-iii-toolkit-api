from datetime import date

from ff_iii_luciferin.api import FireflyAPIError, FireflyClient

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
)
from services.mappers.firefly import category_from_ff_category, tx_from_ff_tx


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
