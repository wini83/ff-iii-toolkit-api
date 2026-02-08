from uuid import UUID

from api.mappers.allegro import map_match_result_to_api
from api.models.allegro import AllegroMatchResponse
from services.allegro_service import AllegroService
from services.allegro_stats.manager import AllegroMetricsManager
from services.domain.allegro import (
    AllegroAccount,
)
from services.domain.match_result import MatchResult
from services.domain.metrics import AllegroMetrics
from services.domain.transaction import TxTag
from services.domain.user_secrets import SecretType, UserSecretReadModel
from services.exceptions import ExternalServiceFailed, InvalidSecretId
from services.firefly_allegro_service import FireflyAllegroService
from services.firefly_base_service import FireflyServiceError
from services.tx_stats.models import MetricsState
from services.user_secrets_service import UserSecretsService


class AllegroApplicationService:
    def __init__(
        self,
        secrets_service: UserSecretsService,
        ff_allegro_service: FireflyAllegroService,
        allegro_service: AllegroService,
    ) -> None:
        self.secrets_service = secrets_service
        self.ff_allegro_service = ff_allegro_service
        self.allegro_service = allegro_service
        self.allegro_metrics_manager = AllegroMetricsManager(
            ff_allegro_service=ff_allegro_service
        )
        self._matches_cache: dict[str, list[MatchResult]] = {}

    def get_allegro_secrets(self, user_id: UUID) -> list[UserSecretReadModel]:
        secrets = self.secrets_service.list_for_user(user_id=user_id)
        allegro_secrets = [
            secret for secret in secrets if secret.type == SecretType.ALLEGRO
        ]
        return allegro_secrets

    def batch_fetch_allegro_data(self, user_id: UUID, secrets_ids: list[UUID]):
        accounts: list[AllegroAccount] = []
        for secret_id in secrets_ids:
            secret = self.secrets_service.get_for_internal_use(
                secret_id=secret_id, user_id=user_id
            )
            accounts.append(AllegroAccount(secret=secret.secret, id=secret.id))

        return self.allegro_service.batch_fetch(accounts=accounts)

    def fetch_allegro_data(self, user_id: UUID, secret_id: UUID):
        try:
            secret = self.secrets_service.get_for_internal_use(
                secret_id=secret_id, user_id=user_id
            )
        except Exception as e:
            raise InvalidSecretId(
                f"Secret with id {secret_id} not found for user {user_id}"
            ) from e
        account = AllegroAccount(secret=secret.secret, id=secret.id)
        try:
            data = self.allegro_service.fetch(account=account)
            return data
        except Exception as e:
            raise ExternalServiceFailed(
                f"Failed to fetch allegro data for secret {secret_id}"
            ) from e

    async def preview_matches(
        self, user_id: UUID, secret_id: UUID
    ) -> AllegroMatchResponse:
        payments = self.fetch_allegro_data(user_id=user_id, secret_id=secret_id)
        try:
            matches = await self.ff_allegro_service.match(
                filter_text=self.ff_allegro_service.filter_desc_allegro,
                tag_done=TxTag.allegro_done,
                candidates=payments.payments,
            )
        except FireflyServiceError as e:
            raise ExternalServiceFailed(str(e)) from e

        if len(payments.payments) != 0:
            login = payments.payments[0].allegro_login
        else:
            login = "unknown"

        self._matches_cache[str(secret_id)] = matches
        not_matched = len([r for r in matches if not r.matches])
        with_one_match = len([r for r in matches if len(r.matches) == 1])
        with_many_matches = len([r for r in matches if len(r.matches) > 1])

        return AllegroMatchResponse(
            login=login,
            payments_fetched=len(payments.payments),
            transactions_found=len(matches),
            transactions_not_matched=not_matched,
            transactions_with_one_match=with_one_match,
            transactions_with_many_matches=with_many_matches,
            fetch_seconds=0.0,  # TODO: measure time taken for matching
            content=[map_match_result_to_api(r) for r in matches],
        )

    # --------------------------------------------------
    # METRICS V2
    # --------------------------------------------------

    def get_metrics_state(self) -> MetricsState[AllegroMetrics]:
        return self.allegro_metrics_manager.get_state()

    async def refresh_metrics_state(self) -> MetricsState[AllegroMetrics]:
        return await self.allegro_metrics_manager.refresh()
