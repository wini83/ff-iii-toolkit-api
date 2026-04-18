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
from services.allegro.payloads import GetOrdersResponse, OrderPayload


def _order_item(
    *,
    order_id: str = "order-123",
    group_id: str = "group-123",
    purchase_id: str = "purchase-123",
    payment_id: str = "pay-123",
    quantity: int = 1,
    delivery_cost: str = "10.49",
) -> dict:
    return {
        "id": order_id,
        "purchaseId": purchase_id,
        "seller": {"login": "seller"},
        "offers": [
            {
                "id": "offer-1",
                "title": "Sample Product",
                "unitPrice": {"amount": "12.34", "currency": "PLN"},
                "friendlyUrl": "https://example.com",
                "quantity": quantity,
                "imageUrl": "https://example.com/image.jpg",
            }
        ],
        "delivery": {
            "cost": {"amount": delivery_cost, "currency": "PLN"},
            "name": "Allegro One Box, DPD",
            "deliveredBy": "Delivery by Allegro One",
            "methodId": "0b257488-c85d-4507-b967-9b45ffbfa2e8",
            "status": "DELIVERED",
        },
        "createDate": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
        "orderDate": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
        "status": {
            "primary": {"status": "DELIVERED", "action": "RATE_SELLER"},
            "traits": ["IS_SURCHARGE_ALLOWED"],
            "actions": [{"type": "RATE_SELLER", "enabled": True}],
        },
        "totalCost": {"amount": "22.83"},
        "payment": {
            "id": payment_id,
            "provider": "PAYU",
            "amount": {"amount": "22.83", "currency": "PLN"},
            "method": "BLIK",
            "methodId": "OCP-ap",
            "status": "COMPLETED",
            "date": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
        },
    }


def test_order_and_payment_metadata_happy_path():
    order = Order.from_payload("group-1", OrderPayload.model_validate(_order_item()))
    payment = Payment(payment_id=order.payment_id, orders=[order])

    assert order.order_id == "order-123"
    assert order.group_id == "group-1"
    assert order.purchase_id == "purchase-123"
    assert order.currency_code == "PLN"
    assert order.payment_provider == "PAYU"
    assert order.payment_method == "BLIK"
    assert order.items_total == Decimal("12.34")
    assert order.delivery_total == Decimal("10.49")
    assert order.known_total == Decimal("22.83")
    assert order.balance_difference == Decimal("0.00")
    assert order.is_known_total_balanced is True

    assert payment.short_id == short_id(order.payment_id)
    assert payment.currency_code == "PLN"
    assert payment.payment_provider == "PAYU"
    assert payment.payment_method == "BLIK"
    assert payment.items_total == Decimal("12.34")
    assert payment.delivery_total == Decimal("10.49")
    assert payment.known_total == Decimal("22.83")
    assert payment.balance_difference == Decimal("0.00")
    assert payment.is_known_total_balanced is True
    assert "Payment metadata: PAYU/BLIK" in str(payment)


def test_get_orders_result_builds_orders_and_groups_payments():
    payload = {
        "orderGroups": [
            {
                "groupId": "g1",
                "myorders": [
                    _order_item(
                        order_id="order-a",
                        purchase_id="purchase-a",
                        payment_id="same-pay",
                    ),
                    _order_item(
                        order_id="order-b",
                        purchase_id="purchase-a",
                        payment_id="same-pay",
                    ),
                ],
            }
        ]
    }

    result = GetOrdersResult.from_dict(payload)

    assert len(result.as_list()) == 2
    assert len(result.payments) == 1
    assert all(order.group_id == "g1" for order in result.as_list())
    assert {order.order_id for order in result.as_list()} == {"order-a", "order-b"}
    assert all(order.purchase_id == "purchase-a" for order in result.as_list())


def test_get_orders_response_parses_nested_monetary_and_datetime_values():
    response = GetOrdersResponse.model_validate(
        {
            "orderGroups": [
                {
                    "groupId": "g1",
                    "myorders": [_order_item(payment_id="same-pay")],
                }
            ]
        }
    )

    order = response.order_groups[0].orders[0]

    assert isinstance(order.order_date, datetime)
    assert order.payment.amount.amount == Decimal("22.83")
    assert order.payment.amount.currency == "PLN"
    assert order.total_cost.amount == Decimal("22.83")
    assert order.delivery is not None
    assert order.delivery.cost is not None
    assert order.delivery.cost.amount == Decimal("10.49")


def test_order_rendering_and_date_parsing_with_z_suffix():
    order = Order.from_payload("group-1", OrderPayload.model_validate(_order_item()))

    assert order.order_date.tzinfo is not None
    assert order.create_date.tzinfo is not None
    assert order.payment_date is not None
    assert len(order.list_offers()) == 1
    assert "Sample Product" in order.format_offers()


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
    first = Order.from_payload(
        "group-1",
        OrderPayload.model_validate(
            _order_item(order_id="order-1", payment_id="pay-99")
        ),
    )
    second = Order.from_payload(
        "group-1",
        OrderPayload.model_validate(
            _order_item(order_id="order-2", payment_id="pay-99")
        ),
    )
    payment = Payment.from_orders([first, second])[0]

    details = payment.list_details()

    assert len(details) == 2
    assert payment.sum_total_cost == Decimal("45.66")
    assert "Payment " in repr(payment)
