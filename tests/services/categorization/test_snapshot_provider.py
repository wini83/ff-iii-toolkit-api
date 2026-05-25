import asyncio
from datetime import date, datetime
from decimal import Decimal

from services.categorization.amount_bucketizer import AmountBucketizer
from services.categorization.snapshot_provider import SnapshotCategorizationProvider
from services.domain.metrics import FetchMetrics
from services.domain.transaction import (
    AccountRef,
    AccountType,
    Category,
    Currency,
    Transaction,
    TxTag,
    TxType,
)
from services.snapshot.models import TransactionSnapshot


class _SnapshotService:
    def __init__(self, snapshot: TransactionSnapshot) -> None:
        self._snapshot = snapshot

    async def get_snapshot(self) -> TransactionSnapshot:
        return self._snapshot


def _transaction(
    *,
    tx_id: int,
    tx_type: TxType,
    amount: Decimal,
    category: Category | None,
    tags: set[str] | None = None,
    notes: str | None = None,
    merchant: str | None = None,
    source_account: AccountRef | None = None,
    destination_account: AccountRef | None = None,
) -> Transaction:
    tx = Transaction(
        id=tx_id,
        date=date(2024, 1, 1),
        amount=amount,
        type=tx_type,
        description=f"tx-{tx_id}",
        tags=tags or set(),
        notes=notes,
        category=category,
        currency=Currency(code="PLN", symbol="zł", decimals=2),
        source_account=source_account,
        destination_account=destination_account,
    )
    if merchant is not None:
        tx.merchant = merchant
    return tx


def test_get_candidate_documents_for_user_filters_uncategorized_and_internal_ops():
    bucketizer = AmountBucketizer()
    snapshot = TransactionSnapshot(
        transactions=[
            _transaction(
                tx_id=1,
                tx_type=TxType.WITHDRAWAL,
                amount=Decimal("12.00"),
                category=Category(id=10, name="Food"),
                merchant="Starbucks",
                notes="latte",
            ),
            _transaction(
                tx_id=2,
                tx_type=TxType.WITHDRAWAL,
                amount=Decimal("15.00"),
                category=None,
                merchant="Uncategorized",
            ),
            _transaction(
                tx_id=3,
                tx_type=TxType.TRANSFER,
                amount=Decimal("100.00"),
                category=Category(id=20, name="Transfer"),
            ),
            _transaction(
                tx_id=4,
                tx_type=TxType.DEPOSIT,
                amount=Decimal("200.00"),
                category=Category(id=30, name="Internal"),
                destination_account=AccountRef(
                    id=1,
                    name="internal",
                    type=AccountType.RECONCILIATION,
                ),
            ),
        ],
        metrics=FetchMetrics(
            total_transactions=4,
            fetching_duration_ms=1,
            invalid=0,
            multipart=0,
        ),
        fetched_at=datetime(2024, 1, 1),
    )
    provider = SnapshotCategorizationProvider(
        snapshot_service=_SnapshotService(snapshot),
        amount_bucketizer=bucketizer,
    )

    documents = asyncio.run(provider.get_candidate_documents_for_user("user-1"))

    assert [doc.transaction_id for doc in documents] == ["1"]
    assert documents[0].category_id == "10"
    assert documents[0].amount_bucket == bucketizer.bucket_for_amount(Decimal("12.00"))
    assert documents[0].source_type == "bank"


def test_get_query_for_transaction_id_builds_query_from_snapshot():
    bucketizer = AmountBucketizer()
    snapshot = TransactionSnapshot(
        transactions=[
            _transaction(
                tx_id=42,
                tx_type=TxType.WITHDRAWAL,
                amount=Decimal("12.34"),
                category=None,
                merchant="Starbucks",
                notes="latte",
                tags={TxTag.blik_done},
            ),
        ],
        metrics=FetchMetrics(
            total_transactions=1,
            fetching_duration_ms=1,
            invalid=0,
            multipart=0,
        ),
        fetched_at=datetime(2024, 1, 1),
    )
    provider = SnapshotCategorizationProvider(
        snapshot_service=_SnapshotService(snapshot),
        amount_bucketizer=bucketizer,
    )

    query = asyncio.run(provider.get_query_for_transaction_id("user-1", "42"))

    assert query.transaction_id == "42"
    assert query.title == "tx-42"
    assert query.merchant == "Starbucks"
    assert query.notes == "latte"
    assert query.amount == Decimal("12.34")
    assert query.amount_bucket == bucketizer.bucket_for_amount(Decimal("12.34"))
    assert query.source_type == "blik"
