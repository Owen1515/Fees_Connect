"""PayPal Orders v2 and Payments v2 over bounded HTTPS requests."""

from decimal import Decimal
from typing import Any

import requests
from django.conf import settings
from django.urls import reverse

from .base import CapabilityError, GatewayResult, PaymentGateway


class PayPalGateway(PaymentGateway):
    """Use approved multiparty seller accounts and an explicit platform fee."""

    @property
    def base(self) -> str:
        """Select sandbox unless the entire deployment is explicitly live."""
        return (
            "https://api-m.paypal.com"
            if settings.PAYMENT_ENVIRONMENT == "live"
            else "https://api-m.sandbox.paypal.com"
        )

    def call(self, method: str, path: str, body: Any = None, key: str = "") -> dict:
        """Acquire OAuth credentials and perform one bounded provider API request."""
        token = requests.post(
            self.base + "/v1/oauth2/token",
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=20,
        )
        token.raise_for_status()
        headers = {
            "Authorization": "Bearer " + token.json()["access_token"],
            "Content-Type": "application/json",
        }
        if key:
            headers["PayPal-Request-Id"] = key
        if settings.PAYPAL_PARTNER_ID:
            headers["PayPal-Partner-Attribution-Id"] = settings.PAYPAL_PARTNER_ID
        result = requests.request(
            method, self.base + path, json=body, headers=headers, timeout=25, allow_redirects=False
        )
        result.raise_for_status()
        return result.json()

    def create(self, payment: Any) -> GatewayResult:
        """Create a seller-scoped order with the agreed platform fee split."""
        if payment.currency_id != payment.principal_currency_id:
            raise CapabilityError(
                "Executable cross-currency pricing requires a contracted FX route."
            )
        quote = payment.quote
        fee = quote.settlement_plan["platform_amount"]
        result = self.call(
            "POST",
            "/v2/checkout/orders",
            {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": payment.reference,
                        "custom_id": payment.reference,
                        "amount": {
                            "currency_code": payment.currency_id,
                            "value": str(payment.amount),
                        },
                        "payee": {"merchant_id": payment.merchant_account.external_account_id},
                        "payment_instruction": {
                            "disbursement_mode": "INSTANT",
                            "platform_fees": [
                                {"amount": {"currency_code": payment.currency_id, "value": fee}}
                            ],
                        },
                    }
                ],
                "payment_source": {
                    "paypal": {
                        "experience_context": {
                            "return_url": settings.SITE_URL
                            + reverse("payments:status", args=[payment.pk]),
                            "cancel_url": settings.SITE_URL
                            + reverse("payments:status", args=[payment.pk]),
                            "user_action": "PAY_NOW",
                        }
                    }
                },
            },
            payment.idempotency_key,
        )
        url = next(
            (x["href"] for x in result["links"] if x["rel"] in ["approve", "payer-action"]), ""
        )
        return GatewayResult(result["id"], "pending", payment.amount, payment.currency_id, url)

    def poll(self, payment: Any) -> GatewayResult:
        """Capture only a provider-approved order; retries reuse the capture key."""
        result = self.call("GET", "/v2/checkout/orders/" + payment.gateway_ref)
        if result["status"] == "APPROVED":
            result = self.call(
                "POST",
                "/v2/checkout/orders/" + payment.gateway_ref + "/capture",
                {},
                "capture:" + payment.idempotency_key,
            )
        unit = result["purchase_units"][0]
        captures = unit.get("payments", {}).get("captures", [])
        paid = captures and captures[0]["status"] == "COMPLETED"
        amount = captures[0]["amount"] if captures else unit["amount"]
        return GatewayResult(
            payment.gateway_ref,
            "succeeded" if paid else "pending",
            Decimal(amount["value"]),
            amount["currency_code"],
        )

    def refund(self, refund: Any) -> str:
        """Submit a capture refund with a stable request ID."""
        payment = refund.payment
        order = self.call("GET", "/v2/checkout/orders/" + payment.gateway_ref)
        capture = order["purchase_units"][0]["payments"]["captures"][0]["id"]
        result = self.call(
            "POST",
            "/v2/payments/captures/" + capture + "/refund",
            {
                "amount": {
                    "currency_code": refund.payer_currency_id,
                    "value": str(refund.payer_refund_total),
                }
            },
            refund.idempotency_key,
        )
        return result["id"]
