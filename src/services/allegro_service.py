from collections.abc import Callable, Iterable
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
    def __init__(self, client_factory: Callable[[str], AllegroApiClient]) -> None:
        self._client_factory = client_factory

    # --------------------------------------------------
    # Account enrichment
    # --------------------------------------------------

    def enrich_accounts(
        self,
        accounts: Iterable[AllegroAccount],
    ) -> list[AllegroAccount]:
        enriched: list[AllegroAccount] = []

        for account in accounts:
            if account.login is not None:
                enriched.append(account)
                continue

            client: AllegroApiClient = self._client_factory(account.secret)
            try:
                info = client.get_user_info()
                enriched.append(replace(account, login=info.login))
            except Exception as exc:
                raise self._wrap_error(exc) from exc

        return enriched

    # --------------------------------------------------
    # Payments
    # --------------------------------------------------

    def fetch_payments(
        self,
        accounts: Iterable[AllegroAccount],
    ) -> AllegroOrderPayments:
        all_payments: list[AllegroOrderPayment] = []

        for account in accounts:
            if account.login is None:
                raise AllegroServiceError("account login is not yet enriched")
            client: AllegroApiClient = self._client_factory(account.secret)
            try:
                raw_payment = client.get_orders()
            except Exception as exc:
                raise self._wrap_error(exc) from exc

            all_payments.extend(
                AllegroOrderPayment.from_allegro_payment(payment, account.login)
                for payment in raw_payment.payments
            )

        return AllegroOrderPayments(payments=all_payments)

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
