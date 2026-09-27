"""Paynow SDK payment objects with hardened signed HTTP transport.

The pinned SDK does not verify poll hashes or set network timeouts. This adapter
uses its payment object and verifies every successful HTTP response itself.
"""

import hashlib
import hmac
import os
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import requests
from django.conf import settings
from django.urls import reverse
from paynow import Paynow

from apps.core.security import unseal

from .base import CapabilityError, GatewayError, GatewayResult, PaymentGateway


def digest(values: dict, key: str) -> str:
    """Hash ordered decoded Paynow values with the lowercase integration key."""
    content = "".join(str(v) for k, v in values.items() if k.lower() != "hash") + key.lower()
    return hashlib.sha512(content.encode()).hexdigest().upper()


def verified(raw: str, key: str) -> dict:
    """Reject duplicate keys, missing hashes and mismatched signed responses."""
    pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
    if len({k.lower() for k, v in pairs}) != len(pairs):
        raise GatewayError("Duplicate Paynow fields.")
    values = dict(pairs)
    supplied = values.get("hash", "")
    if not supplied or not hmac.compare_digest(supplied.upper(), digest(values, key)):
        raise GatewayError("Invalid Paynow signature.")
    return values


def safe_url(url: str) -> str:
    """Prevent provider callback/poll URLs from becoming an SSRF channel."""
    part = urlsplit(url)
    if (
        part.scheme != "https"
        or part.hostname != "www.paynow.co.zw"
        or part.port not in [None, 443]
        or part.username
        or part.password
    ):
        raise GatewayError("Untrusted Paynow URL.")
    return url


class PaynowGateway(PaymentGateway):
    """Hosted/mobile payments; automatic split collection requires a provider contract."""

    def key(self, payment: Any) -> str:
        """Resolve the per-school integration secret from environment only."""
        key = os.environ.get(payment.merchant_account.credential_secret_ref, "")
        if not key:
            raise CapabilityError("School Paynow credentials are not configured.")
        return key

    def create(self, payment: Any) -> GatewayResult:
        """Run Paynow sandbox flows; do not pretend ordinary API supports splitting."""
        if payment.merchant_account.environment == "live":
            raise CapabilityError(
                "Paynow automatic split API contract must be integrated before live activation."
            )
        if payment.currency_id != payment.principal_currency_id:
            raise CapabilityError("This Paynow route does not execute FX quotes.")
        key = self.key(payment)
        sdk = Paynow(
            payment.merchant_account.external_account_id,
            key,
            settings.SITE_URL + reverse("payments:status", args=[payment.pk]),
            settings.SITE_URL
            + reverse("payments:paynow_webhook", args=[payment.merchant_account_id]),
        )
        obj = sdk.create_payment(payment.reference, payment.user.email)
        obj.add("School fees and transaction charge", payment.amount)
        values = {
            "resulturl": sdk.result_url,
            "returnurl": sdk.return_url,
            "reference": obj.reference,
            "amount": str(obj.total()),
            "id": sdk.integration_id,
            "additionalinfo": "School fee payment",
            "authemail": obj.auth_email,
            "status": "Message",
        }
        mobile = payment.quote.payment_method in ["ecocash", "onemoney"]
        if mobile:
            values.update(
                phone=payment.metadata.get("phone", ""), method=payment.quote.payment_method
            )
        values["hash"] = digest(values, key)
        url = sdk.URL_INITIATE_MOBILE_TRANSACTION if mobile else sdk.URL_INITIATE_TRANSACTION
        response = requests.post(url, data=values, timeout=25, allow_redirects=False)
        response.raise_for_status()
        result = verified(response.text, key)
        if result.get("status", "").lower() != "ok":
            raise GatewayError("Paynow did not accept the request.")
        return GatewayResult(
            result.get("paynowreference", payment.reference),
            "pending",
            payment.amount,
            payment.currency_id,
            safe_url(result["browserurl"]) if result.get("browserurl") else "",
            safe_url(result["pollurl"]),
        )

    def poll(self, payment: Any) -> GatewayResult:
        """Reconcile signed Paynow status and match the merchant-side reference."""
        from apps.payments.models import PaymentAttempt

        attempt = PaymentAttempt.objects.filter(payment=payment).latest("attempt_number")
        url = safe_url(unseal(attempt.encrypted_poll_url))
        response = requests.post(url, data={}, timeout=25, allow_redirects=False)
        response.raise_for_status()
        values = verified(response.text, self.key(payment))
        if values.get("reference") != payment.reference:
            raise GatewayError("Paynow reference mismatch.")
        status = values.get("status", "").lower()
        state = (
            "succeeded"
            if status in ["paid", "awaiting delivery", "delivered"]
            else "failed" if status in ["cancelled", "failed"] else "pending"
        )
        return GatewayResult(
            payment.gateway_ref, state, Decimal(values["amount"]), payment.currency_id
        )

    def refund(self, refund: Any) -> str:
        """Refuse an undocumented refund API; an operator must use provider support."""
        raise CapabilityError(
            "Paynow API refunds require the merchant-specific provider contract; use audited manual reconciliation."
        )
