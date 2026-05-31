from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from services.categorization.amount_bucketizer import AmountBucketizer
from services.categorization.models import (
    CategorizationQuery,
    TransactionCategorizationQuery,
)
from services.categorization.similarity_engine import (
    WeightedTransactionSimilarityEngine,
)
from services.categorization.snapshot_provider import CategorizationSnapshotProvider
from services.domain.category_suggestion import (
    CategorySuggestion,
    SimilarTransactionMatch,
)


class CategorySuggestionService:
    async def suggest_for_transaction(
        self,
        *,
        user_id: str,
        transaction: CategorizationQuery,
        limit: int = 3,
    ) -> Sequence[CategorySuggestion]:
        raise NotImplementedError

    async def suggest_for_transaction_id(
        self,
        *,
        user_id: str,
        transaction_id: str,
        limit: int = 3,
    ) -> Sequence[CategorySuggestion]:
        raise NotImplementedError


class DefaultCategorySuggestionService(CategorySuggestionService):
    def __init__(
        self,
        *,
        snapshot_provider: CategorizationSnapshotProvider,
        similarity_engine: WeightedTransactionSimilarityEngine,
        amount_bucketizer: AmountBucketizer,
    ) -> None:
        self._snapshot_provider = snapshot_provider
        self._similarity_engine = similarity_engine
        self._amount_bucketizer = amount_bucketizer

    async def suggest_for_transaction(
        self,
        *,
        user_id: str,
        transaction: CategorizationQuery,
        limit: int = 3,
    ) -> Sequence[CategorySuggestion]:
        query = TransactionCategorizationQuery(
            transaction_id=transaction.transaction_id,
            title=transaction.title,
            merchant=transaction.merchant,
            notes=transaction.notes,
            amount=transaction.amount,
            amount_bucket=self._amount_bucketizer.bucket_for_amount(transaction.amount),
            source_type=transaction.source_type,
        )
        candidates = await self._snapshot_provider.get_candidate_documents_for_user(
            user_id
        )
        matches = await self._similarity_engine.find_similar(
            query=query,
            candidates=candidates,
            limit=20,
        )
        return self._aggregate(matches=matches, limit=limit)

    async def suggest_for_transaction_id(
        self,
        *,
        user_id: str,
        transaction_id: str,
        limit: int = 3,
    ) -> Sequence[CategorySuggestion]:
        query = await self._snapshot_provider.get_query_for_transaction_id(
            user_id=user_id,
            transaction_id=transaction_id,
        )
        candidates = await self._snapshot_provider.get_candidate_documents_for_user(
            user_id
        )
        matches = await self._similarity_engine.find_similar(
            query=query,
            candidates=candidates,
            limit=20,
        )
        return self._aggregate(matches=matches, limit=limit)

    def _aggregate(
        self,
        *,
        matches: Sequence[SimilarTransactionMatch],
        limit: int,
    ) -> Sequence[CategorySuggestion]:
        if not matches:
            return []

        @dataclass(slots=True)
        class _Aggregate:
            category_name: str
            score: float
            best_match: SimilarTransactionMatch

        aggregated: dict[str, _Aggregate] = {}
        for match in matches:
            bucket = aggregated.setdefault(
                match.category_id,
                _Aggregate(
                    category_name=match.category_name,
                    score=0.0,
                    best_match=match,
                ),
            )
            bucket.score = 1.0 - ((1.0 - bucket.score) * (1.0 - match.similarity_score))
            if match.similarity_score > bucket.best_match.similarity_score:
                bucket.best_match = match

        suggestions = [
            CategorySuggestion(
                category_id=category_id,
                category_name=data.category_name,
                score=round(data.score, 4),
                reason=self._reason_from_match(data.best_match),
            )
            for category_id, data in aggregated.items()
        ]
        suggestions.sort(
            key=lambda suggestion: (
                -suggestion.score,
                suggestion.category_name.lower(),
                suggestion.category_id,
            ),
        )
        return suggestions[:limit]

    def _reason_from_match(self, match) -> str:
        if match.matched_by == "merchant":
            return "similar merchant in previous transactions"
        if match.matched_by == "notes":
            return "similar notes in previous transactions"
        if match.matched_by == "title":
            return "similar title pattern in previous transactions"
        return "similar previous transactions"
