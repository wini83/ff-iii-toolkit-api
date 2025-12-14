from dataclasses import dataclass, fields
from typing import Iterable, List

from fireflyiii_enricher_core.firefly_client import SimplifiedItem, SimplifiedTx
from pydantic import BaseModel


@dataclass
class SimplifiedRecord(SimplifiedItem):
    details: str
    recipient: str
    operation_amount: float
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
            if isinstance(value, (int, float)):
                return value != 0
            return True

        lines = []
        for f in fields(self):
            name = f.name
            value = getattr(self, name)

            if include is not None:
                if name not in include:
                    continue
            elif name in exclude:
                continue
            elif only_meaningful and not is_meaningful(value):
                continue

            lines.append(f"{name}: {value}")

        return "\n".join(lines)


@dataclass
class MatchResult:
    tx: SimplifiedTx
    matches: List[SimplifiedRecord]


class StatisticsResponse(BaseModel):
    total_transactions: int
    single_part_transactions: int
    uncategorized_transactions: int
    filtered_by_description_exact: int
    filtered_by_description_partial: int
    not_processed_transactions: int
    not_processed_by_month: dict[str, int]
    inclomplete_procesed_by_month: dict[str, int]


class UploadResponse(BaseModel):
    message: str
    count: int
    id: str


class ApplyPayload(BaseModel):
    tx_indexes: list[int]


class FilePreviewResponse(BaseModel):
    file_id: str
    decoded_name: str
    size: int
    content: List[SimplifiedRecord]


class FileMatchResponse(BaseModel):
    file_id: str
    decoded_name: str
    records_in_file: int
    transactions_found: int
    transactions_not_matched: int
    transactions_with_one_match: int
    transactions_with_many_matches: int
    content: List[MatchResult]


class FileApplyResponse(BaseModel):
    file_id: str
    updated: int
    errors: List[str]
