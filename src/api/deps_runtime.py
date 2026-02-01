"""Runtime-scoped dependencies (process singletons)."""

from functools import lru_cache

from api.deps_services import get_firefly_blik_service, get_firefly_tx_service
from services.blik_application_service import BlikApplicationService
from services.tx_application_service import TxApplicationService


@lru_cache(maxsize=1)
def get_blik_application_runtime() -> BlikApplicationService:
    return BlikApplicationService(blik_service=get_firefly_blik_service())


@lru_cache(maxsize=1)
def get_tx_application_runtime() -> TxApplicationService:
    return TxApplicationService(tx_service=get_firefly_tx_service())
