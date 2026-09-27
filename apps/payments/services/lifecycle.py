"""Trusted provider state transitions; never mark paid from a redirect."""

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.core.security import seal
from apps.core.services import audit, queue_email
from apps.fees.models import Invoice
from apps.fees.services import balance
from apps.payments.models import (
    AllocationAdjustment,
    InvoiceReservation,
    Payment,
    PaymentAllocation,
    PaymentAttempt,
    Receipt,
    Refund,
)

from .gateways import gateway
from .gateways.base import GatewayError


def initiate(payment_id: Any) -> None:
    """Claim creation once; uncertain outcomes require polling, never blind retry."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment_id)
        if payment.status != "created":
            return
        payment.status = "pending"
        payment.save(update_fields=["status"])
        attempt = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            provider_idempotency_key=payment.idempotency_key + ":" + str(payment.user_id),
            state="submitting",
            submitted_at=timezone.now(),
            request_digest=payment.request_digest,
        )
    try:
        result = gateway(payment.gateway).create(payment)
    except Exception as exc:
        attempt.state = "unknown"
        attempt.error_code = type(exc).__name__
        attempt.save()
        # A declined capability is known not to have initiated a debit.
        from .gateways.base import CapabilityError

        if isinstance(exc, CapabilityError):
            apply_failure(payment.pk, "configuration_unavailable")
        else:
            Payment.objects.filter(pk=payment.pk).update(
                review_reason="Creation outcome unknown; reconcile before retry."
            )
        return
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        payment.gateway_ref = result.reference
        payment.metadata = {**payment.metadata, "redirect_url": result.redirect_url}
        payment.save()
        attempt.state = "pending"
        attempt.provider_reference = result.reference
        attempt.encrypted_poll_url = seal(result.poll_url) if result.poll_url else None
        attempt.save()
        queue_email(
            payment.user,
            "payment_pending",
            {"reference": payment.reference},
            "pending:" + str(payment.pk),
        )


@transaction.atomic
def apply_success(payment_id: Any, amount: Decimal, currency: str) -> None:
    """Allocate principal once after verifying gross payer amount and currency."""
    payment = (
        Payment.objects.select_for_update().select_related("invoice", "user").get(pk=payment_id)
    )
    if payment.amount != amount or payment.currency_id != currency:
        raise GatewayError("Provider amount or currency mismatch.")
    if payment.succeeded_at:
        return
    invoice = Invoice.objects.select_for_update().get(pk=payment.invoice_id)
    applicable = max(Decimal("0"), min(payment.principal_amount, balance(invoice)))
    if applicable > 0:
        PaymentAllocation.objects.create(
            payment=payment,
            invoice=invoice,
            principal_amount=applicable,
            currency=invoice.currency,
            source_key="paid:" + str(payment.pk),
            allocated_at=timezone.now(),
        )
    payment.status = "succeeded"
    payment.succeeded_at = timezone.now()
    if applicable < payment.principal_amount:
        payment.review_reason = "Unapplied surplus requires finance reconciliation."
    payment.save()
    InvoiceReservation.objects.filter(payment=payment).update(status="consumed")
    receipt, _ = Receipt.objects.get_or_create(
        payment=payment,
        defaults={
            "number": "R-" + payment.reference,
            "immutable_snapshot": {
                "school": invoice.school.display_name,
                "student": invoice.student.full_name,
                "invoice": invoice.number,
                "principal": str(payment.principal_amount),
                "charge": str(payment.charge_amount),
                "amount": str(payment.amount),
                "currency": payment.currency_id,
                "principal_currency": payment.principal_currency_id,
                "reference": payment.reference,
                "allocated": str(applicable),
                "outstanding": str(balance(invoice)),
            },
        },
    )
    queue_email(
        payment.user,
        "payment_success",
        {"reference": payment.reference, "receipt_id": str(receipt.pk)},
        "paid:" + str(payment.pk),
    )
    audit(payment.user, "payment_succeeded", payment, payment.school)


@transaction.atomic
def apply_failure(payment_id: Any, reason: str) -> None:
    """Record final failure only when no successful capture has been recorded."""
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    if payment.succeeded_at:
        return
    payment.status = "failed"
    payment.review_reason = reason
    payment.save()
    InvoiceReservation.objects.filter(payment=payment).update(status="released")
    queue_email(
        payment.user,
        "payment_failed",
        {"reference": payment.reference},
        "failed:" + str(payment.pk),
    )


def reconcile(payment: Any) -> None:
    """Poll authoritative state; paid/refunded state cannot regress on stale events."""
    if not payment.gateway_ref:
        return
    result = gateway(payment.gateway).poll(payment)
    if result.status == "succeeded":
        apply_success(payment.pk, result.amount, result.currency)
    elif result.status == "failed":
        apply_failure(payment.pk, "provider_failed")


@transaction.atomic
def request_refund(actor: Any, payment_id: Any, principal: Decimal, reason: str) -> Any:
    """Reserve refundable principal after finance permission and scope checks."""
    from apps.accounts.access import is_operator

    from .checkout import money

    if not is_operator(actor):
        raise PermissionError("Platform finance approval is required.")
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    if not payment.succeeded_at:
        raise ValueError("Only confirmed payments can be refunded.")
    amount = money(principal)
    used = sum(
        (
            x.principal_amount
            for x in Refund.objects.filter(payment=payment).exclude(
                status__in=["failed", "rejected"]
            )
        ),
        Decimal("0"),
    )
    if amount > payment.principal_amount - used:
        raise ValueError("Refund exceeds refundable principal.")
    # Launch policy refunds proportional charges; full final refund absorbs cent rounding.
    proportion = amount / payment.principal_amount
    total = (payment.amount * proportion).quantize(Decimal(".01"))
    charge = (payment.charge_amount * proportion).quantize(Decimal(".01"))
    prior = Refund.objects.filter(payment=payment).exclude(status__in=["failed", "rejected"])
    if amount == payment.principal_amount - used:
        total = payment.amount - sum((r.payer_refund_total for r in prior), Decimal("0"))
        charge = payment.charge_amount - sum((r.charge_refund_amount for r in prior), Decimal("0"))
    import uuid

    key = uuid.uuid4().hex
    row = Refund.objects.create(
        payment=payment,
        reference="RF-" + key,
        requested_by=actor,
        approved_by=actor,
        principal_amount=amount,
        principal_currency=payment.principal_currency,
        payer_principal_amount=total - charge,
        charge_refund_amount=charge,
        payer_refund_total=total,
        payer_currency=payment.currency,
        status="approved",
        reason=reason,
        idempotency_key="refund:" + key,
        approved_at=timezone.now(),
    )
    from apps.core.models import OutboxMessage

    OutboxMessage.objects.create(
        kind="task",
        topic="refund",
        dedupe_key="refund:" + key,
        encrypted_payload_key=seal({"refund_id": str(row.pk)}),
        next_attempt_at=timezone.now(),
    )
    audit(actor, "refund_approved", row, payment.school)
    return row


def submit_refund(refund_id: Any) -> None:
    """Submit a reserved refund; completion waits for provider evidence."""
    with transaction.atomic():
        row = Refund.objects.select_for_update().get(pk=refund_id)
        if row.status != "approved":
            return
        row.status = "submitting"
        row.save()
    try:
        reference = gateway(row.payment.gateway).refund(row)
    except Exception as exc:
        row.status = "unknown"
        row.safe_metadata = {"error": type(exc).__name__}
        row.save()
        return
    row.gateway_ref = reference
    row.status = "pending"
    row.save()


@transaction.atomic
def complete_refund(refund_id: Any) -> None:
    """Apply a verified refund once and restore only originally allocated principal."""
    row = Refund.objects.select_for_update().select_related("payment").get(pk=refund_id)
    payment = Payment.objects.select_for_update().get(pk=row.payment_id)
    if row.status == "succeeded":
        return
    Invoice.objects.select_for_update().get(pk=payment.invoice_id)
    allocation = PaymentAllocation.objects.filter(payment=payment).first()
    if allocation:
        already = sum(
            (x.delta for x in AllocationAdjustment.objects.filter(allocation=allocation)),
            Decimal("0"),
        )
        remaining = allocation.principal_amount + already
        total_prior = sum(
            (
                r.principal_amount
                for r in Refund.objects.filter(payment=payment, status="succeeded")
            ),
            Decimal("0"),
        )
        surplus = max(
            Decimal("0"), payment.principal_amount - allocation.principal_amount - total_prior
        )
        restore = min(remaining, max(Decimal("0"), row.principal_amount - surplus))
        if restore:
            AllocationAdjustment.objects.create(
                allocation=allocation,
                refund=row,
                delta=-restore,
                reason="refund",
                source_key="refund:" + str(row.pk),
                effective_at=timezone.now(),
            )
    row.status = "succeeded"
    row.completed_at = timezone.now()
    row.save()
    total = sum(
        (r.principal_amount for r in Refund.objects.filter(payment=payment, status="succeeded")),
        Decimal("0"),
    )
    payment.status = "refunded" if total >= payment.principal_amount else "partially_refunded"
    payment.save()
    queue_email(
        payment.user, "refund", {"reference": row.reference}, "refund-complete:" + str(row.pk)
    )
    audit(row.approved_by, "refund_completed", row, payment.school)
