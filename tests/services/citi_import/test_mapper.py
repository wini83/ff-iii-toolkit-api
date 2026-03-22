from datetime import date

from services.citi_import.mapper import CitiBankRecordMapper
from services.citi_import.models import ParsedCitiTransaction


def test_mapper_converts_parsed_transaction_to_bank_record():
    mapper = CitiBankRecordMapper()

    record = mapper.to_bank_record(
        ParsedCitiTransaction(
            date=date(2025, 1, 16),
            payee="Test Shop",
            amount_text="-42,00PLN",
            amount_currency="PLN",
            amount_value="-42.00",
        )
    )

    assert record.date == date(2025, 1, 16)
    assert str(record.amount) == "-42.00"
    assert record.details == "Test Shop"
    assert record.recipient == "Test Shop"
    assert str(record.operation_amount) == "-42.00"
    assert record.operation_currency == "PLN"
