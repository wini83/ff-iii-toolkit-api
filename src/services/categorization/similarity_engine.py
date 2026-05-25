from __future__ import annotations

from collections.abc import Sequence
from difflib import SequenceMatcher

from services.categorization.amount_bucketizer import AmountBucketizer
from services.categorization.models import TransactionCategorizationQuery
from services.categorization.preprocessor import CategorizationTextPreprocessor
from services.domain.category_suggestion import (
    SimilarTransactionMatch,
    TransactionCategorizationDocument,
)


class WeightedTransactionSimilarityEngine:
    def __init__(
        self,
        *,
        preprocessor: CategorizationTextPreprocessor,
        amount_bucketizer: AmountBucketizer,
        min_similarity_score: float = 0.35,
    ) -> None:
        self._preprocessor = preprocessor
        self._amount_bucketizer = amount_bucketizer
        self._min_similarity_score = min_similarity_score

    async def find_similar(
        self,
        query: TransactionCategorizationQuery,
        candidates: Sequence[TransactionCategorizationDocument],
        limit: int = 20,
    ) -> Sequence[SimilarTransactionMatch]:
        matches: list[SimilarTransactionMatch] = []
        for candidate in candidates:
            if (
                query.transaction_id is not None
                and candidate.transaction_id == query.transaction_id
            ):
                continue

            weighted_score, matched_by = self._score_pair(
                query=query,
                candidate=candidate,
            )
            if weighted_score < self._min_similarity_score:
                continue

            matches.append(
                SimilarTransactionMatch(
                    transaction_id=candidate.transaction_id,
                    category_id=candidate.category_id,
                    category_name=candidate.category_name,
                    similarity_score=round(weighted_score, 4),
                    matched_by=matched_by,
                )
            )

        matches.sort(
            key=lambda item: (
                -item.similarity_score,
                item.category_name.lower(),
                item.transaction_id,
            ),
        )
        return matches[:limit]

    def _score_pair(
        self,
        *,
        query: TransactionCategorizationQuery,
        candidate: TransactionCategorizationDocument,
    ) -> tuple[float, str]:
        weights = self._select_weights(query=query)
        title_score = self._text_similarity(query.title, candidate.title)
        merchant_score = self._text_similarity(query.merchant, candidate.merchant)
        notes_score = self._text_similarity(query.notes, candidate.notes)
        amount_score = self._amount_similarity(
            query_bucket=query.amount_bucket,
            candidate_bucket=candidate.amount_bucket,
        )

        contributions = {
            "title": weights["title"] * title_score,
            "merchant": weights["merchant"] * merchant_score,
            "notes": weights["notes"] * notes_score,
            "amount": weights["amount"] * amount_score,
        }
        score = sum(contributions.values())
        matched_by = max(
            contributions.items(),
            key=lambda item: (item[1], self._field_priority(item[0])),
        )[0]
        return score, matched_by

    def _amount_similarity(
        self,
        *,
        query_bucket: str,
        candidate_bucket: str,
    ) -> float:
        if not query_bucket or not candidate_bucket:
            return 0.0

        left_index = self._amount_bucketizer.bucket_index(query_bucket)
        right_index = self._amount_bucketizer.bucket_index(candidate_bucket)
        distance = abs(left_index - right_index)
        if distance == 0:
            return 1.0
        if distance == 1:
            return 0.65
        if distance == 2:
            return 0.35
        return 0.0

    def _select_weights(
        self, *, query: TransactionCategorizationQuery
    ) -> dict[str, float]:
        source_type = query.source_type.strip().lower()
        merchant_present = bool(self._preprocessor.normalize(query.merchant))
        notes_present = bool(self._preprocessor.normalize(query.notes))

        if source_type == "blik" and merchant_present:
            return {
                "title": 0.25,
                "merchant": 0.50,
                "notes": 0.15,
                "amount": 0.10,
            }
        if source_type == "allegro" and notes_present:
            return {
                "title": 0.20,
                "merchant": 0.10,
                "notes": 0.55,
                "amount": 0.15,
            }
        if merchant_present:
            return {
                "title": 0.35,
                "merchant": 0.40,
                "notes": 0.15,
                "amount": 0.10,
            }
        if notes_present:
            return {
                "title": 0.45,
                "merchant": 0.00,
                "notes": 0.40,
                "amount": 0.15,
            }
        return {
            "title": 0.75,
            "merchant": 0.00,
            "notes": 0.10,
            "amount": 0.15,
        }

    def _text_similarity(self, left: str | None, right: str | None) -> float:
        left_normalized = self._preprocessor.normalize(left)
        right_normalized = self._preprocessor.normalize(right)
        if not left_normalized or not right_normalized:
            return 0.0

        ratio = SequenceMatcher(None, left_normalized, right_normalized).ratio()
        left_tokens = self._preprocessor.tokens(left)
        right_tokens = self._preprocessor.tokens(right)
        if not left_tokens or not right_tokens:
            return ratio

        overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
        return max(ratio, overlap)

    def _field_priority(self, field_name: str) -> int:
        priorities = {
            "merchant": 3,
            "notes": 2,
            "title": 1,
            "amount": 0,
        }
        return priorities[field_name]
