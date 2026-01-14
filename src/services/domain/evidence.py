from typing import Protocol

from services.domain.transaction import Transaction, TransactionUpdate


class Evidence(Protocol):
    def build_tx_update(self, tx: Transaction) -> TransactionUpdate: ...
