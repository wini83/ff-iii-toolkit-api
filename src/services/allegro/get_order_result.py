"""Data structures for the ``get_orders`` API call."""

from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Self

from services.allegro.payloads import (
    DeliveryPayload,
    GetOrdersResponse,
    MoneyPayload,
    OfferPayload,
    OrderPayload,
)

_LOGGER = logging.getLogger(__name__)


def short_id(id_str: str, length: int = 8) -> str:
    """Return a short, deterministic hash of ``id_str``."""
    return hashlib.sha1(id_str.encode()).hexdigest()[:length]


class GetOrdersResult:  # pylint: disable=too-few-public-methods
    """Result of get_orders method."""

    def __init__(self, items: GetOrdersResponse) -> None:
        """Init method."""
        self._payload = items
        self.orders: list[Order] = []
        for group in self._payload.order_groups:
            for order_payload in group.orders:
                self.orders.append(Order.from_payload(group.group_id, order_payload))
        self.payments: list[Payment] = Payment.from_orders(self.orders)

    @classmethod
    def from_dict(cls, items: dict[str, Any]) -> Self:
        """Create result from a raw API payload."""
        return cls(GetOrdersResponse.model_validate(items))

    def as_list(self) -> list[Order]:
        """Return orders as list."""
        return self.orders


@dataclass(slots=True)
class Offer:
    """Single offer item."""

    offer_id: str
    title: str
    unit_price: Decimal
    price_currency: str
    friendly_url: str
    quantity: int
    image_url: str

    @classmethod
    def from_payload(cls, payload: OfferPayload) -> Offer:
        """Create :class:`Offer` from parsed API payload."""
        return cls(
            offer_id=payload.offer_id,
            title=payload.title,
            unit_price=payload.unit_price.amount,
            price_currency=payload.unit_price.currency,
            friendly_url=payload.friendly_url,
            quantity=payload.quantity,
            image_url=payload.image_url,
        )

    def get_simplified_title(self) -> str:
        """Create shortened title suitable for tagging."""

        def format_word(title_word: str) -> str:
            return "-".join(
                w.capitalize() if len(w) > 2 else w.lower()
                for w in title_word.split("-")
            )

        clean = re.sub(r"[^\w\s\-]", "", self.title or "", flags=re.UNICODE)

        words = clean.split()
        result: list[str] = []
        total_length = 0

        for word in words:
            formatted = format_word(word)
            extra = len(formatted) + (1 if result else 0)

            if len(result) < 3 and total_length + extra <= 32:
                result.append(formatted)
                total_length += extra
            else:
                break

        return " ".join(result)


@dataclass(slots=True)
class Order:
    """Single order item."""

    order_id: str
    group_id: str
    purchase_id: str | None
    seller: str
    offers: list[Offer]
    delivery: Delivery | None
    _order_date: datetime
    _create_date: datetime | None
    _payment_date: datetime | None
    total_cost_amount: Decimal
    payment_amount: Decimal
    currency_code: str
    payment_provider: str
    payment_method: str
    payment_id: str

    @classmethod
    def from_payload(cls, group_id: str, payload: OrderPayload) -> Order:
        """Create :class:`Order` from parsed API payload."""
        return cls(
            order_id=payload.order_id,
            group_id=group_id,
            purchase_id=payload.purchase_id,
            seller=payload.seller.login,
            offers=[Offer.from_payload(offer) for offer in payload.offers],
            delivery=Delivery.from_payload(payload.delivery)
            if payload.delivery
            else None,
            _order_date=payload.order_date,
            _create_date=payload.create_date,
            _payment_date=payload.payment.date,
            total_cost_amount=payload.total_cost.amount,
            payment_amount=payload.payment.amount.amount,
            currency_code=payload.payment.amount.currency,
            payment_provider=payload.payment.provider,
            payment_method=payload.payment.method,
            payment_id=payload.payment.payment_id,
        )

    @property
    def create_date(self) -> datetime:
        """Return order creation date when available."""
        if self._create_date is None:
            return self.order_date
        if self._create_date.tzinfo is None:
            return self._create_date.replace(tzinfo=UTC)
        return self._create_date

    @property
    def payment_date(self) -> datetime | None:
        """Return payment date when available."""
        if self._payment_date is None:
            return None
        if self._payment_date.tzinfo is None:
            return self._payment_date.replace(tzinfo=UTC)
        return self._payment_date

    @property
    def items_total(self) -> Decimal:
        """Return the sum of item prices in the order."""
        return sum(
            (offer.unit_price * Decimal(offer.quantity) for offer in self.offers),
            start=Decimal("0"),
        )

    @property
    def delivery_total(self) -> Decimal:
        """Return the delivery total for the order."""
        if self.delivery is None:
            return Decimal("0")
        return self.delivery.cost_amount

    @property
    def known_total(self) -> Decimal:
        """Return the total derived from modeled monetary components."""
        return self.items_total + self.delivery_total

    @property
    def balance_difference(self) -> Decimal:
        """Return payment amount minus known total."""
        return self.payment_amount - self.known_total

    @property
    def is_known_total_balanced(self) -> bool:
        """Return whether the known total reconciles with the payment amount."""
        return abs(self.balance_difference) <= Decimal("0.01")

    def format_offers(self) -> str:
        """Return human readable representation of ordered offers."""
        return "\n".join(
            f"{offer.get_simplified_title()} x{offer.quantity} ({offer.unit_price} "
            f"{offer.price_currency})"
            for offer in self.offers
        )

    def list_offers(self) -> list[str]:
        """Return list of human readable representations of ordered offers."""
        return [
            f"{offer.get_simplified_title()} x{offer.quantity} ({offer.unit_price} "
            f"{offer.price_currency})"
            for offer in self.offers
        ]

    def print_offers(self) -> str:
        """Legacy alias for :meth:`format_offers`."""
        return self.format_offers()

    @property
    def order_date(self) -> datetime:
        """Return order date as ``datetime`` with timezone awareness."""
        if self._order_date.tzinfo is None:
            return self._order_date.replace(tzinfo=UTC)
        return self._order_date

    @property
    def is_balanced(self) -> bool:
        """Legacy alias for :attr:`is_known_total_balanced`."""
        return self.is_known_total_balanced


