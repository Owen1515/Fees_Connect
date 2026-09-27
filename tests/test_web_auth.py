"""End-to-end Django form, template, permissions and account-token checks."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts import services
from apps.accounts.models import RoleAssignment, User
from apps.core.models import OutboxMessage
from apps.core.security import unseal
from apps.payments.services.lifecycle import apply_success


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/demo/",
        "/privacy/",
        "/terms/",
        "/contact/",
        "/healthz/",
        "/readyz/",
        "/accounts/register/",
        "/accounts/login/",
        "/accounts/password/reset/",
        "/accounts/verification/resend/",
        "/accounts/verification/sent/",
        "/accounts/verification/confirmed/",
        "/accounts/password/sent/",
        "/accounts/password/complete/",
        "/accounts/verify/test/",
        "/accounts/password/reset/test/",
    ],
)
def test_public_pages(client, path):
    """Every public/auth template is routed and renders without an exception."""
    assert client.get(path).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name",
    [
        "index",
        "home",
        "auth",
        "login",
        "register",
        "account",
        "demo",
        "privacy",
        "forgot-password",
        "resend-verification",
        "reset",
        "verify",
    ],
)
def test_uploaded_aliases(client, name):
    """Every uploaded HTML filename has a working canonical redirect."""
    assert client.get("/" + name + ".html").status_code == 302


@pytest.mark.parametrize(
    "path",
    [
        "/account/",
        "/accounts/profile/",
        "/accounts/password/change/",
        "/accounts/2fa/setup/",
        "/fees/",
        "/fees/students/register/",
        "/fees/schools/register/",
        "/payments/history/",
        "/payments/export/",
        "/payments/reconciliation/",
        "/support/",
    ],
)
def test_authenticated_pages(world, client, path):
    """All ordinary authenticated pages render with the uploaded brand shell."""
    client.force_login(world["user"])
    assert client.get(path).status_code == 200


def test_registration_verify_reset(world, client):
    """Tokens are delivered asynchronously, consumed once and invalidate prior sessions."""
    response = client.post(
        "/accounts/register/",
        {
            "email": "new@example.com",
            "full_name": "New Parent",
            "role": "parent",
            "password": "Unique-passphrase-7385!",
            "confirm_password": "Unique-passphrase-7385!",
            "agree": "on",
        },
    )
    assert response.status_code == 302
    user = User.objects.get(email="new@example.com")
    assert not user.email_verified_at
    email = OutboxMessage.objects.get(user=user, topic="verification")
    link = unseal(email.encrypted_payload_key)["link"]
    token = link.rstrip("/").split("/")[-1]
    assert client.get("/accounts/verify/" + token + "/").status_code == 200
    user.refresh_from_db()
    assert not user.email_verified_at
    assert client.post("/accounts/verify/" + token + "/").status_code == 302
    with pytest.raises(ValueError):
        services.consume_token(token, "verification")
    assert (
        client.post(
            "/accounts/login/", {"username": user.email, "password": "Unique-passphrase-7385!"}
        ).status_code
        == 302
    )
    assert client.get("/account/").status_code == 200
    client.post("/accounts/password/reset/", {"email": user.email})
    email = OutboxMessage.objects.filter(user=user, topic="password_reset").latest("created_at")
    reset = unseal(email.encrypted_payload_key)["link"].rstrip("/").split("/")[-1]
    assert (
        client.post(
            "/accounts/password/reset/" + reset + "/",
            {"password": "Another-passphrase-582!", "confirm_password": "Another-passphrase-582!"},
        ).status_code
        == 302
    )
    assert client.get("/account/").status_code == 302
    assert client.get("/accounts/logout/").status_code == 405


def test_form_validation_and_enumeration(world, client):
    """Weak/mismatched passwords fail, and duplicate registration has the same response."""
    bad = client.post(
        "/accounts/register/",
        {
            "email": "bad@example.com",
            "full_name": "Bad",
            "role": "parent",
            "password": "x",
            "confirm_password": "y",
            "agree": "on",
        },
    )
    assert bad.status_code == 200 and not User.objects.filter(email="bad@example.com").exists()
    services.register(world["user"].email, "Duplicate", "Complex-passphrase-333!", "parent")
    assert User.objects.filter(email=world["user"].email).count() == 1
    with pytest.raises(ValueError):
        services.register("a@b.com", "A", "Complex-passphrase-333!", "super_admin")
    assert (
        client.post("/accounts/password/reset/", {"email": "absent@example.com"}).status_code == 302
    )
    assert (
        client.post("/accounts/verification/resend/", {"email": world["user"].email}).status_code
        == 302
    )


def test_profile_password_and_csrf(world, client):
    """Profile edits do not grant roles; password change signs the account out."""
    client.force_login(world["user"])
    assert (
        client.post(
            "/accounts/profile/",
            {"full_name": "Updated", "phone": "12345678", "is_superuser": "on"},
        ).status_code
        == 302
    )
    world["user"].refresh_from_db()
    assert not world["user"].is_superuser
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(world["user"])
    assert csrf_client.post("/accounts/logout/").status_code == 403
    response = client.post(
        "/accounts/password/change/",
        {
            "old_password": "Complex-passphrase-581!",
            "new_password1": "Different-Strong-Pass-871!",
            "new_password2": "Different-Strong-Pass-871!",
        },
    )
    assert response.status_code == 302 and client.get("/account/").status_code == 302


def test_invoice_payment_pages_and_private_pdf(world, client):
    """Quote/confirm/status/receipt/download form one connected server-side flow."""
    client.force_login(world["user"])
    invoice = world["invoice"]
    assert client.get(reverse("fees:invoice", args=[invoice.pk])).status_code == 200
    assert client.get(reverse("fees:invoice_pdf", args=[invoice.pk])).content.startswith(b"%PDF")
    path = reverse("payments:checkout", args=[invoice.pk])
    assert client.get(path).status_code == 200
    response = client.post(
        path,
        {
            "amount": "40",
            "merchant": str(world["merchant"].pk),
            "method": "card",
            "currency": "USD",
        },
    )
    assert response.status_code == 200
    selected = response.context["quote"]
    response = client.post(path, {"quote_id": str(selected.pk), "idempotency_key": "web-checkout"})
    from apps.payments.models import Payment

    payment = Payment.objects.get(quote=selected)
    assert response.status_code == 302
    assert client.get(reverse("payments:status", args=[payment.pk])).status_code == 200
    assert (
        client.get(reverse("payments:status_json", args=[payment.pk])).json()["status"] == "created"
    )
    apply_success(payment.pk, payment.amount, "USD")
    for name in ["status", "receipt", "receipt_pdf"]:
        response = client.get(reverse("payments:" + name, args=[payment.pk]))
        assert response.status_code == 200
    assert client.get("/payments/export/").status_code == 200
    client.force_login(world["other"])
    assert client.get(reverse("payments:receipt_pdf", args=[payment.pk])).status_code == 403


def test_support_and_api_scope(world, client):
    """Stable chat is idempotent, authenticated and does not leak other conversations."""
    assert client.post("/api/support/chat/", {}, content_type="application/json").status_code == 403
    client.force_login(world["user"])
    payload = {"message": "How do I pay fees?", "request_id": "turn-1"}
    response = client.post("/api/support/chat/", payload, content_type="application/json")
    assert response.status_code == 200
    again = client.post("/api/support/chat/", payload, content_type="application/json")
    assert again.json() == response.json()
    conv = response.json()["conversation_id"]
    assert (
        client.post(
            "/api/support/chat/",
            {"message": "receipt", "request_id": "turn-2", "conversation_id": conv},
            content_type="application/json",
        ).status_code
        == 200
    )
    assert client.get("/api/payments/").status_code == 200
    assert client.get("/api/invoices/").json()[0]["number"] == "INV-1"
    response = client.post(
        "/support/", {"subject": "Question", "body": "Please help with an invoice."}
    )
    assert response.status_code == 302 and client.get(response.url).status_code == 200
    client.force_login(world["other"])
    assert client.get(response.url).status_code == 404
    assert (
        client.post(
            "/api/support/chat/",
            {"message": "hello", "request_id": "x", "conversation_id": conv},
            content_type="application/json",
        ).status_code
        == 404
    )


def test_student_school_workflow(world, client):
    """Verified school admins approve pupil links and issue invoices in their scope."""
    from django.contrib.auth.models import Group

    from apps.fees.models import StudentAccess

    client.force_login(world["other"])
    assert (
        client.post(
            "/fees/students/register/",
            {
                "school": str(world["school"].pk),
                "admission_number": "B2",
                "full_name": "Another Pupil",
                "relationship": "self",
            },
        ).status_code
        == 302
    )
    group = Group.objects.create(name="school_admin")
    RoleAssignment.objects.create(user=world["user"], group=group, school=world["school"])
    client.force_login(world["user"])
    assert client.get("/fees/schools/manage/").status_code == 200
    link = StudentAccess.objects.get(user=world["other"])
    assert client.post("/fees/schools/manage/", {"link_id": str(link.pk)}).status_code == 302
    assert (
        client.post(
            "/fees/invoices/new/",
            {
                "student_id": str(link.student_id),
                "number": "INV-2",
                "description": "Tuition",
                "amount": "50",
                "currency": "USD",
                "due_on": "2027-01-01",
            },
        ).status_code
        == 302
    )
    assert (
        client.post(
            "/fees/schools/register/",
            {
                "legal_name": "New school",
                "display_name": "New school",
                "registration_number": "REG",
                "contact_email": "a@school.test",
                "address": "Address",
            },
        ).status_code
        == 302
    )


def test_error_pages_and_otp_redirect(world, client):
    """Errors use site templates and OTP rejects anonymous bypass attempts."""
    from django.contrib.auth.models import AnonymousUser
    from django.test import RequestFactory

    from apps.core.views import error403, error404, error500

    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    assert error403(request).status_code == 403
    assert error404(request).status_code == 404
    assert error500(request).status_code == 500
    assert client.get("/accounts/2fa/verify/").status_code == 302
