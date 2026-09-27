from typing import Any

from django.contrib.auth import get_user_model

"""Server-side quoting, balance reservations and idempotent payment creation."""
import hashlib
import json
import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.accounts.access import invoices_for
from apps.core.models import OutboxMessage
from apps.core.security import seal
from apps.core.services import audit
from apps.fees.models import Invoice
from apps.fees.services import balance
from apps.payments.models import (
    FeePolicy,
    FXQuote,
    InvoiceReservation,
    MerchantAccount,
    Payment,
    PaymentQuote,
)

from .gateways.base import CapabilityError

CENT = Decimal("0.01")


def money(value: Any) -> Decimal:
    """Validate user-supplied decimal money without silently rounding extra digits."""
    try:
        amount = Decimal(str(value))
    except Exception as exc:
        raise ValueError("Enter a valid amount.") from exc
    if (
        not amount.is_finite()
        or amount <= 0
        or amount > Decimal("10000000")
        or amount != amount.quantize(CENT)
    ):
        raise ValueError("Enter a positive amount with at most two decimal places.")
    return amount


@transaction.atomic
def quote(
    user: Any,
    invoice_id: Any,
    amount: Any,
    merchant_id: Any,
    method: str,
    payer_currency: str,
    fx_id: Any = None,
) -> Any:
    """Create an immutable price; validate tenant, currency and merchant capabilities."""
    invoice = invoices_for(user, "pay").select_related("school").get(pk=invoice_id)
    if invoice.status != "issued" or invoice.school.status != "approved":
        raise ValueError("Invoice is not payable.")
    principal = money(amount)
    if principal > balance(invoice):
        raise ValueError("Amount exceeds the outstanding balance.")
    merchant = MerchantAccount.objects.get(
        pk=merchant_id,
        school=invoice.school,
        status="enabled",
        settlement_currency=invoice.currency,
    )
    caps = merchant.verified_capabilities
    if merchant.gateway == "stripe" and merchant.fee_bearer != "platform":
        raise CapabilityError("Stripe processing fees must be assigned to FeesConnect.")
    if merchant.environment != settings.PAYMENT_ENVIRONMENT or method not in caps.get(
        "methods", []
    ):
        raise CapabilityError("Payment method is unavailable.")
    if merchant.environment == "live" and (
        not caps.get("split_verified") or not merchant.verified_at
    ):
        raise CapabilityError("Direct split settlement is not verified.")
    platform = MerchantAccount.objects.get(
        owner_kind="platform",
        gateway=merchant.gateway,
        environment=merchant.environment,
        status="enabled",
        settlement_currency=invoice.currency,
    )
    policy = (
        FeePolicy.objects.filter(effective_from__lte=timezone.now(), approved_at__isnull=False)
        .order_by("-version")
        .first()
    )
    if not policy or (policy.effective_until and policy.effective_until <= timezone.now()):
        raise CapabilityError("Approved fee policy is required.")
    charge = (principal * Decimal("0.03")).quantize(CENT, rounding=ROUND_HALF_UP)
    total = principal + charge
    expected_cost = (
        total * Decimal(str(caps.get("cost_rate", "0"))) + Decimal(str(caps.get("cost_fixed", "0")))
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    if merchant.environment == "live" and "cost_rate" not in caps:
        raise CapabilityError("Provider pricing must be configured.")
    if expected_cost > charge:
        raise CapabilityError("This route exceeds the agreed 3% charge.")
    if payer_currency != invoice.currency_id:
        FXQuote.objects.get(
            pk=fx_id,
            merchant_account=merchant,
            source_currency=invoice.currency,
            payer_currency_id=payer_currency,
            source_amount=total,
            executable=True,
            expires_at__gt=timezone.now(),
        )
        # No configured default adapter promises a rate it cannot execute.
        raise CapabilityError("No contracted executable FX adapter is configured yet.")
    platform_amount = charge if merchant.gateway == "stripe" else charge - expected_cost
    payload = {
        "invoice": str(invoice.pk),
        "principal": str(principal),
        "merchant": str(merchant.pk),
        "method": method,
        "currency": payer_currency,
    }
    return PaymentQuote.objects.create(
        user=user,
        invoice=invoice,
        school_merchant=merchant,
        platform_merchant=platform,
        policy=policy,
        principal_amount=principal,
        charge_amount=charge,
        invoice_currency=invoice.currency,
        payer_amount=total,
        payer_currency_id=payer_currency,
        expected_provider_cost=expected_cost,
        expected_cost_currency=invoice.currency,
        expected_platform_margin=charge - expected_cost,
        expected_margin_currency=invoice.currency,
        payment_method=method,
        settlement_plan={"platform_amount": str(platform_amount), "school_amount": str(principal)},
        capabilities_version=merchant.capabilities_version,
        expires_at=timezone.now() + timedelta(minutes=10),
        request_digest=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
    )


@transaction.atomic
def create_payment(user: Any, quote_id: Any, key: str, phone: str = "") -> Payment:
    """Reserve invoice principal once; repeated identical requests return the same payment."""
    if not settings.PAYMENTS_ENABLED:
        raise CapabilityError("Payments are not enabled yet.")
    if not key or len(key) > 128:
        raise ValueError("A valid idempotency key is required.")
    import re

    if phone and not re.fullmatch(r"\+?[0-9]{7,15}", phone):
        raise ValueError("Invalid mobile number.")
    selected = PaymentQuote.objects.select_for_update().get(pk=quote_id, user=user)
    if selected.payment_method in ["ecocash", "onemoney"] and not phone:
        raise ValueError("Mobile number required.")
    # Lock the payer before checking a key across different quote IDs.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    existing = Payment.objects.filter(user=user, idempotency_key=key).first()
    if existing:
        if existing.quote_id != selected.pk:
            raise ValueError("Idempotency key was already used for another request.")
        return existing
    if Payment.objects.filter(quote=selected).exists():
        raise ValueError("This quote already has a payment. Check payment history.")
    if selected.expires_at <= timezone.now():
        raise ValueError("Quote expired. Review a new quote.")
    invoice = (
        Invoice.objects.select_for_update().select_related("school").get(pk=selected.invoice_id)
    )
    if invoice.status != "issued" or invoice.school.status != "approved":
        raise CapabilityError("The school or invoice is no longer available for payment.")
    if not invoices_for(user, "pay").filter(pk=invoice.pk).exists():
        raise PermissionDenied
    if (
        selected.school_merchant.status != "enabled"
        or selected.school_merchant.capabilities_version != selected.capabilities_version
    ):
        raise CapabilityError("Merchant configuration changed; request a new quote.")
    active = InvoiceReservation.objects.filter(
        invoice=invoice, status="active", expires_at__gt=timezone.now()
    )
    reserved = sum((row.principal_amount for row in active), Decimal("0"))
    if selected.principal_amount > balance(invoice) - reserved:
        raise ValueError("Another payment is already covering this balance.")
    payment = Payment.objects.create(
        user=user,
        invoice=invoice,
        quote=selected,
        school=invoice.school,
        merchant_account=selected.school_merchant,
        reference="FC-" + uuid.uuid4().hex.upper(),
        amount=selected.payer_amount,
        currency=selected.payer_currency,
        principal_amount=selected.principal_amount,
        principal_currency=selected.invoice_currency,
        charge_amount=selected.charge_amount,
        charge_currency=selected.invoice_currency,
        gateway=selected.school_merchant.gateway,
        idempotency_key=key,
        request_digest=selected.request_digest,
        metadata={"phone": phone},
    )
    selected.accepted_at = timezone.now()
    selected.save(update_fields=["accepted_at"])
    InvoiceReservation.objects.create(
        invoice=invoice,
        payment=payment,
        principal_amount=selected.principal_amount,
        currency=invoice.currency,
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    OutboxMessage.objects.create(
        kind="task",
        topic="initiate_payment",
        dedupe_key="initiate:" + str(payment.pk),
        encrypted_payload_key=seal({"payment_id": str(payment.pk)}),
        next_attempt_at=timezone.now(),
    )
    audit(user, "payment_created", payment, invoice.school)
    return payment
