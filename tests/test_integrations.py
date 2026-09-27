"""Provider, OAuth, outbox and reconciliation tests with bounded mocked transport."""

import json
from decimal import Decimal
from unittest.mock import Mock, patch
from urllib.parse import urlencode

import pytest
from django.utils import timezone

from apps.core.models import OutboxMessage
from apps.core.security import seal
from apps.core.services import queue_email
from apps.core.tasks import dispatch_outbox
from apps.payments.models import PaymentAttempt, ReconciliationItem, WebhookEvent
from apps.payments.services.checkout import create_payment, quote
from apps.payments.services.gateways.base import CapabilityError, GatewayError, GatewayResult
from apps.payments.services.gateways.paynow import PaynowGateway, digest, safe_url, verified
from apps.payments.services.gateways.paypal import PayPalGateway
from apps.payments.services.gateways.stripe import StripeGateway
from apps.payments.services.lifecycle import apply_success, initiate


@pytest.fixture
def payment(world):
    """Create a reserved sandbox payment with a real immutable quote."""
    q = quote(world["user"], world["invoice"].pk, "40", world["merchant"].pk, "card", "USD")
    return create_payment(world["user"], q.pk, "gateway-test")


def signed(values, key="key"):
    """Build signed provider fixtures using a known integration test key."""
    return urlencode({**values, "hash": digest(values, key)})


@pytest.mark.parametrize(
    "url",
    [
        "http://www.paynow.co.zw/a",
        "https://evil.test/",
        "https://www.paynow.co.zw.evil.test/",
        "https://user@www.paynow.co.zw/a",
        "https://www.paynow.co.zw:8443/a",
    ],
)
def test_paynow_ssrf(url):
    """Poll endpoints must remain on the exact trusted HTTPS provider host."""
    with pytest.raises(GatewayError):
        safe_url(url)


def test_paynow_signature_tampering():
    """Hash verification rejects tampered amounts, duplicates and unsigned updates."""
    raw = signed({"reference": "FC-1", "amount": "103.00", "status": "paid"})
    assert verified(raw, "key")["amount"] == "103.00"
    for bad in [raw.replace("103.00", "104.00"), raw + "&amount=1", "status=paid"]:
        with pytest.raises(GatewayError):
            verified(bad, "key")


def test_stripe_creation_poll_and_refund(world, payment):
    """Stripe receives the full customer total and fee exactly once under account scope."""
    adapter = StripeGateway()
    with (
        patch("stripe.Customer.create", return_value=Mock(id="cus_1")) as customer,
        patch(
            "stripe.checkout.Session.create",
            return_value=Mock(id="cs_1", url="https://checkout.stripe.com/a"),
        ) as create,
    ):
        result = adapter.create(payment)
        assert result.reference == "cs_1"
        assert create.call_args.kwargs["payment_intent_data"]["application_fee_amount"] == 120
        assert create.call_args.kwargs["stripe_account"] == "acct_school"
        adapter.create(payment)
        assert customer.call_count == 1
    payment.gateway_ref = "cs_1"
    payment.save()
    session = Mock(
        payment_status="paid",
        status="complete",
        amount_total=4120,
        currency="usd",
        payment_intent="pi_1",
    )
    with patch("stripe.checkout.Session.retrieve", return_value=session):
        assert adapter.poll(payment).status == "succeeded"
        refund = Mock(payment=payment, payer_refund_total=Decimal("10.30"), idempotency_key="rf")
        with patch("stripe.Refund.create", return_value=Mock(id="re_1")):
            assert adapter.refund(refund) == "re_1"


