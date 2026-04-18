from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

import services.allegro.get_order_result as get_order_result_module
from services.allegro.get_order_result import (
    GetOrdersResult,
    Offer,
    Order,
    Payment,
    short_id,
)
from services.allegro.payloads import GetOrdersResponse, OrderPayload

_DEFAULT_DELIVERY = object()


def _order_item(
    *,
    order_id: str = "order-123",
    group_id: str = "group-123",
    purchase_id: str = "purchase-123",
    payment_id: str = "pay-123",
    quantity: int = 1,
    title: str = "Sample Product",
    create_date: datetime | None = datetime(2024, 1, 1, tzinfo=UTC),
    order_date: datetime = datetime(2024, 1, 1, tzinfo=UTC),
    payment_date: datetime | None = datetime(2024, 1, 1, tzinfo=UTC),
    delivery: Any = _DEFAULT_DELIVERY,
    total_cost_amount: str = "22.83",
    payment_amount: str = "22.83",
    payment_currency: str = "PLN",
    payment_provider: str = "PAYU",
    payment_method: str = "BLIK",
    delivery_cost: str = "10.49",
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": order_id,
        "purchaseId": purchase_id,
        "seller": {"login": "seller"},
        "offers": [
            {
                "id": "offer-1",
                "title": title,
                "unitPrice": {"amount": "12.34", "currency": "PLN"},
                "friendlyUrl": "https://example.com",
                "quantity": quantity,
                "imageUrl": "https://example.com/image.jpg",
            }
        ],
        "orderDate": order_date.isoformat(),
        "status": {
            "primary": {"status": "DELIVERED", "action": "RATE_SELLER"},
            "traits": ["IS_SURCHARGE_ALLOWED"],
            "actions": [{"type": "RATE_SELLER", "enabled": True}],
        },
        "totalCost": {"amount": total_cost_amount},
        "payment": {
            "id": payment_id,
            "provider": payment_provider,
            "amount": {"amount": payment_amount, "currency": payment_currency},
            "method": payment_method,
            "methodId": "OCP-ap",
            "status": "COMPLETED",
            "date": payment_date.isoformat() if payment_date is not None else None,
        },
    }

    if create_date is not None:
        item["createDate"] = create_date.isoformat()
    if delivery is _DEFAULT_DELIVERY:
        item["delivery"] = {
            "cost": {"amount": delivery_cost, "currency": "PLN"},
            "name": "Allegro One Box, DPD",
            "deliveredBy": "Delivery by Allegro One",
            "methodId": "0b257488-c85d-4507-b967-9b45ffbfa2e8",
            "status": "DELIVERED",
        }
    else:
        item["delivery"] = delivery

    return item


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
    assert order.list_offers() == ["Sample Product x1 (12.34 PLN)"]
    assert payment.list_details()[0] == "Sample Product x1 (12.34 PLN)"
    assert payment.list_details()[1] == "Delivery: Allegro One Box, DPD (10.49 PLN)"
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
    assert order.list_offers()[0] == "Sample Product x1 (12.34 PLN)"
    assert "Sample Product x1" in order.format_offers()


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

    assert len(details) == 4
    assert payment.sum_total_cost == Decimal("45.66")
    assert details[0] == "Sample Product x1 (12.34 PLN)"
    assert details[1] == "Delivery: Allegro One Box, DPD (10.49 PLN)"
    assert details[2] == "Sample Product x1 (12.34 PLN)"
    assert details[3] == "Delivery: Allegro One Box, DPD (10.49 PLN)"
    assert "Payment " in repr(payment)


