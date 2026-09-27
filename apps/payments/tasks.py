"""Durable provider-event processing and five-minute fallback reconciliation."""

from datetime import timedelta
from decimal import Decimal
from typing import Any

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.core.security import unseal

from .models import (
    MerchantAccount,
    Payment,
    ReconciliationItem,
    ReconciliationRun,
    Refund,
    WebhookEvent,
)
from .services.lifecycle import complete_refund, reconcile


def process_event(event: Any) -> None:
    """Resolve a verified event to a merchant-scoped payment and fetch final state."""
    data = unseal(event.encrypted_payload_key)
    obj = (
        data.get("data", {}).get("object", {})
        if event.gateway == "stripe"
        else data.get("resource", data)
    )
    reference = (
        obj.get("metadata", {}).get("payment_reference")
        or obj.get("client_reference_id")
        or obj.get("custom_id")
        or obj.get("reference")
    )
    payment = (
        Payment.objects.filter(merchant_account=event.merchant_account, reference=reference).first()
        if reference
        else None
    )
    if not payment and event.gateway == "stripe" and obj.get("object") == "checkout.session":
        payment = Payment.objects.filter(
            merchant_account=event.merchant_account, gateway_ref=obj["id"]
        ).first()
    if not payment and event.gateway == "paypal":
        order = obj.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
        payment = (
            Payment.objects.filter(
                merchant_account=event.merchant_account, gateway_ref=order
            ).first()
            if order
            else None
        )
    if "refund" in event.event_type.lower():
        refs = [x["id"] for x in obj.get("refunds", {}).get("data", [])] or [obj.get("id")]
        for row in Refund.objects.filter(
            payment__merchant_account=event.merchant_account, gateway_ref__in=refs
        ):
            # Fetch refund status rather than inferring success from the event name.
            if event.gateway == "stripe":
                import stripe
                from django.conf import settings

                evidence = stripe.Refund.retrieve(
                    row.gateway_ref,
                    api_key=settings.STRIPE_SECRET_KEY,
                    stripe_account=event.merchant_account.external_account_id,
                )
                if (
                    evidence.status == "succeeded"
                    and evidence.amount == int(row.payer_refund_total * 100)
                    and evidence.currency.upper() == row.payer_currency_id
                ):
                    complete_refund(row.pk)
            elif event.gateway == "paypal":
                from .services.gateways.paypal import PayPalGateway

                evidence = PayPalGateway().call("GET", "/v2/payments/refunds/" + row.gateway_ref)
                if (
                    evidence["status"] == "COMPLETED"
                    and Decimal(evidence["amount"]["value"]) == row.payer_refund_total
                    and evidence["amount"]["currency_code"] == row.payer_currency_id
                ):
                    complete_refund(row.pk)
        return
    if not payment:
        raise ValueError("Payment not yet available for this event.")
    if not payment.gateway_ref:
        raise ValueError("Provider creation has not finished.")
    reconcile(payment)
    event.payment = payment
    event.save(update_fields=["payment"])


@shared_task
def process_events() -> int:
    """Retry event processing safely; retain failed events for operator review."""
    from django.db.models import Q

    ids = list(
        WebhookEvent.objects.filter(processing_status__in=["received", "retry"])
        .filter(Q(next_retry_at=None) | Q(next_retry_at__lte=timezone.now()))
        .values_list("pk", flat=True)[:100]
    )
    processed = 0
    for pk in ids:
        with transaction.atomic():
            event = WebhookEvent.objects.select_for_update().get(pk=pk)
            if event.processing_status == "processed":
                continue
            event.attempt_count += 1
            try:
                with transaction.atomic():
                    process_event(event)
            except Exception as exc:
                event.processing_status = "dead_letter" if event.attempt_count >= 12 else "retry"
                event.error_code = type(exc).__name__
                event.next_retry_at = timezone.now() + timedelta(
                    seconds=min(3600, 2**event.attempt_count * 10)
                )
            else:
                event.processing_status = "processed"
                event.processed_at = timezone.now()
                processed += 1
            event.save()
    return processed


@shared_task
def reconcile_pending() -> int:
    """Poll pending orders and record finance exceptions without inventing settlement."""
    count = 0
    for merchant in MerchantAccount.objects.filter(owner_kind="school", status="enabled"):
        if ReconciliationRun.objects.filter(merchant_account=merchant, status="running").exists():
            continue
        run = ReconciliationRun.objects.create(
            merchant_account=merchant,
            period_start=timezone.now() - timedelta(days=7),
            period_end=timezone.now(),
        )
        for payment in Payment.objects.filter(
            merchant_account=merchant, status__in=["created", "pending", "review", "succeeded"]
        )[:200]:
            try:
                if not payment.gateway_ref:
                    raise ValueError("No provider reference; manual reconciliation required.")
                reconcile(payment)
                count += 1
                payment.refresh_from_db()
                if payment.succeeded_at:
                    from .services.settlement import check_settlement

                    check_settlement(run, payment)
            except Exception as exc:
                ReconciliationItem.objects.get_or_create(
                    run=run,
                    source_reference=payment.reference,
                    issue_type="missing_provider",
                    defaults={
                        "payment": payment,
                        "expected_amount": payment.amount,
                        "currency": payment.currency,
                        "resolution_note": type(exc).__name__,
                    },
                )
        run.status = "completed"
        run.finished_at = timezone.now()
        run.counts = {"polled": count}
        run.save()
    return count
