import asyncio
from decimal import Decimal

from services.categorization.amount_bucketizer import AmountBucketizer
from services.categorization.models import TransactionCategorizationQuery
from services.categorization.preprocessor import CategorizationTextPreprocessor
from services.categorization.similarity_engine import (
    WeightedTransactionSimilarityEngine,
)
from services.domain.category_suggestion import TransactionCategorizationDocument


def _document(
    transaction_id: str,
    *,
    category_id: str,
    category_name: str,
    title: str,
    merchant: str | None,
    notes: str | None,
    amount: str,
    source_type: str = "bank",
) -> TransactionCategorizationDocument:
    bucketizer = AmountBucketizer()
    return TransactionCategorizationDocument(
        transaction_id=transaction_id,
        user_id="user-1",
        category_id=category_id,
        category_name=category_name,
        title=title,
        merchant=merchant,
        notes=notes,
        amount=Decimal(amount),
        amount_bucket=bucketizer.bucket_for_amount(Decimal(amount)),
        source_type=source_type,
    )


def test_similarity_engine_prefers_merchant_when_blik_query_has_merchant():
    engine = WeightedTransactionSimilarityEngine(
        preprocessor=CategorizationTextPreprocessor(),
        amount_bucketizer=AmountBucketizer(),
    )
    bucketizer = AmountBucketizer()
    query = TransactionCategorizationQuery(
        transaction_id=None,
        title="blik payment",
        merchant="Starbucks",
        notes=None,
        amount=Decimal("12.00"),
        amount_bucket=bucketizer.bucket_for_amount(Decimal("12.00")),
        source_type="blik",
    )
    candidates = [
        _document(
            "1",
            category_id="1",
            category_name="Coffee",
            title="random bank title",
            merchant="Starbucks",
            notes=None,
            amount="11.90",
            source_type="blik",
        ),
        _document(
            "2",
            category_id="2",
            category_name="Groceries",
            title="blik payment at coffee shop",
            merchant=None,
            notes=None,
            amount="12.10",
        ),
    ]

    matches = asyncio.run(engine.find_similar(query=query, candidates=candidates))

    assert [match.transaction_id for match in matches] == ["1"]
    assert matches[0].matched_by == "merchant"


def test_similarity_engine_prefers_notes_for_allegro_queries():
    bucketizer = AmountBucketizer()
    engine = WeightedTransactionSimilarityEngine(
        preprocessor=CategorizationTextPreprocessor(),
        amount_bucketizer=bucketizer,
        min_similarity_score=0.0,
    )
    query = TransactionCategorizationQuery(
        transaction_id=None,
        title="Allegro payment",
        merchant=None,
        notes="lego technic set",
        amount=Decimal("249.99"),
        amount_bucket=bucketizer.bucket_for_amount(Decimal("249.99")),
        source_type="allegro",
    )
    candidates = [
        _document(
            "1",
            category_id="1",
            category_name="Toys",
            title="some marketplace order",
            merchant=None,
            notes="lego technic set with motor",
            amount="250.00",
        ),
        _document(
            "2",
            category_id="2",
            category_name="Shopping",
            title="allegro payment",
            merchant=None,
            notes=None,
            amount="249.95",
        ),
    ]

    matches = asyncio.run(engine.find_similar(query=query, candidates=candidates))

    assert [match.transaction_id for match in matches[:2]] == ["1", "2"]
    assert matches[0].matched_by == "notes"