@dataclass(slots=True)
class Delivery:
    """Single delivery item."""

    cost: MoneyPayload | None
    name: str | None
    delivered_by: str | None
    method_id: str | None
    status: str | None

    @classmethod
    def from_payload(cls, payload: DeliveryPayload) -> Delivery:
        """Create :class:`Delivery` from parsed API payload."""
        return cls(
            cost=payload.cost,
            name=payload.name,
            delivered_by=payload.delivered_by,
            method_id=payload.method_id,
            status=payload.status,
        )

    @property
    def cost_amount(self) -> Decimal:
        """Return delivery cost as decimal value."""
        if self.cost is None:
            return Decimal("0")
        return self.cost.amount


@dataclass(slots=True)
class Payment:
    """Group of orders paid together."""

    payment_id: str
    orders: list[Order]
    tolerance: Decimal = Decimal("0.01")

    def __post_init__(self) -> None:
        """Warn when payment metadata differs across grouped orders."""
        if not self.orders:
            return

        first_currency = self.orders[0].currency_code
        first_provider = self.orders[0].payment_provider
        first_method = self.orders[0].payment_method
        first_amount = self.orders[0].payment_amount

        mismatches: list[str] = []
        if any(order.currency_code != first_currency for order in self.orders[1:]):
            mismatches.append("currency")
        if any(order.payment_provider != first_provider for order in self.orders[1:]):
            mismatches.append("provider")
        if any(order.payment_method != first_method for order in self.orders[1:]):
            mismatches.append("method")
        if any(order.payment_amount != first_amount for order in self.orders[1:]):
            mismatches.append("amount")

        if mismatches:
            _LOGGER.warning(
                "Inconsistent payment metadata for %s; mismatched fields: %s",
                self.payment_id,
                ", ".join(mismatches),
            )

    @property
    def short_id(self) -> str:
        """Return short, deterministic ID for the payment."""
        return short_id(self.payment_id)

    def list_details(self) -> list[str]:
        """Return list of details for all orders in the payment."""
        details = list[str]()
        for order in self.orders:
            details.extend(order.list_offers())
            if order.delivery is None:
                continue
            if order.delivery.cost_amount == Decimal("0"):
                continue
            delivery_cost = order.delivery.cost
            if delivery_cost is None:
                continue
            delivery_name = order.delivery.name or "Delivery"
            details.append(
                f"{delivery_name} ({delivery_cost.amount} {delivery_cost.currency})"
            )
        return details

    @property
    def items_total(self) -> Decimal:
        """Return the sum of item totals across grouped orders."""
        return sum((order.items_total for order in self.orders), start=Decimal("0"))

    @property
    def delivery_total(self) -> Decimal:
        """Return the sum of delivery totals across grouped orders."""
        return sum((order.delivery_total for order in self.orders), start=Decimal("0"))

    @property
    def known_total(self) -> Decimal:
        """Return the total built from modeled monetary components."""
        return self.items_total + self.delivery_total

    @property
    def balance_difference(self) -> Decimal:
        """Return payment amount minus known total."""
        return self.amount - self.known_total

    @property
    def is_known_total_balanced(self) -> bool:
        """Return whether the known total reconciles with payment amount."""
        return abs(self.balance_difference) <= self.tolerance

    @property
    def sum_total_cost(self) -> Decimal:
        """Legacy alias for the known total."""
        return self.known_total

    @property
    def amount(self) -> Decimal:
        """Return paid amount value."""
        if not self.orders:
            return Decimal("0")
        return self.orders[0].payment_amount

    @property
    def currency_code(self) -> str:
        """Return currency code of the payment."""
        if not self.orders:
            raise ValueError("No orders in payment")
        return self.orders[0].currency_code

    @property
    def payment_provider(self) -> str:
        """Return payment provider."""
        if not self.orders:
            raise ValueError("No orders in payment")
        return self.orders[0].payment_provider

    @property
    def payment_method(self) -> str:
        """Return payment method."""
        if not self.orders:
            raise ValueError("No orders in payment")
        return self.orders[0].payment_method

    @property
    def date(self) -> datetime:
        """Return payment date."""
        if not self.orders:
            raise ValueError("No orders in payment")
        return self.orders[0].payment_date or self.orders[0].create_date

    @property
    def is_balanced(self) -> bool:
        """Legacy alias for :attr:`is_known_total_balanced`."""
        return self.is_known_total_balanced

    def __str__(self) -> str:
        return (
            f"Payment {self.short_id}: "
            f"Payment metadata: {self.payment_provider}/{self.payment_method} "
            f"{len(self.orders)} orders, {self.amount:.2f} "
            f"total, balanced: {self.is_balanced}"
        )

    def __repr__(self) -> str:
        return (
            f"Payment {short_id(self.payment_id)}: {len(self.orders)} "
            f"orders, {self.amount:.2f} total, balanced: {self.is_balanced}"
        )

    @classmethod
    def from_orders(cls, orders: list[Order]) -> list[Self]:
        """Group orders by ``payment_id`` and create ``Payment`` objects."""
        grouped: dict[str, list[Order]] = defaultdict(list)

        for order in orders:
            grouped[order.payment_id].append(order)

        return [
            cls(payment_id=payment_id, orders=group)
            for payment_id, group in grouped.items()
        ]
