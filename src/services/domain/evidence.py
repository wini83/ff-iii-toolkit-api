from typing import Protocol

from services.domain.transaction import Transaction, TransactionUpdate


class Evidence(Protocol):
    def build_tx_update(self, tx: Transaction) -> TransactionUpdate: ...


def add_line(existing: str | None, new_line: str) -> str:
    if existing:
        return existing + "\n" + new_line
    return new_line
