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


def test_similarity_engine_covers_default_weights_threshold_and_limit():
    bucketizer = AmountBucketizer()
    engine = WeightedTransactionSimilarityEngine(
        preprocessor=CategorizationTextPreprocessor(),
        amount_bucketizer=bucketizer,
        min_similarity_score=0.0,
    )
    query = TransactionCategorizationQuery(
        transaction_id="10",
        title="grocery store",
        merchant="",
        notes="",
        amount=Decimal("10.00"),
        amount_bucket=bucketizer.bucket_for_amount(Decimal("10.00")),
        source_type="bank",
    )
    candidates = [
        _document(
            "10",
            category_id="1",
            category_name="Food",
            title="grocery store",
            merchant=None,
            notes=None,
            amount="10.00",
        ),
        _document(
            "11",
            category_id="2",
            category_name="Bills",
            title="grocery store nearby",
            merchant=None,
            notes=None,
            amount="10.01",
        ),
    ]

    matches = asyncio.run(engine.find_similar(query=query, candidates=candidates))

    assert [match.transaction_id for match in matches] == ["11"]
    assert matches[0].matched_by == "title"


def test_similarity_engine_covers_merchant_and_notes_weight_branches():
    bucketizer = AmountBucketizer()
    engine = WeightedTransactionSimilarityEngine(
        preprocessor=CategorizationTextPreprocessor(),
        amount_bucketizer=bucketizer,
        min_similarity_score=0.0,
    )

    merchant_query = TransactionCategorizationQuery(
        transaction_id=None,
        title="card payment",
        merchant="CoffeeShop",
        notes=None,
        amount=Decimal("12.00"),
        amount_bucket=bucketizer.bucket_for_amount(Decimal("12.00")),
        source_type="bank",
    )
    notes_query = TransactionCategorizationQuery(
        transaction_id=None,
        title="marketplace order",
        merchant=None,
        notes="lego set",
        amount=Decimal("249.99"),
        amount_bucket=bucketizer.bucket_for_amount(Decimal("249.99")),
        source_type="bank",
    )

    merchant_matches = asyncio.run(
        engine.find_similar(
            query=merchant_query,
            candidates=[
                _document(
                    "1",
                    category_id="1",
                    category_name="Coffee",
                    title="random title",
                    merchant="CoffeeShop",
                    notes=None,
                    amount="12.00",
                )
            ],
        )
    )
    notes_matches = asyncio.run(
        engine.find_similar(
            query=notes_query,
            candidates=[
                _document(
                    "2",
                    category_id="2",
                    category_name="Toys",
                    title="random title",
                    merchant=None,
                    notes="lego set with motor",
                    amount="250.00",
                )
            ],
        )
    )

    assert merchant_matches[0].matched_by == "merchant"
    assert notes_matches[0].matched_by == "notes"


def test_similarity_engine_skips_same_transaction_id():
    bucketizer = AmountBucketizer()
    engine = WeightedTransactionSimilarityEngine(
        preprocessor=CategorizationTextPreprocessor(),
        amount_bucketizer=bucketizer,
        min_similarity_score=0.0,
    )
    query = TransactionCategorizationQuery(
        transaction_id="1",
        title="coffee",
        merchant="Starbucks",
        notes=None,
        amount=Decimal("12.00"),
        amount_bucket=bucketizer.bucket_for_amount(Decimal("12.00")),
        source_type="blik",
    )

    matches = asyncio.run(
        engine.find_similar(
            query=query,
            candidates=[
                _document(
                    "1",
                    category_id="1",
                    category_name="Coffee",
                    title="coffee",
                    merchant="Starbucks",
                    notes=None,
                    amount="12.00",
                )
            ],
        )
    )

    assert matches == []


def test_similarity_engine_amount_similarity_branches():
    engine = WeightedTransactionSimilarityEngine(
        preprocessor=CategorizationTextPreprocessor(),
        amount_bucketizer=AmountBucketizer(),
    )

    assert (
        engine._amount_similarity(
            query_bucket="0-10",
            candidate_bucket="0-10",
        )
        == 1.0
    )
    assert (
        engine._amount_similarity(
            query_bucket="0-10",
            candidate_bucket="10-25",
        )
        == 0.65
    )
    assert (
        engine._amount_similarity(
            query_bucket="0-10",
            candidate_bucket="25-50",
        )
        == 0.35
    )
    assert (
        engine._amount_similarity(
            query_bucket="0-10",
            candidate_bucket="500+",
        )
        == 0.0
    )
    assert engine._amount_similarity(query_bucket="", candidate_bucket="0-10") == 0.0
    assert engine._text_similarity(None, "abc") == 0.0
    assert engine._text_similarity("abc", None) == 0.0


def test_similarity_engine_text_similarity_falls_back_to_ratio_without_tokens():
    class _Preprocessor:
        def normalize(self, value):
            return "abc" if value else ""

        def tokens(self, value):
            return set()

    engine = WeightedTransactionSimilarityEngine(
        preprocessor=_Preprocessor(),
        amount_bucketizer=AmountBucketizer(),
    )

    assert engine._text_similarity("left", "right") > 0.0
