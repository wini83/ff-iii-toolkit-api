from dataclasses import dataclass
from enum import Enum

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


class TxTag(str, Enum):
    blik_done = "blik_done"
    allegro_done = "allegro_done"
    rule_p = "rule_potential"
    action_req = "action_req"
