from datetime import date
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

from services.citi_import.exporter import CitiCsvZipExporter
from services.domain.bank_record import BankRecord


def _record(index: int) -> BankRecord:
    return BankRecord(
        date=date(2025, 1, index),
        amount=Decimal(f"-{index}.00"),
        details=f"Shop {index}",
        recipient=f"Shop {index}",
        operation_amount=Decimal(f"-{index}.00"),
    )


def test_exporter_returns_single_csv_zip_when_records_fit_chunk():
    exporter = CitiCsvZipExporter()

    payload = exporter.export_zip(
        file_id="file-1",
        records=[_record(1)],
        chunk_size=60,
    )

    with ZipFile(BytesIO(payload)) as archive:
        assert archive.namelist() == ["citi_file-1_20250101_20250101.csv"]
        content = archive.read("citi_file-1_20250101_20250101.csv").decode()

    assert "Date;Amount;Payee;Description" in content
    assert "2025-01-01;-1.00;Shop 1;Shop 1" in content


def test_exporter_splits_csv_into_multiple_files_when_chunk_size_is_exceeded():
    exporter = CitiCsvZipExporter()

    payload = exporter.export_zip(
        file_id="file-1",
        records=[_record(1), _record(2), _record(3)],
        chunk_size=2,
    )

    with ZipFile(BytesIO(payload)) as archive:
        assert archive.namelist() == [
            "citi_file-1_20250101_20250103_1.csv",
            "citi_file-1_20250101_20250103_2.csv",
        ]
