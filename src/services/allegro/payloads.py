"""Pydantic models for Allegro ``get_orders`` payloads."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _PayloadModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class MoneyPayload(_PayloadModel):
    amount: Decimal
    currency: str


class SellerPayload(_PayloadModel):
    id: str | None = None
    login: str


class DeliveryPayload(_PayloadModel):
    cost: MoneyPayload | None = None
    name: str | None = None
    delivered_by: str | None = Field(default=None, alias="deliveredBy")
    method_id: str | None = Field(default=None, alias="methodId")
    status: str | None = None


class OrderStatusPayload(_PayloadModel):
    primary: dict[str, Any] | None = None
    primary_custom: dict[str, Any] | None = Field(default=None, alias="primaryCustom")
    traits: list[str] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)


class OfferPayload(_PayloadModel):
    offer_id: str = Field(alias="id")
    title: str
    unit_price: MoneyPayload = Field(alias="unitPrice")
    friendly_url: str = Field(alias="friendlyUrl")
    quantity: int
    image_url: str = Field(alias="imageUrl")


class PaymentPayload(_PayloadModel):
    method_id: str | None = Field(default=None, alias="methodId")
    status: str | None = None
    date: datetime | None = None
    amount: MoneyPayload
    provider: str
    method: str
    payment_id: str = Field(alias="id")


class OrderPayload(_PayloadModel):
    order_id: str = Field(alias="id")
    purchase_id: str | None = Field(default=None, alias="purchaseId")
    seller: SellerPayload
    offers: list[OfferPayload]
    delivery: DeliveryPayload | None = None
    create_date: datetime | None = Field(default=None, alias="createDate")
    order_date: datetime = Field(alias="orderDate")
    status: OrderStatusPayload | None = None
    total_cost: MoneyPayload = Field(alias="totalCost")
    payment: PaymentPayload

    @model_validator(mode="before")
    @classmethod
    def _fill_total_cost_currency(cls, data: object) -> object:
        """Normalize legacy payloads that omit ``totalCost.currency``."""
        if not isinstance(data, dict):
            return data

        total_cost = data.get("totalCost")
        payment = data.get("payment")
        if not isinstance(total_cost, dict) or "currency" in total_cost:
            return data
        if not isinstance(payment, dict):
            return data

        payment_amount = payment.get("amount")
        if not isinstance(payment_amount, dict):
            return data

        currency = payment_amount.get("currency")
        if not currency:
            return data

        normalized = dict(data)
        normalized_total_cost = dict(total_cost)
        normalized_total_cost["currency"] = currency
        normalized["totalCost"] = normalized_total_cost
        return normalized


class OrderGroupPayload(_PayloadModel):
    group_id: str = Field(alias="groupId")
    orders: list[OrderPayload] = Field(alias="myorders")


class GetOrdersResponse(_PayloadModel):
    order_groups: list[OrderGroupPayload] = Field(alias="orderGroups")
