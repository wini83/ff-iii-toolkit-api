from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from services.citi_import.models import CitiImportFile
from services.domain.bank_record import BankRecord
from services.exceptions import FileNotFound, InvalidFileId


@dataclass
class CitiImportStore:
    _files: dict[str, CitiImportFile] = field(default_factory=dict)

    def create(
        self,
        *,
        records: list[BankRecord],
        warnings: list[str],
        chunk_size: int,
        include_positive: bool,
        source_name: str | None,
    ) -> CitiImportFile:
        file_id = str(uuid4())
        entry = CitiImportFile(
            file_id=file_id,
            records=list(records),
            warnings=list(warnings),
            chunk_size=chunk_size,
            include_positive=include_positive,
            source_name=source_name,
        )
        self._files[file_id] = entry
        return entry

    def get(self, *, file_id: str) -> CitiImportFile:
        self._validate_file_id(file_id)
        entry = self._files.get(file_id)
        if entry is None:
            raise FileNotFound()
        return entry

    def _validate_file_id(self, file_id: str) -> None:
        try:
            UUID(file_id)
        except ValueError as exc:
            raise InvalidFileId(file_id) from exc


_store = CitiImportStore()


def get_citi_import_store() -> CitiImportStore:
    return _store