def test_order_and_payment_date_aliases_and_naive_datetime_handling():
    order = Order.from_payload(
        "group-1",
        OrderPayload.model_validate(
            _order_item(
                create_date=datetime(2024, 1, 1, 11, 0),
                order_date=datetime(2024, 1, 1, 12, 0),
                payment_date=datetime(2024, 1, 1, 13, 0),
                delivery={
                    "name": "Free delivery",
                    "deliveredBy": "Carrier",
                    "methodId": "delivery-1",
                    "status": "DELIVERED",
                },
            )
        ),
    )

    assert order.order_date.tzinfo == UTC
    assert order.create_date.tzinfo == UTC
    assert order.create_date.hour == 11
    assert order.payment_date is not None
    assert order.payment_date.tzinfo == UTC
    assert order.delivery_total == Decimal("0")
    assert order.delivery is not None
    assert order.delivery.cost_amount == Decimal("0")
    assert order.print_offers() == order.format_offers()
    assert order.is_balanced == order.is_known_total_balanced


def test_order_create_date_and_payment_date_optional_branches():
    order = Order.from_payload(
        "group-1",
        OrderPayload.model_validate(
            _order_item(
                create_date=None,
                payment_date=None,
                delivery=None,
            )
        ),
    )

    assert order.create_date.tzinfo == UTC
    assert order.create_date == order.order_date
    assert order.payment_date is None
    assert order.delivery_total == Decimal("0")


def test_payment_details_skip_missing_or_free_delivery_and_warn_on_mismatch(
    monkeypatch,
):
    first = Order.from_payload(
        "group-1",
        OrderPayload.model_validate(_order_item(payment_id="pay-77")),
    )
    second = Order.from_payload(
        "group-1",
        OrderPayload.model_validate(
            _order_item(
                order_id="order-2",
                payment_id="pay-77",
                payment_provider="CARD",
                payment_method="CARD",
                payment_currency="EUR",
                payment_amount="99.99",
                total_cost_amount="99.99",
                delivery={
                    "cost": {"amount": "0.00", "currency": "PLN"},
                    "name": "Free delivery",
                    "deliveredBy": "Carrier",
                    "methodId": "delivery-2",
                    "status": "DELIVERED",
                },
            )
        ),
    )

    warning = MagicMock()
    monkeypatch.setattr(get_order_result_module._LOGGER, "warning", warning)
    payment = Payment.from_orders([first, second])[0]

    assert payment.amount == Decimal("22.83")
    assert payment.date == first.payment_date
    assert payment.is_balanced is False
    assert payment.list_details() == [
        "Sample Product x1 (12.34 PLN)",
        "Delivery: Allegro One Box, DPD (10.49 PLN)",
        "Sample Product x1 (12.34 PLN)",
    ]
    assert payment.sum_total_cost == payment.known_total
    warning.assert_called_once_with(
        "Inconsistent payment metadata for %s; mismatched fields: %s",
        "pay-77",
        "currency, provider, method, amount",
    )


def test_payment_list_details_skips_missing_delivery_and_missing_cost():
    missing_delivery = Order.from_payload(
        "group-1",
        OrderPayload.model_validate(
            _order_item(order_id="order-3", payment_id="pay-88", delivery=None)
        ),
    )
    missing_cost = Order.from_payload(
        "group-1",
        OrderPayload.model_validate(
            _order_item(
                order_id="order-4",
                payment_id="pay-88",
                delivery={
                    "name": "Mystery delivery",
                    "deliveredBy": "Carrier",
                    "methodId": "delivery-4",
                    "status": "DELIVERED",
                },
            )
        ),
    )
    missing_cost.delivery = SimpleNamespace(
        cost_amount=Decimal("1.00"),
        cost=None,
        name="Mystery delivery",
    )

    payment = Payment.from_orders([missing_delivery, missing_cost])[0]

    assert payment.list_details() == [
        "Sample Product x1 (12.34 PLN)",
        "Sample Product x1 (12.34 PLN)",
    ]


def test_payment_date_raises_without_orders():
    payment = Payment(payment_id="pay-1", orders=[])

    with pytest.raises(ValueError, match="No orders in payment"):
        _ = payment.date


def test_offer_simplified_title_truncates_and_normalizes():
    offer = Offer(
        offer_id="o2",
        title="super-fast usb-c cable with extra-long name",
        unit_price=Decimal("1.00"),
        price_currency="PLN",
        friendly_url="u",
        quantity=1,
        image_url="i",
    )

    assert offer.get_simplified_title() == "Super-Fast Usb-c Cable"
