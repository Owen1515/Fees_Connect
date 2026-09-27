"""Stripe Checkout direct charges using the official pinned Python SDK."""

from decimal import Decimal
from typing import Any

import stripe
from django.conf import settings
from django.urls import reverse

from .base import CapabilityError, GatewayResult, PaymentGateway


class StripeGateway(PaymentGateway):
    """Use connected school accounts with platform-paid processing fees."""

    def options(self, payment: Any) -> dict:
        """Scope every SDK request to the correct school merchant account."""
        return {
            "api_key": settings.STRIPE_SECRET_KEY,
            "stripe_account": payment.merchant_account.external_account_id,
        }

    def create(self, payment: Any) -> GatewayResult:
        """Create a single-use hosted checkout without handling card details."""
        if payment.currency_id != payment.principal_currency_id:
            raise CapabilityError(
                "Executable cross-currency pricing requires a contracted FX route."
            )
        from apps.payments.models import GatewayCustomer

        opts = self.options(payment)
        customer = GatewayCustomer.objects.filter(
            user=payment.user, merchant_account=payment.merchant_account
        ).first()
        if not customer:
            result = stripe.Customer.create(
                email=payment.user.email,
                idempotency_key=f"customer:{payment.user_id}:{payment.merchant_account_id}",
                **opts,
            )
            customer, _ = GatewayCustomer.objects.get_or_create(
                user=payment.user,
                merchant_account=payment.merchant_account,
                defaults={"external_customer_id": result.id},
            )
        result = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=(
                ["sepa_debit"] if payment.quote.payment_method == "sepa_debit" else ["card"]
            ),
            customer=customer.external_customer_id,
            line_items=[
                {
                    "price_data": {
                        "currency": payment.currency_id.lower(),
                        "unit_amount": int(payment.amount * 100),
                        "product_data": {"name": "School fees including 3% transaction charge"},
                    },
                    "quantity": 1,
                }
            ],
            payment_intent_data={
                "application_fee_amount": int(payment.charge_amount * 100),
                "metadata": {"payment_reference": payment.reference},
            },
            client_reference_id=payment.reference,
            success_url=settings.SITE_URL + reverse("payments:status", args=[payment.pk]),
            cancel_url=settings.SITE_URL + reverse("payments:status", args=[payment.pk]),
            idempotency_key=payment.idempotency_key,
            **opts,
        )
        return GatewayResult(result.id, "pending", payment.amount, payment.currency_id, result.url)

    def poll(self, payment: Any) -> GatewayResult:
        """Resolve Checkout's payment intent and trust only the provider amount."""
        session = stripe.checkout.Session.retrieve(
            payment.gateway_ref, expand=["payment_intent"], **self.options(payment)
        )
        state = (
            "succeeded"
            if session.payment_status == "paid"
            else "failed" if session.status == "expired" else "pending"
        )
        return GatewayResult(
            session.id, state, Decimal(session.amount_total) / 100, session.currency.upper()
        )

    def refund(self, refund: Any) -> str:
        """Refund principal and the selected proportional application fee."""
        payment = refund.payment
        session = stripe.checkout.Session.retrieve(payment.gateway_ref, **self.options(payment))
        result = stripe.Refund.create(
            payment_intent=session.payment_intent,
            amount=int(refund.payer_refund_total * 100),
            refund_application_fee=True,
            idempotency_key=refund.idempotency_key,
            **self.options(payment),
        )
        return result.id
