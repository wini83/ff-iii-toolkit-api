from dataclasses import dataclass
from enum import StrEnum

from services.domain.base import Matchable


class MatchProcessingStatus(StrEnum):
    NEW = "new"
    ALREADY_PROCESSED = "already_processed"


@dataclass
class MatchResult:
    tx: Matchable
    matches: list[Matchable]
    status: MatchProcessingStatus = MatchProcessingStatus.NEW