def test_paypal_transport_and_flow(payment):
    """PayPal requests use OAuth and merchant-scoped purchase units and capture IDs."""
    adapter = PayPalGateway()
    token = Mock()
    token.json.return_value = {"access_token": "token"}
    response = Mock()
    response.json.return_value = {"id": "order"}
    with (
        patch("requests.post", return_value=token),
        patch("requests.request", return_value=response) as request,
    ):
        assert adapter.call("POST", "/test", {}, "idem")["id"] == "order"
        assert request.call_args.kwargs["timeout"] == 25
    with patch.object(
        adapter,
        "call",
        return_value={
            "id": "order",
            "links": [{"rel": "approve", "href": "https://www.paypal.com/a"}],
        },
    ) as call:
        assert adapter.create(payment).reference == "order"
        assert call.call_args.args[2]["purchase_units"][0]["payee"]["merchant_id"] == "acct_school"
    payment.gateway_ref = "order"
    order = {
        "status": "APPROVED",
        "purchase_units": [{"amount": {"value": "41.20", "currency_code": "USD"}}],
    }
    captured = {
        "status": "COMPLETED",
        "purchase_units": [
            {
                "payments": {
                    "captures": [
                        {
                            "id": "capture",
                            "status": "COMPLETED",
                            "amount": {"value": "41.20", "currency_code": "USD"},
                        }
                    ]
                }
            }
        ],
    }
    with patch.object(adapter, "call", side_effect=[order, captured]):
        assert adapter.poll(payment).status == "succeeded"
    with patch.object(adapter, "call", side_effect=[captured, {"id": "refund"}]):
        assert (
            adapter.refund(
                Mock(
                    payment=payment,
                    payer_currency_id="USD",
                    payer_refund_total=Decimal("10.30"),
                    idempotency_key="rf",
                )
            )
            == "refund"
        )


def test_paynow_sandbox_and_poll(world, payment, monkeypatch):
    """The SDK-based sandbox flow verifies initiation and polling signatures."""
    adapter = PaynowGateway()
    world["merchant"].credential_secret_ref = "TEST_PAYNOW"
    world["merchant"].save()
    payment.refresh_from_db()
    monkeypatch.setenv("TEST_PAYNOW", "key")
    response = Mock()
    response.text = signed(
        {
            "status": "Ok",
            "browserurl": "https://www.paynow.co.zw/payment/1",
            "pollurl": "https://www.paynow.co.zw/interface/checkpayment/1",
        }
    )
    with patch("requests.post", return_value=response):
        result = adapter.create(payment)
    assert result.poll_url.startswith("https:")
    PaymentAttempt.objects.create(
        payment=payment,
        attempt_number=1,
        provider_idempotency_key="k",
        request_digest="d",
        encrypted_poll_url=seal(result.poll_url),
    )
    response.text = signed(
        {
            "reference": payment.reference,
            "amount": "41.20",
            "status": "paid",
            "paynowreference": "1",
        }
    )
    with patch("requests.post", return_value=response):
        assert adapter.poll(payment).status == "succeeded"
    payment.merchant_account.environment = "live"
    with pytest.raises(CapabilityError):
        adapter.create(payment)
    with pytest.raises(CapabilityError):
        adapter.refund(Mock())


def test_webhook_auth_and_replay(world, payment, client, monkeypatch):
    """Authenticated duplicate provider events persist once; bad signatures fail."""
    from apps.payments.tasks import process_events

    payment.gateway_ref = "cs_1"
    payment.save()
    event = {
        "id": "evt_1",
        "type": "payment_intent.succeeded",
        "account": "acct_school",
        "data": {"object": {"metadata": {"payment_reference": payment.reference}}},
    }
    obj = Mock()
    obj.get.side_effect = event.get
    obj.id = "evt_1"
    obj.type = event["type"]
    obj.to_dict_recursive.return_value = event
    with patch("stripe.Webhook.construct_event", return_value=obj):
        assert (
            client.post(
                "/payments/webhooks/stripe/", json.dumps(event), content_type="application/json"
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/payments/webhooks/stripe/", json.dumps(event), content_type="application/json"
            ).status_code
            == 200
        )
    assert WebhookEvent.objects.count() == 1
    with patch("apps.payments.services.lifecycle.gateway") as adapter:
        adapter.return_value.poll.return_value = GatewayResult(
            "cs_1", "succeeded", payment.amount, "USD"
        )
        assert process_events() == 1
        assert process_events() == 0
    assert (
        client.post(
            "/payments/webhooks/stripe/", b"bad", content_type="application/json"
        ).status_code
        == 400
    )
    merchant = world["merchant"]
    merchant.gateway = "paynow"
    merchant.credential_secret_ref = "TEST_PAYNOW"
    merchant.save()
    monkeypatch.setenv("TEST_PAYNOW", "key")
    url = f"/payments/webhooks/paynow/{merchant.pk}/"
    assert (
        client.post(
            url,
            signed({"reference": payment.reference, "amount": "41.20", "status": "paid"}),
            content_type="application/x-www-form-urlencoded",
        ).status_code
        == 200
    )
    assert (
        client.post(url, "amount=1", content_type="application/x-www-form-urlencoded").status_code
        == 400
    )


