from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from services.categorization.amount_bucketizer import AmountBucketizer
from services.categorization.models import TransactionCategorizationQuery
from services.domain.category_suggestion import TransactionCategorizationDocument
from services.domain.transaction import AccountType, Transaction, TxTag, TxType
from services.exceptions import TransactionNotFound
from services.snapshot.service import TransactionSnapshotService


class CategorizationSnapshotProvider:
    async def get_candidate_documents_for_user(
        self, user_id: str
    ) -> Sequence[TransactionCategorizationDocument]:
        raise NotImplementedError

    async def get_documents_for_user(
        self, user_id: str
    ) -> Sequence[TransactionCategorizationDocument]:
        return await self.get_candidate_documents_for_user(user_id)

    async def get_query_for_transaction_id(
        self, user_id: str, transaction_id: str
    ) -> TransactionCategorizationQuery:
        raise NotImplementedError


class SnapshotCategorizationProvider(CategorizationSnapshotProvider):
    def __init__(
        self,
        *,
        snapshot_service: TransactionSnapshotService,
        amount_bucketizer: AmountBucketizer,
    ) -> None:
        self._snapshot_service = snapshot_service
        self._amount_bucketizer = amount_bucketizer

    async def get_candidate_documents_for_user(
        self, user_id: str
    ) -> Sequence[TransactionCategorizationDocument]:
        # This is a single-user application. user_id stays on the contract for
        # future compatibility, but the current snapshot is not user-partitioned.
        snapshot = await self._snapshot_service.get_snapshot()
        documents: list[TransactionCategorizationDocument] = []
        for tx in snapshot.transactions:
            document = self._to_document(tx=tx, user_id=user_id)
            if document is not None:
                documents.append(document)
        return documents

    async def get_documents_for_user(
        self, user_id: str
    ) -> Sequence[TransactionCategorizationDocument]:
        return await self.get_candidate_documents_for_user(user_id)

    async def get_query_for_transaction_id(
        self, user_id: str, transaction_id: str
    ) -> TransactionCategorizationQuery:
        # This is a single-user application. user_id stays on the contract for
        # future compatibility, but the current snapshot is not user-partitioned.
        snapshot = await self._snapshot_service.get_snapshot()
        tx = self._find_transaction(
            snapshot.transactions, transaction_id=transaction_id
        )
        if tx is None:
            raise TransactionNotFound(f"Transaction id {transaction_id} not found")

        merchant = getattr(tx, "merchant", None)
        amount = self._transaction_amount(tx)
        return TransactionCategorizationQuery(
            transaction_id=str(tx.id),
            title=tx.description,
            merchant=merchant,
            notes=tx.notes,
            amount=amount,
            amount_bucket=self._amount_bucketizer.bucket_for_amount(amount),
            source_type=self._infer_source_type(tx=tx, merchant=merchant),
        )

    def _to_document(
        self, *, tx: Transaction, user_id: str
    ) -> TransactionCategorizationDocument | None:
        if tx.category is None:
            return None
        if self._is_internal_operation(tx):
            return None

        merchant = getattr(tx, "merchant", None)
        source_type = self._infer_source_type(tx=tx, merchant=merchant)
        amount = self._transaction_amount(tx)

        return TransactionCategorizationDocument(
            transaction_id=str(tx.id),
            user_id=user_id,
            category_id=str(tx.category.id),
            category_name=tx.category.name,
            title=tx.description,
            merchant=merchant,
            notes=tx.notes,
            amount=amount,
            amount_bucket=self._amount_bucketizer.bucket_for_amount(amount),
            source_type=source_type,
        )

    def _find_transaction(
        self, transactions: Sequence[Transaction], *, transaction_id: str
    ) -> Transaction | None:
        for tx in transactions:
            if str(tx.id) == transaction_id:
                return tx
        return None

    def _transaction_amount(self, tx: Transaction) -> Decimal:
        return tx.amount

    def _is_internal_operation(self, tx: Transaction) -> bool:
        if tx.type == TxType.TRANSFER:
            return True

        internal_account_types = {
            AccountType.INITIAL_BALANCE,
            AccountType.RECONCILIATION,
        }
        source_account = getattr(tx, "source_account", None)
        destination_account = getattr(tx, "destination_account", None)
        if source_account is not None and source_account.type in internal_account_types:
            return True
        return (
            destination_account is not None
            and destination_account.type in internal_account_types
        )

    def _infer_source_type(self, *, tx: Transaction, merchant: str | None) -> str:
        has_blik_marker = TxTag.blik_done in tx.tags
        has_allegro_marker = TxTag.allegro_done in tx.tags

        if has_blik_marker and merchant:
            return "blik"
        if has_allegro_marker and tx.notes:
            return "allegro"
        return "bank"
