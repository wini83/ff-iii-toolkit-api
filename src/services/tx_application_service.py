import calendar
from datetime import date

from api.mappers.tx import map_category_to_api, map_tx_to_api
from api.models.tx import (
    ScreeningMonthResponse,
    TxTag,
)
from services.domain.metrics import TXStatisticsMetrics
from services.exceptions import ExternalServiceFailed
from services.firefly_base_service import FireflyServiceError
from services.firefly_tx_service import FireflyTxService
from services.tx_stats.manager import TxMetricsManager
from services.tx_stats.models import MetricsState


class TxApplicationService:
    """
    Application-level service for transaction screening and updates.

    Responsibilities:
    - orchestrate screening flows
    - map domain objects to API DTOs
    """

    def __init__(self, *, tx_service: FireflyTxService) -> None:
        self.tx_service = tx_service
        self.tx_metrics_manager = TxMetricsManager(tx_service=tx_service)

    # --------------------------------------------------
    # SCREENING
    # --------------------------------------------------

    async def get_screening_month(
        self, *, year: int, month: int
    ) -> ScreeningMonthResponse | None:
        start_date, end_date = self._month_range(year=year, month=month)
        try:
            categories = await self.tx_service.get_categories()
            txs = await self.tx_service.get_txs_for_screening(
                start_date=start_date, end_date=end_date
            )
        except FireflyServiceError as e:
            raise ExternalServiceFailed(str(e)) from e

        if not txs:
            return None

        return ScreeningMonthResponse(
            year=year,
            month=month,
            remaining=len(txs),
            transactions=[map_tx_to_api(tx) for tx in txs],
            categories=[map_category_to_api(cat) for cat in categories],
        )

    # --------------------------------------------------
    # UPDATES
    # --------------------------------------------------

    async def apply_category(self, *, tx_id: int, category_id: int) -> None:
        try:
            await self.tx_service.apply_category_by_id(
                tx_id=tx_id, category_id=category_id
            )
        except FireflyServiceError as e:
            raise ExternalServiceFailed(str(e)) from e

    async def apply_tag(self, *, tx_id: int, tag: TxTag) -> None:
        try:
            await self.tx_service.add_tag_by_id(tx_id=tx_id, tag=tag.value)
        except FireflyServiceError as e:
            raise ExternalServiceFailed(str(e)) from e

    # --------------------------------------------------
    # METRICS
    # --------------------------------------------------

    async def get_tx_metrics(self) -> MetricsState[TXStatisticsMetrics]:
        state = self.tx_metrics_manager.get_state()
        return state

    async def refresh_tx_metrics(self) -> MetricsState[TXStatisticsMetrics]:
        state = await self.tx_metrics_manager.refresh()
        return state

    # --------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------

    @staticmethod
    def _month_range(year: int, month: int) -> tuple[date, date]:
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        return first_day, last_day
