from dataclasses import dataclass
from datetime import datetime

from services.domain.metrics import FetchMetrics
from services.domain.transaction import Transaction


@dataclass(slots=True)
class TransactionSnapshot:
    transactions: list[Transaction]
    metrics: FetchMetrics
    fetched_at: datetime
    schema_version: int = 1

    @property
    def transaction_count(self) -> int:
        return len(self.transactions)
