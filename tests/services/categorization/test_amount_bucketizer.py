from decimal import Decimal

from services.categorization.amount_bucketizer import AmountBucketizer


def test_amount_bucketizer_maps_amounts_to_expected_buckets():
    bucketizer = AmountBucketizer()

    assert bucketizer.bucket_for_amount(Decimal("-2.50")) == "0-10"
    assert bucketizer.bucket_for_amount(Decimal("10.00")) == "0-10"
    assert bucketizer.bucket_for_amount(Decimal("10.01")) == "10-25"
    assert bucketizer.bucket_for_amount(Decimal("25.00")) == "10-25"
    assert bucketizer.bucket_for_amount(Decimal("25.01")) == "25-50"
    assert bucketizer.bucket_for_amount(Decimal("50.00")) == "25-50"
    assert bucketizer.bucket_for_amount(Decimal("50.01")) == "50-100"
    assert bucketizer.bucket_for_amount(Decimal("100.00")) == "50-100"
    assert bucketizer.bucket_for_amount(Decimal("250.00")) == "100-250"
    assert bucketizer.bucket_for_amount(Decimal("500.00")) == "250-500"
    assert bucketizer.bucket_for_amount(Decimal("999.00")) == "500+"


def test_amount_bucketizer_similarity_and_index_helpers():
    bucketizer = AmountBucketizer()

    assert bucketizer.bucket_similarity(Decimal("10.00"), Decimal("10.00")) == 1.0
    assert bucketizer.bucket_similarity(Decimal("10.00"), Decimal("20.00")) == 0.65
    assert bucketizer.bucket_similarity(Decimal("10.00"), Decimal("40.00")) == 0.35
    assert bucketizer.bucket_similarity(Decimal("10.00"), Decimal("1000.00")) == 0.0
    assert bucketizer.bucket_index("not-a-bucket") == 6


def test_amount_bucketizer_fallback_branch_is_reachable():
    bucketizer = AmountBucketizer()
    bucketizer._upper_bounds = ()
    bucketizer._labels = ()

    try:
        bucketizer.bucket_for_amount(Decimal("1.00"))
    except IndexError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("expected IndexError")
