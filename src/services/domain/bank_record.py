from collections.abc import Iterable
from dataclasses import dataclass, fields
from decimal import Decimal

from services.domain.base import BaseMatchItem
from services.domain.evidence import Evidence, add_line
from services.domain.transaction import Transaction, TransactionUpdate, TxTag


@dataclass(slots=True)
class BankRecord(BaseMatchItem, Evidence):
    details: str
    recipient: str
    operation_amount: Decimal
    sender: str = ""
    operation_currency: str = "PLN"
    account_currency: str = "PLN"
    sender_account: str = ""
    recipient_account: str = ""

    def pretty_print(
        self,
        *,
        only_meaningful: bool = False,
        include: Iterable[str] | None = None,
        exclude: Iterable[str] | None = None,
    ) -> str:
        include = set(include) if include else None
        exclude = set(exclude or [])

        def is_meaningful(value) -> bool:
            if value is None:
                return False
            if isinstance(value, str):
                return value.strip() != ""
            if isinstance(value, (int, float, Decimal)):
                return value != 0
            return True

        lines: list[str] = []

        for f in fields(self):
            name = f.name
            value = getattr(self, name)

            if include is not None:
                if name not in include:
                    continue
            elif name in exclude or (only_meaningful and not is_meaningful(value)):
                continue

            lines.append(f"{name}: {value}")

        return "\n".join(lines)

    def build_tx_update(self, tx: Transaction) -> TransactionUpdate:
        new_description: str | None = None
        if (
            self.details.lower() not in (tx.description).lower()
        ):  # inclomplete processed
            new_description = f"{tx.description};{self.details}"
        notes = add_line(tx.notes, self.pretty_print(only_meaningful=True))
        tags = set(tx.tags)
        tags.add(TxTag.blik_done)
        tags = list(tags)
        return TransactionUpdate(
            description=new_description,
            notes=notes,
            tags=tags,
        )
