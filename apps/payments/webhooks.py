"""Public webhook endpoints authenticate provider messages before persistence."""

import hashlib
import json
import os
from typing import Any

import stripe
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.security import seal

from .models import MerchantAccount, WebhookEvent
from .services.gateways.paynow import verified
from .services.gateways.paypal import PayPalGateway


def store_event(merchant: Any, gateway: str, key: str, kind: str, payload: dict) -> None:
    """Persist only authenticated events; duplicate delivery has no new effect."""
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    WebhookEvent.objects.get_or_create(
        merchant_account=merchant,
        dedupe_key=key,
        defaults={
            "gateway": gateway,
            "external_event_id": key,
            "event_type": kind,
            "payload_digest": digest,
            "encrypted_payload_key": seal(payload),
        },
    )


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> Any:
    """Verify Stripe's signed raw body including timestamp tolerance."""
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.headers.get("Stripe-Signature", ""),
            settings.STRIPE_WEBHOOK_SECRET,
        )
        merchant = MerchantAccount.objects.get(
            gateway="stripe",
            owner_kind="school",
            external_account_id=event.get("account"),
            environment=settings.PAYMENT_ENVIRONMENT,
        )
        store_event(merchant, "stripe", event.id, event.type, event.to_dict_recursive())
    except Exception:
        return JsonResponse({"error": "Invalid event"}, status=400)
    return JsonResponse({"received": True})


@csrf_exempt
@require_POST
def paypal_webhook(request: HttpRequest) -> Any:
    """Verify PayPal transmission via its authenticated verification endpoint."""
    try:
        event = json.loads(request.body)
        result = PayPalGateway().call(
            "POST",
            "/v1/notifications/verify-webhook-signature",
            {
                "auth_algo": request.headers.get("Paypal-Auth-Algo"),
                "cert_url": request.headers.get("Paypal-Cert-Url"),
                "transmission_id": request.headers.get("Paypal-Transmission-Id"),
                "transmission_sig": request.headers.get("Paypal-Transmission-Sig"),
                "transmission_time": request.headers.get("Paypal-Transmission-Time"),
                "webhook_id": settings.PAYPAL_WEBHOOK_ID,
                "webhook_event": event,
            },
        )
        if result.get("verification_status") != "SUCCESS":
            raise ValueError
        resource = event["resource"]
        seller = resource.get("payee", {}).get("merchant_id")
        from .models import Payment

        reference = resource.get("custom_id")
        payment = (
            Payment.objects.filter(reference=reference, gateway="paypal").first()
            if reference
            else None
        )
        if not payment:
            order_id = resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
            payment = (
                Payment.objects.filter(gateway_ref=order_id, gateway="paypal").first()
                if order_id
                else None
            )
        if not payment and "REFUND" in event.get("event_type", ""):
            from .models import Refund

            refund = (
                Refund.objects.filter(gateway_ref=resource.get("id"), payment__gateway="paypal")
                .select_related("payment")
                .first()
            )
            payment = refund.payment if refund else None
        if not payment:
            raise ValueError
        merchant = payment.merchant_account
        if seller and seller != merchant.external_account_id:
            raise ValueError
        store_event(merchant, "paypal", event["id"], event["event_type"], event)
    except Exception:
        return JsonResponse({"error": "Invalid or unresolved event"}, status=400)
    return JsonResponse({"received": True})


@csrf_exempt
@require_POST
def paynow_webhook(request: HttpRequest, merchant_id: Any) -> Any:
    """Verify ordered Paynow values with the school-specific integration secret."""
    merchant = get_object_or_404(MerchantAccount, pk=merchant_id, gateway="paynow")
    try:
        key = os.environ.get(merchant.credential_secret_ref, "")
        if not key:
            raise ValueError
        values = verified(request.body.decode(), key)
        store_event(
            merchant,
            "paynow",
            hashlib.sha256(request.body).hexdigest(),
            values.get("status", "update"),
            values,
        )
    except Exception:
        return JsonResponse({"error": "Invalid event"}, status=400)
    return JsonResponse({"received": True})
