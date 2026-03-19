"""Runtime-scoped dependencies (process singletons)."""

from functools import lru_cache

from fastapi import Depends

from api.deps_services import (
    get_allegro_service,
    get_firefly_enrichment_service,
    get_firefly_tx_service,
    get_snapshot_allegro_metrics_service,
    get_snapshot_blik_metrics_service,
    get_snapshot_tx_metrics_service,
    get_user_secrets_service,
)
from services.allegro_application_service import AllegroApplicationService
from services.allegro_service import AllegroService
from services.allegro_state_store import AllegroStateStore, get_allegro_state_store
from services.blik_application_service import BlikApplicationService
from services.blik_state_store import get_blik_state_store
from services.firefly_enrichment_service import FireflyEnrichmentService
from services.tx_application_service import TxApplicationService
from services.user_secrets_service import UserSecretsService
from settings import settings


@lru_cache(maxsize=1)
def get_blik_application_runtime() -> BlikApplicationService:
    return BlikApplicationService(
        enrichment_service=get_firefly_enrichment_service(),
        metrics_provider=get_snapshot_blik_metrics_service(),
        state_store=get_blik_state_store(),
    )


@lru_cache(maxsize=1)
def get_tx_application_runtime() -> TxApplicationService:
    return TxApplicationService(
        tx_service=get_firefly_tx_service(),
        metrics_provider=get_snapshot_tx_metrics_service(),
    )


def get_allegro_application_runtime(
    secrets_service: UserSecretsService = Depends(get_user_secrets_service),
    enrichment_service: FireflyEnrichmentService = Depends(
        get_firefly_enrichment_service
    ),
    allegro_service: AllegroService = Depends(get_allegro_service),
    state: AllegroStateStore = Depends(get_allegro_state_store),
) -> AllegroApplicationService:
    return AllegroApplicationService(
        secrets_service=secrets_service,
        enrichment_service=enrichment_service,
        metrics_provider=get_snapshot_allegro_metrics_service(),
        allegro_service=allegro_service,
        state_store=state,
        filter_desc_allegro=getattr(settings, "ALLEGRO_DESCRIPTION_FILTER", "allegro"),
    )
