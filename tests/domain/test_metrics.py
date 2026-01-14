from datetime import UTC, datetime

from services.domain.metrics import BlikStatisticsMetrics, FetchMetrics


def test_fetch_metrics_fields():
    metrics = FetchMetrics(
        total_transactions=10,
        fetching_duration_ms=123,
        invalid=1,
        multipart=2,
    )

    assert metrics.total_transactions == 10
    assert metrics.fetching_duration_ms == 123
    assert metrics.invalid == 1
    assert metrics.multipart == 2


def test_blik_statistics_metrics_fields():
    now = datetime.now(UTC)
    metrics = BlikStatisticsMetrics(
        total_transactions=20,
        fetching_duration_ms=456,
        single_part_transactions=18,
        uncategorized_transactions=7,
        filtered_by_description_exact=2,
        filtered_by_description_partial=3,
        not_processed_transactions=2,
        not_processed_by_month={"2024-01": 1},
        inclomplete_procesed_by_month={"2024-02": 1},
        time_stamp=now,
    )

    assert metrics.total_transactions == 20
    assert metrics.single_part_transactions == 18
    assert metrics.uncategorized_transactions == 7
    assert metrics.filtered_by_description_exact == 2
    assert metrics.filtered_by_description_partial == 3
    assert metrics.not_processed_transactions == 2
    assert metrics.not_processed_by_month == {"2024-01": 1}
    assert metrics.inclomplete_procesed_by_month == {"2024-02": 1}
    assert metrics.time_stamp is now
