from datetime import UTC, datetime
from decimal import Decimal

import pytest

from services.domain.allegro import AllegroOrderPayment, AllegroPageRequest
from services.domain.transaction import TxTag


class DummyPayment:
    amount = Decimal("12.34")
    date = datetime(2025, 2, 3, 12, 0, tzinfo=UTC)
    short_id = "SHORT-1"
    payment_method = "CARD"
    payment_provider = "VISA"
    payment_id = "PAYMENT-1"
    is_balanced = True

    def list_details(self):
        return [
            "Order: #123 x2 (12.34 PLN)",
            "Delivery: Allegro One Box (10.49 PLN)",
            "Type: full",
        ]


def test_from_allegro_payment_builds_details_and_metadata():
    result = AllegroOrderPayment.from_allegro_payment(DummyPayment(), "buyer_login")

    assert result.amount == Decimal("12.34")
    assert result.date.isoformat() == "2025-02-03"
    assert result.tag_done == TxTag.allegro_done
    assert result.allegro_login == "buyer_login"
    assert result.external_short_id == "SHORT-1"
    assert result.external_id == "PAYMENT-1"
    assert result.details[0] == "Buyer: buyer_login"
    assert result.details[1] == "Payment ID: SHORT-1"
    assert result.details[2] == "Order: #123 x2 (12.34 PLN)"
    assert result.details[3] == "Delivery: Allegro One Box (10.49 PLN)"
    assert result.details[-1] == "Payment metadata: CARD/VISA"


@pytest.mark.parametrize(
    ("limit", "offset", "error"),
    [
        (0, 0, "limit must be greater than 0"),
        (-1, 0, "limit must be greater than 0"),
        (1, -1, "offset must be greater than or equal to 0"),
    ],
)
def test_page_request_validates_limit_and_offset(limit, offset, error):
    with pytest.raises(ValueError, match=error):
        AllegroPageRequest(limit=limit, offset=offset)
