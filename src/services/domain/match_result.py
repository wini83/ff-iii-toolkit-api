from dataclasses import dataclass

from services.domain.base import Matchable


@dataclass
class MatchResult:
    tx: Matchable
    matches: list[Matchable]
