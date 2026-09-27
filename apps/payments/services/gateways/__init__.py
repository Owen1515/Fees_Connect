"""Registered gateway adapters; account registration remains an external process."""

from typing import Any

from .base import CapabilityError
from .paynow import PaynowGateway
from .paypal import PayPalGateway
from .stripe import StripeGateway

GATEWAYS = {"stripe": StripeGateway, "paypal": PayPalGateway, "paynow": PaynowGateway}


def gateway(name: str) -> Any:
    """Return a supported adapter or fail closed for unknown gateways."""
    if name not in GATEWAYS:
        raise CapabilityError("Gateway is not supported.")
    return GATEWAYS[name]()
