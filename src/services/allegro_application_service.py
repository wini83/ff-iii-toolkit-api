from uuid import UUID

from services.allegro.api import AllegroApiClient
from services.domain.user_secrets import SecretType, UserSecretReadModel
from services.user_secrets_service import UserSecretsService


class AllegroApplicationService:
    def __init__(
        self, secrets_service: UserSecretsService, allegro_api_client: AllegroApiClient
    ) -> None:
        self.secrets_service = secrets_service
        self.allegro_api_client = allegro_api_client

    def get_allegro_secrets(self, user_id: UUID) -> list[UserSecretReadModel]:
        secrets = self.secrets_service.list_for_user(user_id=user_id)
        allegro_secrets = [
            secret for secret in secrets if secret.type == SecretType.ALLEGRO
        ]
        return allegro_secrets

    def fetch_allegro_data(self, secrets_ids: list[UUID]):
        pass
