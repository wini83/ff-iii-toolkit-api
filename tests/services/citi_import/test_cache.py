from datetime import date
from decimal import Decimal

import pytest

from services.citi_import.cache import CitiImportStore
from services.domain.bank_record import BankRecord
from services.exceptions import FileNotFound, InvalidFileId


def _record() -> BankRecord:
    return BankRecord(
        date=date(2025, 1, 16),
        amount=Decimal("-42.00"),
        details="Test Shop",
        recipient="Test Shop",
        operation_amount=Decimal("-42.00"),
    )


def test_store_create_and_get_roundtrip():
    store = CitiImportStore()

    entry = store.create(
        records=[_record()],
        warnings=["warn"],
        chunk_size=25,
        include_positive=False,
        source_name="input.txt",
    )

    loaded = store.get(file_id=entry.file_id)

    assert loaded.file_id == entry.file_id
    assert loaded.records[0].details == "Test Shop"
    assert loaded.warnings == ["warn"]
    assert loaded.chunk_size == 25


def test_store_rejects_invalid_file_id():
    store = CitiImportStore()

    with pytest.raises(InvalidFileId):
        store.get(file_id="bad-id")


def test_store_raises_file_not_found_for_missing_entry():
    store = CitiImportStore()

    with pytest.raises(FileNotFound):
        store.get(file_id="e42ecabb-e678-48c4-a8e7-e5cc3a5f7503")
