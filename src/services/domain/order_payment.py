from dataclasses import dataclass
from datetime import timedelta

from services.domain.base import BaseMatchItem, Matchable
from services.domain.evidence import add_line
from services.domain.transaction import Transaction, TransactionUpdate, TxTag


@dataclass
class OrderPayment(BaseMatchItem):
    """Abstractional representation of an Order payment."""

    details: list[str]
    tag_done: TxTag

    def flatten_details(self) -> str:
        """Return details as a single string."""
        return "\n".join(self.details)

    def compare(self, other: "Matchable") -> bool:
        """Check whether ``other`` matches this payment within tolerance."""
        if not bool(super().compare_amounts_abs(other)):
            return False
        latest_acceptable_date = self.date + timedelta(days=6)
        return self.date <= other.date <= latest_acceptable_date

    def build_tx_update(self, tx: Transaction) -> TransactionUpdate:
        details = self.flatten_details()
        if details == "":
            raise ValueError("Details cannot be empty")
        notes: str | None = None
        if tx.notes:
            if details.lower() not in tx.notes.lower():
                notes = add_line(tx.notes, details)
        else:
            notes = add_line(tx.notes, details)
        tags = set(tx.tags)
        tags.add(self.tag_done)
        tags_list = list(tags)
        return TransactionUpdate(
            notes=notes,
            tags=tags_list,
        )
