from __future__ import annotations

from decimal import Decimal

from services.citi_import.models import ParsedCitiTransaction
from services.domain.bank_record import BankRecord


class CitiBankRecordMapper:
    def to_bank_record(self, transaction: ParsedCitiTransaction) -> BankRecord:
        amount = Decimal(transaction.amount_value)
        return BankRecord(
            date=transaction.date,
            amount=amount,
            details=transaction.payee,
            recipient=transaction.payee,
            operation_amount=amount,
            operation_currency=transaction.amount_currency,
            account_currency=transaction.amount_currency,
        )

    def to_bank_records(
        self,
        transactions: list[ParsedCitiTransaction],
    ) -> list[BankRecord]:
        return [self.to_bank_record(transaction) for transaction in transactions]
