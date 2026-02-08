from dataclasses import dataclass
from uuid import UUID

from services.allegro.get_order_result import Payment as allegro_payment
from services.domain.order_payment import OrderPayment
from services.domain.transaction import TxTag


@dataclass(frozen=True)
class AllegroAccount:
    id: UUID  # lokalny ID (UserSecret.id)
    secret: str  # cookie / token
    login: str | None = None


@dataclass
class AllegroOrderPayment(OrderPayment):
    """Representation of an Allegro order payment."""

    is_balanced: bool
    allegro_login: str  # display metadata, NOT identity

    @classmethod
    def from_allegro_payment(cls, payment: allegro_payment, allegro_login: str):
        """Create AllegroOrderPayment from allegro Payment."""
        # allegro_login is used ONLY for details / UI
        details = list[str]()
        details.append(f"Buyer: {allegro_login}")
        details.extend(payment.list_details())
        return cls(
            amount=payment.amount,
            date=payment.date.date(),
            details=details,
            tag_done=TxTag.allegro_done,
            is_balanced=payment.is_balanced,
            allegro_login=allegro_login,
        )


@dataclass
class AllegroOrderPayments:
    """Collection of Allegro order payments."""

    payments: list[AllegroOrderPayment]
