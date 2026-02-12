from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Literal
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
    external_short_id: str  # short ID of the payment
    external_id: str  # full ID of the payment

    @classmethod
    def from_allegro_payment(cls, payment: allegro_payment, allegro_login: str):
        """Create AllegroOrderPayment from allegro Payment."""
        # allegro_login is used ONLY for details / UI
        details = list[str]()
        details.append(f"Buyer: {allegro_login}")
        details.append(f"Payment ID: {payment.short_id}")
        details.extend(payment.list_details())
        details.append(
            f"Payment metadata: {payment.payment_method}/{payment.payment_provider}"
        )
        return cls(
            amount=payment.amount,
            date=payment.date.date(),
            details=details,
            tag_done=TxTag.allegro_done,
            is_balanced=payment.is_balanced,
            allegro_login=allegro_login,
            external_short_id=payment.short_id,
            external_id=payment.payment_id,
        )


@dataclass
class AllegroOrderPayments:
    """Collection of Allegro order payments."""

    payments: list[AllegroOrderPayment]


@dataclass
class MatchDecision:
    payment_id: str
    transaction_id: int
    strategy: Literal["auto", "manual", "force"] = "auto"


class ApplyJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(slots=True)
class AllegroApplyJob:
    id: UUID
    secret_id: UUID
    total: int
    status: ApplyJobStatus
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    applied: int = 0
    failed: int = 0

    finished_at: datetime | None = None
