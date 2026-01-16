from dataclasses import dataclass
from datetime import datetime


@dataclass
class BaseMetrics:
    total_transactions: int
    fetching_duration_ms: int


@dataclass
class FetchMetrics(BaseMetrics):
    invalid: int
    multipart: int


@dataclass
class BlikStatisticsMetrics(BaseMetrics):
    single_part_transactions: int
    uncategorized_transactions: int
    filtered_by_description_exact: int
    filtered_by_description_partial: int
    not_processed_transactions: int
    not_processed_by_month: dict[str, int]
    inclomplete_procesed_by_month: dict[str, int]
    time_stamp: datetime
