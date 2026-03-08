from collections.abc import Callable
from dataclasses import replace

from requests import Session

from services.allegro.api import AllegroApiClient, AllegroApiError, AllegroAuthError
from services.domain.allegro import (
    AllegroAccount,
    AllegroOrderPayment,
    AllegroOrderPayments,
)


class AllegroServiceError(RuntimeError):
    """Raised when Allegro API calls fail."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details


class AllegroService:
    def __init__(
        self,
        client_factory: Callable[[str], AllegroApiClient],
    ) -> None:
        self._client_factory = client_factory

    def _client_for(self, account: AllegroAccount) -> AllegroApiClient:
        client = self._client_factory(account.secret)

        return client

    def fetch(
        self,
        account: AllegroAccount,
        limit: int = 25,
        offset: int = 0,
    ) -> AllegroOrderPayments:
        client = self._client_for(account)

        try:
            if account.login is None:
                info = client.get_user_info()
                account = replace(account, login=info.login)

            raw = client.get_orders(limit=limit, offset=offset)
            payments = [
                AllegroOrderPayment.from_allegro_payment(p, account.login or "unknown")
                for p in raw.payments
            ]

            return AllegroOrderPayments(payments=payments)

        except Exception as exc:
            raise self._wrap_error(exc) from exc

    # --------------------------------------------------
    # Error mapping
    # --------------------------------------------------

    def _wrap_error(self, exc: Exception) -> AllegroServiceError:
        if isinstance(exc, AllegroAuthError):
            return AllegroServiceError(
                "allegro authentication failed",
                details={"error": str(exc)},
            )
        if isinstance(exc, AllegroApiError):
            return AllegroServiceError(
                "allegro api error",
                details={"error": str(exc)},
            )
        raise exc


def allegro_client_factory(secret: str) -> AllegroApiClient:
    return AllegroApiClient(
        cookie=secret,
        session=Session(),
    )
