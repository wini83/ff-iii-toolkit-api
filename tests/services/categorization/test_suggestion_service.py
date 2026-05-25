import asyncio
from decimal import Decimal

from services.categorization.amount_bucketizer import AmountBucketizer
from services.categorization.models import (
    CategorizationQuery,
    TransactionCategorizationQuery,
)
from services.categorization.preprocessor import CategorizationTextPreprocessor
from services.categorization.service import DefaultCategorySuggestionService
from services.categorization.similarity_engine import (
    WeightedTransactionSimilarityEngine,
)
from services.domain.category_suggestion import TransactionCategorizationDocument


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
