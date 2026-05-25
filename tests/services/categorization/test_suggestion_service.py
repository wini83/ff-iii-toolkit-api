import asyncio
from decimal import Decimal

import pytest

from services.categorization.amount_bucketizer import AmountBucketizer
from services.categorization.models import (
    CategorizationQuery,
    TransactionCategorizationQuery,
)
from services.categorization.preprocessor import CategorizationTextPreprocessor
from services.categorization.service import (
    CategorySuggestionService,
    DefaultCategorySuggestionService,
)
from services.categorization.similarity_engine import (
    WeightedTransactionSimilarityEngine,
)
from services.domain.category_suggestion import (
    SimilarTransactionMatch,
    TransactionCategorizationDocument,
)


class _Provider:
    def __init__(self, documents):
        self.documents = documents

    async def get_candidate_documents_for_user(self, user_id: str):
        return self.documents

    async def get_query_for_transaction_id(self, user_id: str, transaction_id: str):
        return TransactionCategorizationQuery(
            transaction_id=transaction_id,
            title="coffee shop",
            merchant="Starbucks",
            notes=None,
            amount=Decimal("12.00"),
            amount_bucket=AmountBucketizer().bucket_for_amount(Decimal("12.00")),
            source_type="blik",
        )


class _Engine:
    def __init__(self, matches: list[SimilarTransactionMatch]):
        self.matches = matches
        self.calls: list[tuple[object, object, int]] = []

    async def find_similar(self, *, query, candidates, limit: int = 20):
        self.calls.append((query, candidates, limit))
        return self.matches


def test_suggestion_service_aggregates_scores_by_category():
    bucketizer = AmountBucketizer()
    engine = WeightedTransactionSimilarityEngine(
        preprocessor=CategorizationTextPreprocessor(),
        amount_bucketizer=bucketizer,
        min_similarity_score=0.0,
    )
    provider = _Provider(
        [
            TransactionCategorizationDocument(
                transaction_id="1",
                user_id="user-1",
                category_id="10",
                category_name="Food",
                title="coffee shop",
                merchant="Starbucks",
                notes=None,
                amount=Decimal("12.00"),
                amount_bucket=bucketizer.bucket_for_amount(Decimal("12.00")),
                source_type="blik",
            ),
            TransactionCategorizationDocument(
                transaction_id="2",
                user_id="user-1",
                category_id="10",
                category_name="Food",
                title="morning coffee",
                merchant=None,
                notes=None,
                amount=Decimal("11.50"),
                amount_bucket=bucketizer.bucket_for_amount(Decimal("11.50")),
                source_type="bank",
            ),
            TransactionCategorizationDocument(
                transaction_id="3",
                user_id="user-1",
                category_id="20",
                category_name="Groceries",
                title="supermarket",
                merchant=None,
                notes=None,
                amount=Decimal("13.00"),
                amount_bucket=bucketizer.bucket_for_amount(Decimal("13.00")),
                source_type="bank",
            ),
        ]
    )
    service = DefaultCategorySuggestionService(
        snapshot_provider=provider,
        similarity_engine=engine,
        amount_bucketizer=bucketizer,
    )
    query = CategorizationQuery(
        transaction_id=None,
        title="Starbucks latte",
        merchant="Starbucks",
        notes=None,
        amount=Decimal("12.10"),
        source_type="blik",
    )

    suggestions = asyncio.run(
        service.suggest_for_transaction(user_id="user-1", transaction=query)
    )

    assert [suggestion.category_id for suggestion in suggestions] == ["10", "20"]
    assert suggestions[0].reason == "similar merchant in previous transactions"
    assert suggestions[0].score >= suggestions[1].score


