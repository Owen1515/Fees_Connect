"""Financial invariants and authorisation tests use service boundaries."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.access import invoices_for
from apps.fees.services import balance, request_student_link
from apps.payments.models import PaymentAllocation, Receipt
from apps.payments.services.checkout import create_payment, money, quote
from apps.payments.services.gateways.base import CapabilityError, GatewayError, GatewayResult
from apps.payments.services.lifecycle import (
    apply_failure,
    apply_success,
    complete_refund,
    initiate,
    request_refund,
)


@pytest.fixture
def payment(world):
    """Create an actual service-generated payment without contacting a provider."""
    q = quote(world["user"], world["invoice"].pk, "40", world["merchant"].pk, "card", "USD")
    return create_payment(world["user"], q.pk, "test-key")


def test_charge_and_partial_balance(world, payment):
    """Only fee principal reduces the invoice; the customer pays the 3% charge."""
    assert payment.amount == Decimal("41.20")
    apply_success(payment.pk, Decimal("41.20"), "USD")
    assert balance(world["invoice"]) == Decimal("60")
    apply_success(payment.pk, Decimal("41.20"), "USD")
    assert PaymentAllocation.objects.count() == 1
    assert Receipt.objects.count() == 1
    apply_failure(payment.pk, "late_failure")
    payment.refresh_from_db()
    assert payment.status == "succeeded"


def test_idempotency_and_reservation(world, payment):
    """Retries return the same payment; competing requests cannot overallocate."""
    assert create_payment(world["user"], payment.quote_id, "test-key").pk == payment.pk
    q = quote(world["user"], world["invoice"].pk, "70", world["merchant"].pk, "card", "USD")
    with pytest.raises(ValueError):
        create_payment(world["user"], q.pk, "other-key")
    with pytest.raises(ValueError):
        create_payment(world["user"], q.pk, "test-key")


def test_scope_currency_and_amount(world, payment):
    """Foreign users and mismatched provider amounts cannot alter fee records."""
    assert not invoices_for(world["other"]).exists()
    with pytest.raises(GatewayError):
        apply_success(payment.pk, Decimal("40"), "USD")
    with pytest.raises(GatewayError):
        apply_success(payment.pk, payment.amount, "EUR")
    assert not PaymentAllocation.objects.exists()


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "0", "1.001", "10000001", "wrong"])
def test_invalid_money(value):
    """Reject malformed values, excessive precision and non-finite decimals."""
    with pytest.raises(ValueError):
        money(value)


def test_expiry_and_overpriced_route(world):
    """Expired quotes and costs exceeding 3% fail before any charge request."""
    q = quote(world["user"], world["invoice"].pk, "10", world["merchant"].pk, "card", "USD")
    q.expires_at = timezone.now() - timedelta(seconds=1)
    q.save()
    with pytest.raises(ValueError):
        create_payment(world["user"], q.pk, "expired")
    world["merchant"].verified_capabilities = {"methods": ["card"], "cost_rate": "0.10"}
    world["merchant"].save()
    with pytest.raises(CapabilityError):
        quote(world["user"], world["invoice"].pk, "10", world["merchant"].pk, "card", "USD")


def test_refund_once(world, payment):
    """Refund reservation and completion cannot refund more than was captured."""
    apply_success(payment.pk, payment.amount, "USD")
    operator = world["other"]
    operator.is_superuser = True
    operator.save()
    refund = request_refund(operator, payment.pk, Decimal("20"), "Requested by payer")
    assert refund.payer_refund_total == Decimal("20.60")
    complete_refund(refund.pk)
    complete_refund(refund.pk)
    assert balance(world["invoice"]) == Decimal("80")
    with pytest.raises(ValueError):
        request_refund(operator, payment.pk, Decimal("30"), "Too much")


def test_late_success_surplus(world, payment):
    """Late captures are recorded but do not reduce an invoice below zero."""
    world["invoice"].total_amount = Decimal("20")
    world["invoice"].save()
    apply_success(payment.pk, payment.amount, "USD")
    payment.refresh_from_db()
    assert balance(world["invoice"]) == 0
    assert "surplus" in payment.review_reason


def test_async_creation_once(world, payment):
    """Worker retries do not create additional provider transactions."""
    result = GatewayResult(
        "cs_test", "pending", payment.amount, "USD", "https://checkout.stripe.com/c/test"
    )
    with patch("apps.payments.services.lifecycle.gateway") as adapter:
        adapter.return_value.create.return_value = result
        initiate(payment.pk)
        initiate(payment.pk)
        assert adapter.return_value.create.call_count == 1
    payment.refresh_from_db()
    assert payment.gateway_ref == "cs_test"


def test_student_claim_does_not_expose_existing_data(world, client):
    """A submitted admission number is not proof of student ownership."""
    request_student_link(world["other"], world["school"], "A1", "Fake name", "self")
    assert not invoices_for(world["other"]).exists()
    world["student"].refresh_from_db()
    assert world["student"].full_name == "Pupil"
    client.force_login(world["other"])
    assert client.get(reverse("fees:invoice", args=[world["invoice"].pk])).status_code == 404
