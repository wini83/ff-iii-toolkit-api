"""Runtime-scoped dependencies (process singletons)."""

from functools import lru_cache

from fastapi import Depends

from api.deps_services import (
    get_allegro_service,
    get_firefly_allegro_service,
    get_firefly_blik_service,
    get_firefly_tx_service,
    get_user_secrets_service,
)
from services.allegro_application_service import AllegroApplicationService
from services.allegro_service import AllegroService
from services.allegro_state_store import AllegroStateStore, get_allegro_state_store
from services.blik_application_service import BlikApplicationService
from services.firefly_allegro_service import FireflyAllegroService
from services.tx_application_service import TxApplicationService
from services.user_secrets_service import UserSecretsService


@lru_cache(maxsize=1)
def get_blik_application_runtime() -> BlikApplicationService:
    return BlikApplicationService(blik_service=get_firefly_blik_service())


@lru_cache(maxsize=1)
def get_tx_application_runtime() -> TxApplicationService:
    return TxApplicationService(tx_service=get_firefly_tx_service())


def get_allegro_application_runtime(
    secrets_service: UserSecretsService = Depends(get_user_secrets_service),
    ff_allegro_service: FireflyAllegroService = Depends(get_firefly_allegro_service),
    allegro_service: AllegroService = Depends(get_allegro_service),
    state: AllegroStateStore = Depends(get_allegro_state_store),
) -> AllegroApplicationService:
    return AllegroApplicationService(
        secrets_service=secrets_service,
        ff_allegro_service=ff_allegro_service,
        allegro_service=allegro_service,
        state_store=state,
    )
