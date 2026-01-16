from datetime import date

from ff_iii_luciferin.api import FireflyAPIError, FireflyClient
from ff_iii_luciferin.services.transactions import fetch_transactions_with_stats

from services.domain.metrics import FetchMetrics
from services.domain.transaction import Transaction, TransactionUpdate
from services.mappers.firefly import tx_from_ff_tx, tx_update_to_ff_tx_update


class FireflyServiceError(RuntimeError):
    """Raised when Firefly III API calls fail."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def filter_by_description(
    transactions: list[Transaction],
    description_filter: str,
    exact_match: bool = True,
    exclude: bool = False,
) -> list[Transaction]:
    """Filter transactions by description, optionally excluding matches."""
    desc = description_filter.lower()

    def matches(t: Transaction) -> bool:
        t_desc = t.description.lower()
        if exact_match:
            return t_desc == desc
        return desc in t_desc

    return [t for t in transactions if matches(t) != exclude]


def filter_out_categorized(transactions: list[Transaction]) -> list[Transaction]:
    """Filter out transactions that already have a category set."""

    return [t for t in transactions if t.category is None]


def filter_out_by_tag(transactions: list[Transaction], tag: str) -> list[Transaction]:
    filtered: list[Transaction] = []
    for tx in transactions:
        if tag not in tx.tags:
            filtered.append(tx)
    return filtered


class FireflyBaseService:
    """Logika przetwarzania i aktualizacji transakcji"""

    def __init__(
        self,
        firefly_client: FireflyClient,
    ):
        self.firefly_client = firefly_client

    async def fetch_transactions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        page_size: int = 1000,
        max_pages: int | None = None,
        exclude_categorized: bool = False,
    ) -> list[Transaction]:
        try:
            ff_txs = await self.firefly_client.fetch_transactions(
                start_date=start_date,
                end_date=end_date,
                page_size=page_size,
                max_pages=max_pages,
            )
            domain_txs = [tx_from_ff_tx(tx) for tx in ff_txs]
        except FireflyAPIError as e:
            raise FireflyServiceError(
                message="Failed to fetch transactions from Firefly iii",
                status_code=e.status_code,
            ) from e
        if exclude_categorized:
            return filter_out_categorized(domain_txs)
        else:
            return domain_txs

    async def update_transaction(
        self, tx: Transaction, payload: TransactionUpdate
    ) -> None:
        payload_ff = tx_update_to_ff_tx_update(payload)
        try:
            await self.firefly_client.update_transaction(tx.id, payload_ff)
        except FireflyAPIError as e:
            raise FireflyServiceError(
                message=f"Failed to update transaction {tx.id}",
                status_code=e.status_code,
            ) from e

    async def fetch_transactions_with_metrics(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> tuple[list[Transaction], FetchMetrics]:
        try:
            ff_txs, stats = await fetch_transactions_with_stats(
                self.firefly_client, start_date=start_date, end_date=end_date
            )
        except FireflyAPIError as e:
            raise FireflyServiceError(
                message="Failed to fetch transactions from Firefly iii",
                status_code=e.status_code,
            ) from e
        domain_txs = [tx_from_ff_tx(tx) for tx in ff_txs]
        domain_stats = FetchMetrics(
            total_transactions=stats.total,
            fetching_duration_ms=stats.duration_ms,
            invalid=stats.invalid,
            multipart=stats.multipart,
        )
        return domain_txs, domain_stats