def test_paypal_verified_webhook(payment, client):
    """PayPal callback acceptance depends on successful remote signature verification."""
    payment.gateway = "paypal"
    payment.gateway_ref = "order"
    payment.save()
    event = {
        "id": "WH-1",
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {"custom_id": payment.reference, "payee": {"merchant_id": "acct_school"}},
    }
    with patch.object(PayPalGateway, "call", return_value={"verification_status": "SUCCESS"}):
        assert (
            client.post(
                "/payments/webhooks/paypal/", json.dumps(event), content_type="application/json"
            ).status_code
            == 200
        )
    with patch.object(PayPalGateway, "call", return_value={"verification_status": "FAILURE"}):
        assert (
            client.post(
                "/payments/webhooks/paypal/", json.dumps(event), content_type="application/json"
            ).status_code
            == 400
        )


def test_worker_email_receipt_and_retry(world, payment):
    """Confirmed payments generate one receipt attachment; transient mail failures retry."""
    from django.core import mail

    OutboxMessage.objects.filter(kind="task").delete()
    apply_success(payment.pk, payment.amount, "USD")
    assert dispatch_outbox() == 1
    assert mail.outbox[-1].attachments[0].mimetype == "application/pdf"
    row = queue_email(world["user"], "test", {}, "test1")
    with patch("django.core.mail.message.EmailMultiAlternatives.send", side_effect=OSError):
        assert dispatch_outbox() == 0
    row.refresh_from_db()
    assert row.state == "retry"
    row.next_attempt_at = timezone.now()
    row.save()
    assert dispatch_outbox() == 1


def test_unknown_creation_not_recharged(payment):
    """A timeout cannot cause a second debit on worker retry."""
    with patch("apps.payments.services.lifecycle.gateway") as adapter:
        adapter.return_value.create.side_effect = TimeoutError
        initiate(payment.pk)
        initiate(payment.pk)
        assert adapter.return_value.create.call_count == 1
    assert PaymentAttempt.objects.get(payment=payment).state == "unknown"


def test_reconciliation_records_exception(world, payment):
    """Missing provider references become finance exceptions, not successful payments."""
    from apps.payments.tasks import reconcile_pending

    assert reconcile_pending() == 0
    assert ReconciliationItem.objects.filter(payment=payment).exists()


def test_oauth_smtp_uses_tls_and_xoauth(settings):
    """SMTP cannot silently fall back to a password or plaintext connection."""
    from apps.core.email import OAuthSMTPBackend

    settings.MS_TENANT_ID = "tenant"
    settings.MS_CLIENT_ID = "client"
    settings.MS_CLIENT_SECRET = "secret"
    with patch("msal.ConfidentialClientApplication") as msal, patch("smtplib.SMTP") as smtp:
        msal.return_value.acquire_token_for_client.return_value = {"access_token": "token"}
        smtp.return_value.docmd.return_value = (235, b"ok")
        backend = OAuthSMTPBackend()
        assert backend.open()
        assert smtp.return_value.starttls.called
        assert smtp.return_value.docmd.call_args.args[1].startswith("XOAUTH2 ")
        assert not backend.open()
    with patch("msal.ConfidentialClientApplication") as msal:
        msal.return_value.acquire_token_for_client.return_value = {"error": "denied"}
        with pytest.raises(RuntimeError):
            OAuthSMTPBackend().open()
