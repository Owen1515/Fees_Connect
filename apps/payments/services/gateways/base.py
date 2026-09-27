"""Provider-neutral payment operations and explicit capability errors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


class GatewayError(Exception):
    """A safe provider failure without secret-bearing transport details."""


class CapabilityError(GatewayError):
    """The configured provider cannot execute the required money flow."""


@dataclass(frozen=True)
class GatewayResult:
    """Normalised provider evidence; amounts are in the payer currency."""

    reference: str
    status: str
    amount: Decimal
    currency: str
    redirect_url: str = ""
    poll_url: str = ""


class PaymentGateway(ABC):
    """Every adapter must implement creation, status lookup and refunds."""

    @abstractmethod
    def create(self, payment: Any) -> GatewayResult:
        """Create a provider payment with the persisted idempotency key."""

    @abstractmethod
    def poll(self, payment: Any) -> GatewayResult:
        """Retrieve authoritative payment evidence without initiating a charge."""

    @abstractmethod
    def refund(self, refund: Any) -> str:
        """Request a refund; return its provider reference, not a success assumption."""
