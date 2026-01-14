from datetime import date
from decimal import Decimal

from services.domain.bank_record import BankRecord
from services.domain.transaction import Transaction, TxTag


def test_pretty_print_only_meaningful_skips_empty_fields():
    record = BankRecord(
        date=date(2024, 1, 5),
        amount=Decimal("12.34"),
        details="BLIK payment",
        recipient="ACME",
        operation_amount=Decimal("12.34"),
    )

    output = record.pretty_print(only_meaningful=True)

    assert "details: BLIK payment" in output
    assert "recipient: ACME" in output
    assert "sender:" not in output
    assert "recipient_account:" not in output


def test_build_tx_update_appends_description_notes_and_tags():
    record = BankRecord(
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        details="ATM withdrawal",
        recipient="Bank",
        operation_amount=Decimal("10.00"),
    )
    tx = Transaction(
        id=1,
        date=date(2024, 1, 5),
        amount=Decimal("10.00"),
        description="Payment",
        tags=set(),
        notes=None,
        category=None,
    )

    update = record.build_tx_update(tx)

    assert update.description == "Payment;ATM withdrawal"
    assert "details: ATM withdrawal" in (update.notes or "")
    assert TxTag.blik_done in update.tags
