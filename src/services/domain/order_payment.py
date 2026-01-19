from dataclasses import dataclass
from datetime import timedelta

from services.domain.base import BaseMatchItem, Matchable
from services.domain.evidence import Evidence, add_line
from services.domain.transaction import Transaction, TransactionUpdate, TxTag


@dataclass
class OrderPayment(BaseMatchItem, Evidence):
    """Abstractional representation of an Order payment."""

    details: str
    tag_done: TxTag

    def compare(self, other: "Matchable") -> bool:
        """Check whether ``other`` matches this payment within tolerance."""
        if not bool(super().compare_amounts_abs(other)):
            return False
        latest_acceptable_date = self.date + timedelta(days=6)
        return self.date <= other.date <= latest_acceptable_date

    def build_tx_update(self, tx: Transaction) -> TransactionUpdate:
        if self.details == "":
            raise ValueError("Details cannot be empty")
        notes: str | None = None
        if tx.notes:
            if self.details.lower() not in tx.notes.lower():
                notes = add_line(tx.notes, self.details)
        else:
            notes = add_line(tx.notes, self.details)
        tags = set(tx.tags)
        tags.add(self.tag_done)
        tags = list(tags)
        return TransactionUpdate(
            notes=notes,
            tags=tags,
        )
