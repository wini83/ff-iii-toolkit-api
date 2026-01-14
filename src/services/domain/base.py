from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


class Matchable(Protocol):
    date: date
    amount: Decimal

    def compare(self, other: "Matchable") -> bool: ...


@dataclass(slots=True)
class BaseMatchItem(Matchable):
    date: date
    amount: Decimal

    def compare(self, other: "Matchable") -> bool:
        return self.date == other.date and self.amount == other.amount


def add_line(existing: str | None, new_line: str) -> str:
    if existing:
        return existing + "\n" + new_line
    return new_line
