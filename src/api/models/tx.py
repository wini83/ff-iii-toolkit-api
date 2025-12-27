from dataclasses import dataclass

from fireflyiii_enricher_core.firefly_client import SimplifiedCategory, SimplifiedTx


@dataclass
class ScreeningResponse:
    tx: SimplifiedTx
    categories: list[SimplifiedCategory]


@dataclass
class ScreeningMonthResponse:
    year: int
    month: int
    remaining: int
    transactions: list[SimplifiedTx]
    categories: list[SimplifiedCategory]
