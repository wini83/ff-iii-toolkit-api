from __future__ import annotations

import csv
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from services.domain.bank_record import BankRecord


class CitiCsvZipExporter:
    headers = [
        "Date",
        "Amount",
        "Payee",
        "Description",
        "Category",
        "Source account",
        "Destination account",
        "Tags",
        "Notes",
    ]

    def export_zip(
        self,
        *,
        file_id: str,
        records: list[BankRecord],
        chunk_size: int,
    ) -> bytes:
        effective_chunk_size = max(1, chunk_size)
        chunks = [
            records[index : index + effective_chunk_size]
            for index in range(0, len(records), effective_chunk_size)
        ] or [[]]

        buffer = BytesIO()
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
            for index, chunk in enumerate(chunks, start=1):
                suffix = f"_{index}" if len(chunks) > 1 else ""
                archive.writestr(
                    f"citi_import_{file_id}{suffix}.csv",
                    self._render_csv(chunk),
                )

        return buffer.getvalue()

    def _render_csv(self, records: list[BankRecord]) -> str:
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=self.headers, delimiter=";")
        writer.writeheader()
        writer.writerows(self._to_rows(records))
        return output.getvalue()

    def _to_rows(self, records: list[BankRecord]) -> list[dict[str, str]]:
        return [
            {
                "Date": record.date.isoformat(),
                "Amount": f"{record.amount:.2f}",
                "Payee": record.recipient,
                "Description": record.details,
                "Category": "",
                "Source account": "Bank",
                "Destination account": record.recipient,
                "Tags": "",
                "Notes": "",
            }
            for record in records
        ]
