"""Data structures for the ``get_orders`` API call."""

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Self


def short_id(id_str: str, length: int = 8) -> str:
    """Return a short, deterministic hash of ``id_str``."""
    return hashlib.sha1(id_str.encode()).hexdigest()[:length]


class GetOrdersResult:  # pylint: disable=too-few-public-methods
    """Result of get_orders method"""

    def __init__(self, items: dict[str, Any]) -> None:
        """Init method"""
        self.orders: list[Order] = []
        for group in items["orderGroups"]:
            self.orders.append(Order(group["groupId"], group["myorders"][0]))
        self.payments: list[Payment] = Payment.from_orders(self.orders)

    def as_list(self) -> list["Order"]:
        """Return orders as list."""
        return self.orders


class Order:
    """Single order item"""

    def __init__(self, order_id: str, items: dict[str, Any]) -> None:
        """Initialize order from API response ``items``."""
        self.order_id = order_id
        self.seller = items["seller"]["login"]
        self.offers = [Offer.from_dict(o) for o in items["offers"]]
        self._order_date = items["orderDate"]
        self.total_cost_amount: Decimal = Decimal(items["totalCost"]["amount"])
        self.payment_amount = Decimal(items["payment"]["amount"]["amount"])
        self.payment_id = items["payment"]["id"]

    def print_offers(self) -> str:
        """Return human readable representation of ordered offers."""
        return "\n".join(
            f"{offer.get_simplified_title()} ({offer.unit_price} "
            f"{offer.price_currency})"
            for offer in self.offers
        )

    @property
    def order_date(self) -> datetime:
        """Return order date as ``datetime`` with timezone awareness."""
        if self._order_date.endswith("Z"):
            return datetime.fromisoformat(self._order_date[:-1]).replace(tzinfo=UTC)
        return datetime.fromisoformat(self._order_date)


@dataclass(slots=True)
class Offer:
    """Single offer item"""

    offer_id: str
    title: str
    unit_price: Decimal
    price_currency: str
    friendly_url: str
    quantity: int
    image_url: str

    @staticmethod
    def from_dict(item: dict[str, Any]) -> "Offer":
        """Create :class:`Offer` from API response ``item``."""
        return Offer(
            item["id"],
            item["title"],
            Decimal(item["unitPrice"]["amount"]),
            item["unitPrice"]["currency"],
            item["friendlyUrl"],
            int(item["quantity"]),
            item["imageUrl"],
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


@dataclass()
class Payment:
    """Group of orders paid together."""

    payment_id: str
    orders: list["Order"]
    tolerance: Decimal = Decimal("0.01")

    @property
    def sum_total_cost(self) -> Decimal:
        """Return the total cost of all orders in the payment."""
        return sum(
            (order.total_cost_amount for order in self.orders), start=Decimal("0")
        )

    @property
    def amount(self) -> Decimal:
        """Return paid amount value."""
        if not self.orders:
            return Decimal("0")
        return self.orders[0].payment_amount

    @property
    def is_balanced(self) -> bool:
        """Czy suma wartości zamówień zgadza się z kwotą płatności (z tolerancją)."""
        return abs(self.amount - self.sum_total_cost) <= self.tolerance

    def __str__(self) -> str:
        return (
            f"Payment {short_id(self.payment_id)}: "
            f"{len(self.orders)} orders, {self.amount:.2f} "
            f"total, balanced: {self.is_balanced}"
        )

    def __repr__(self) -> str:
        return (
            f"Payment {short_id(self.payment_id)}: {len(self.orders)} "
            f"orders, {self.amount:.2f} total, balanced: {self.is_balanced}"
        )

    @classmethod
    def from_orders(cls, orders: list["Order"]) -> list[Self]:
        """Grupuje zamówienia po `payment_id` i tworzy obiekty Payment."""
        grouped = defaultdict(list)

        for order in orders:
            grouped[order.payment_id].append(order)

        payments = [cls(payment_id=pid, orders=group) for pid, group in grouped.items()]
        return payments
