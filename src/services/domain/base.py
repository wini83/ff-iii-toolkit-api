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

    def compare_amounts_abs(self, other: "Matchable") -> bool:
        return abs(self.amount) == abs(other.amount)

    def compare(self, other: "Matchable") -> bool:
        if not self.compare_amounts_abs(other=other):
            return False
        return self.date == other.date
