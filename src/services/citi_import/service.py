from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from services.citi_import.cache import CitiImportStore
from services.citi_import.exporter import CitiCsvZipExporter
from services.citi_import.mapper import CitiBankRecordMapper
from services.citi_import.parser import CitiTextParser
from services.domain.bank_record import BankRecord
from services.exceptions import InvalidFileFormat


@dataclass(slots=True)
class CitiParsePreview:
    file_id: str
    record_count: int
    preview: list[BankRecord]
    warnings: list[str]


@dataclass(slots=True)
class CitiExportPayload:
    filename: str
    media_type: str
    content: BytesIO


class CitiImportService:
    def __init__(
        self,
        *,
        parser: CitiTextParser,
        mapper: CitiBankRecordMapper,
        store: CitiImportStore,
        exporter: CitiCsvZipExporter,
    ) -> None:
        self.parser = parser
        self.mapper = mapper
        self.store = store
        self.exporter = exporter

    async def parse_text(
        self,
        *,
        raw_text: str,
        include_positive: bool = False,
        chunk_size: int = 60,
        source_name: str | None = None,
    ) -> CitiParsePreview:
        parsed = self.parser.parse(
            raw_text=raw_text,
            include_positive=include_positive,
        )
        records = self.mapper.to_bank_records(parsed.transactions)
        entry = self.store.create(
            records=records,
            warnings=parsed.warnings,
            chunk_size=chunk_size,
            include_positive=include_positive,
            source_name=source_name,
        )
        return self._build_preview(
            file_id=entry.file_id,
            records=records,
            warnings=parsed.warnings,
        )

    async def upload_text_file(
        self,
        *,
        filename: str | None,
        file_bytes: bytes,
        include_positive: bool = False,
        chunk_size: int = 60,
    ) -> CitiParsePreview:
        if filename and not filename.lower().endswith(".txt"):
            raise InvalidFileFormat("Only .txt files are supported")

        raw_text = self._decode_text(file_bytes)
        return await self.parse_text(
            raw_text=raw_text,
            include_positive=include_positive,
            chunk_size=chunk_size,
            source_name=filename,
        )

    async def get_file(self, *, file_id: str) -> CitiParsePreview:
        entry = self.store.get(file_id=file_id)
        return self._build_preview(
            file_id=entry.file_id,
            records=entry.records,
            warnings=entry.warnings,
        )

    async def export_csv_zip(self, *, file_id: str) -> CitiExportPayload:
        entry = self.store.get(file_id=file_id)
        export_name = self.exporter.build_export_name(
            file_id=file_id,
            records=entry.records,
        )
        content = self.exporter.export_zip(
            file_id=file_id,
            records=entry.records,
            chunk_size=entry.chunk_size,
        )
        return CitiExportPayload(
            filename=f"{export_name}.zip",
            media_type="application/zip",
            content=BytesIO(content),
        )

    def _build_preview(
        self,
        *,
        file_id: str,
        records: list[BankRecord],
        warnings: list[str],
    ) -> CitiParsePreview:
        return CitiParsePreview(
            file_id=file_id,
            record_count=len(records),
            preview=records,
            warnings=warnings,
        )

    def _decode_text(self, file_bytes: bytes) -> str:
        for encoding in ("utf-8-sig", "cp1250", "latin-1"):
            try:
                return file_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        return file_bytes.decode("utf-8", errors="replace")
