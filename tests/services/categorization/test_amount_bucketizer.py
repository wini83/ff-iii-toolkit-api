from decimal import Decimal

from services.categorization.amount_bucketizer import AmountBucketizer


def test_amount_bucketizer_maps_amounts_to_expected_buckets():
    bucketizer = AmountBucketizer()

    assert bucketizer.bucket_for_amount(Decimal("2.50")) == "0-10"
    assert bucketizer.bucket_for_amount(Decimal("17.00")) == "10-25"
    assert bucketizer.bucket_for_amount(Decimal("999.00")) == "500+"
