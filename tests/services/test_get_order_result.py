from datetime import UTC, datetime
from decimal import Decimal

import pytest

from services.allegro.get_order_result import (
    GetOrdersResult,
    Offer,
    Order,
    Payment,
    short_id,
)


def _order_item(*, payment_id: str = "pay-123") -> dict:
    return {
        "seller": {"login": "seller"},
        "offers": [
            {
                "id": "offer-1",
                "title": "Sample Product",
                "unitPrice": {"amount": "12.34", "currency": "PLN"},
                "friendlyUrl": "https://example.com",
                "quantity": 1,
                "imageUrl": "https://example.com/image.jpg",
            }
        ],
        "orderDate": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
        "totalCost": {"amount": "12.34"},
        "payment": {
            "amount": {"amount": "12.34", "currency": "PLN"},
            "provider": "PAYU",
            "method": "BLIK",
            "id": payment_id,
        },
    }


def test_order_and_payment_metadata_happy_path():
    order = Order("order-1", _order_item())
    payment = Payment(payment_id=order.payment_id, orders=[order])

    assert order.currency_code == "PLN"
    assert order.payment_provider == "PAYU"
    assert order.payment_method == "BLIK"

    assert payment.short_id == short_id(order.payment_id)
    assert payment.currency_code == "PLN"
    assert payment.payment_provider == "PAYU"
    assert payment.payment_method == "BLIK"
    assert "Payment metadata: PAYU/BLIK" in str(payment)


def test_get_orders_result_builds_orders_and_groups_payments():
    payload = {
        "orderGroups": [
            {"groupId": "g1", "myorders": [_order_item(payment_id="same-pay")]},
            {"groupId": "g2", "myorders": [_order_item(payment_id="same-pay")]},
        ]
    }

    result = GetOrdersResult(payload)

    assert len(result.as_list()) == 2
    assert len(result.payments) == 1


def test_order_rendering_and_date_parsing_with_z_suffix():
    order = Order("order-1", _order_item())

    assert order.order_date.tzinfo is not None
    assert len(order.list_offers()) == 1
    assert "Sample Product" in order.print_offers()


def test_payment_metadata_properties_raise_for_empty_orders():
    payment = Payment(payment_id="pay-1", orders=[])

    assert payment.amount == Decimal("0")

    with pytest.raises(ValueError, match="No orders in payment"):
        _ = payment.currency_code

    with pytest.raises(ValueError, match="No orders in payment"):
        _ = payment.payment_provider

    with pytest.raises(ValueError, match="No orders in payment"):
        _ = payment.payment_method


def test_offer_get_simplified_title_edge_case_with_empty_title():
    offer = Offer(
        offer_id="o1",
        title="",
        unit_price=Decimal("1.00"),
        price_currency="PLN",
        friendly_url="u",
        quantity=1,
        image_url="i",
    )

    assert offer.get_simplified_title() == ""


def test_payment_list_details_sum_and_repr():
    first = Order("order-1", _order_item(payment_id="pay-99"))
    second = Order("order-2", _order_item(payment_id="pay-99"))
    payment = Payment.from_orders([first, second])[0]

    details = payment.list_details()

    assert len(details) == 2
    assert payment.sum_total_cost == Decimal("24.68")
    assert "Payment " in repr(payment)
