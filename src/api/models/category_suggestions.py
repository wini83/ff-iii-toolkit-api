from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class CategorySuggestionPreviewRequest(BaseModel):
    title: str
    merchant: str | None = None
    notes: str | None = None
    amount: Decimal
    source_type: Literal["bank", "blik", "allegro"] = Field(default="bank")


class CategorySuggestionDto(BaseModel):
    category_id: str
    category_name: str
    score: float
    reason: str


class CategorySuggestionsResponse(BaseModel):
    suggestions: list[CategorySuggestionDto]
