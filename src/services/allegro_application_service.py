from uuid import UUID

from services.allegro_stats.manager import AllegroMetricsManager
from services.domain.metrics import AllegroMetrics
from services.domain.user_secrets import SecretType, UserSecretReadModel
from services.firefly_allegro_service import FireflyAllegroService
from services.tx_stats.models import MetricsState
from services.user_secrets_service import UserSecretsService


class AllegroApplicationService:
    def __init__(
        self,
        secrets_service: UserSecretsService,
        ff_allegro_service: FireflyAllegroService,
    ) -> None:
        self.secrets_service = secrets_service
        self.ff_allegro_service = ff_allegro_service
        self.allegro_metrics_manager = AllegroMetricsManager(
            ff_allegro_service=ff_allegro_service
        )

    def get_allegro_secrets(self, user_id: UUID) -> list[UserSecretReadModel]:
        secrets = self.secrets_service.list_for_user(user_id=user_id)
        allegro_secrets = [
            secret for secret in secrets if secret.type == SecretType.ALLEGRO
        ]
        return allegro_secrets

    # --------------------------------------------------
    # METRICS V2
    # --------------------------------------------------

    def get_metrics_state(self) -> MetricsState[AllegroMetrics]:
        return self.allegro_metrics_manager.get_state()

    async def refresh_metrics_state(self) -> MetricsState[AllegroMetrics]:
        return await self.allegro_metrics_manager.refresh()
