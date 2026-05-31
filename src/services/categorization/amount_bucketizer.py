from __future__ import annotations

from decimal import Decimal


class AmountBucketizer:
    _upper_bounds: tuple[Decimal, ...] = (
        Decimal("10"),
        Decimal("25"),
        Decimal("50"),
        Decimal("100"),
        Decimal("250"),
        Decimal("500"),
        Decimal("Infinity"),
    )
    _labels: tuple[str, ...] = (
        "0-10",
        "10-25",
        "25-50",
        "50-100",
        "100-250",
        "250-500",
        "500+",
    )

    def bucket_for_amount(self, amount: Decimal) -> str:
        absolute_amount = abs(amount)
        for upper_bound, label in zip(self._upper_bounds, self._labels, strict=True):
            if absolute_amount <= upper_bound:
                return label
        return self._labels[-1]

    def bucket_similarity(self, left_amount: Decimal, right_amount: Decimal) -> float:
        left_index = self.bucket_index(self.bucket_for_amount(left_amount))
        right_index = self.bucket_index(self.bucket_for_amount(right_amount))
        distance = abs(left_index - right_index)
        if distance == 0:
            return 1.0
        if distance == 1:
            return 0.65
        if distance == 2:
            return 0.35
        return 0.0

    def bucket_index(self, bucket: str) -> int:
        try:
            return self._labels.index(bucket)
        except ValueError:
            return len(self._labels) - 1