def test_suggestion_service_by_transaction_id_uses_snapshot_query():
    bucketizer = AmountBucketizer()
    engine = WeightedTransactionSimilarityEngine(
        preprocessor=CategorizationTextPreprocessor(),
        amount_bucketizer=bucketizer,
        min_similarity_score=0.0,
    )
    provider = _Provider(
        [
            TransactionCategorizationDocument(
                transaction_id="1",
                user_id="user-1",
                category_id="10",
                category_name="Food",
                title="coffee shop",
                merchant="Starbucks",
                notes=None,
                amount=Decimal("12.00"),
                amount_bucket=bucketizer.bucket_for_amount(Decimal("12.00")),
                source_type="blik",
            )
        ]
    )
    service = DefaultCategorySuggestionService(
        snapshot_provider=provider,
        similarity_engine=engine,
        amount_bucketizer=bucketizer,
    )

    suggestions = asyncio.run(
        service.suggest_for_transaction_id(user_id="user-1", transaction_id="99")
    )

    assert [suggestion.category_id for suggestion in suggestions] == ["10"]


def test_suggestion_service_returns_empty_when_no_matches():
    bucketizer = AmountBucketizer()
    engine = _Engine(matches=[])
    provider = _Provider([])
    service = DefaultCategorySuggestionService(
        snapshot_provider=provider,
        similarity_engine=engine,
        amount_bucketizer=bucketizer,
    )

    suggestions = asyncio.run(
        service.suggest_for_transaction_id(user_id="user-1", transaction_id="99")
    )

    assert suggestions == []
    assert engine.calls[0][2] == 20


def test_suggestion_service_maps_reason_from_best_match():
    bucketizer = AmountBucketizer()
    engine = _Engine(
        matches=[
            SimilarTransactionMatch(
                transaction_id="1",
                category_id="10",
                category_name="Food",
                similarity_score=0.4,
                matched_by="notes",
            ),
            SimilarTransactionMatch(
                transaction_id="2",
                category_id="10",
                category_name="Food",
                similarity_score=0.7,
                matched_by="title",
            ),
            SimilarTransactionMatch(
                transaction_id="3",
                category_id="20",
                category_name="Transport",
                similarity_score=0.6,
                matched_by="amount",
            ),
        ]
    )
    provider = _Provider([])
    service = DefaultCategorySuggestionService(
        snapshot_provider=provider,
        similarity_engine=engine,
        amount_bucketizer=bucketizer,
    )

    suggestions = asyncio.run(
        service.suggest_for_transaction_id(user_id="user-1", transaction_id="99")
    )

    assert [suggestion.category_id for suggestion in suggestions] == ["10", "20"]
    assert suggestions[0].reason == "similar title pattern in previous transactions"
    assert suggestions[1].reason == "similar previous transactions"


def test_suggestion_service_maps_notes_reason_when_best_match_comes_from_notes():
    bucketizer = AmountBucketizer()
    engine = _Engine(
        matches=[
            SimilarTransactionMatch(
                transaction_id="1",
                category_id="10",
                category_name="Food",
                similarity_score=0.8,
                matched_by="notes",
            ),
            SimilarTransactionMatch(
                transaction_id="2",
                category_id="20",
                category_name="Transport",
                similarity_score=0.6,
                matched_by="amount",
            ),
        ]
    )
    service = DefaultCategorySuggestionService(
        snapshot_provider=_Provider([]),
        similarity_engine=engine,
        amount_bucketizer=bucketizer,
    )

    suggestions = asyncio.run(
        service.suggest_for_transaction_id(user_id="user-1", transaction_id="99")
    )

    assert suggestions[0].reason == "similar notes in previous transactions"


def test_suggestion_service_base_contract_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        asyncio.run(
            CategorySuggestionService.suggest_for_transaction(
                CategorySuggestionService(),
                user_id="user-1",
                transaction=CategorizationQuery(
                    transaction_id=None,
                    title="x",
                    merchant=None,
                    notes=None,
                    amount=Decimal("1.00"),
                    source_type="bank",
                ),
            )
        )
    with pytest.raises(NotImplementedError):
        asyncio.run(
            CategorySuggestionService.suggest_for_transaction_id(
                CategorySuggestionService(),
                user_id="user-1",
                transaction_id="1",
            )
        )
