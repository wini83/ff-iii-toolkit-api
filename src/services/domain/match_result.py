from dataclasses import dataclass
from enum import Enum

from services.domain.base import Matchable


class MatchProcessingStatus(str, Enum):
    NEW = "new"
    ALREADY_PROCESSED = "already_processed"


@dataclass
class MatchResult:
    tx: Matchable
    matches: list[Matchable]
    status: MatchProcessingStatus = MatchProcessingStatus.NEW
