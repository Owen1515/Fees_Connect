"""Shared isolated fixtures; external providers are mocked in tests."""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import Currency
from apps.fees.models import Invoice, InvoiceLine, School, Student, StudentAccess
from apps.payments.models import FeePolicy, MerchantAccount


@pytest.fixture(autouse=True)
def environment(settings, tmp_path):
    """Avoid real email, caches, gateways and private-file cross-test leakage."""
    settings.ENFORCE_ADMIN_2FA = False
    settings.PAYMENTS_ENABLED = True
    settings.STORAGES["default"] = {"BACKEND": "django.core.files.storage.InMemoryStorage"}
    from django.core.cache import cache

    cache.clear()


@pytest.fixture
def world(db):
    """Create a verified payer, school, pupil and supported sandbox route."""
    usd = Currency.objects.create(code="USD", display_name="US dollar", symbol="$")
    user = User.objects.create_user(
        "parent@example.com",
        "Complex-passphrase-581!",
        full_name="Parent",
        email_verified_at=timezone.now(),
    )
    other = User.objects.create_user(
        "other@example.com",
        "Complex-passphrase-582!",
        full_name="Other",
        email_verified_at=timezone.now(),
    )
    school = School.objects.create(
        code="SCHOOL",
        legal_name="School",
        display_name="School",
        contact_email="school@example.com",
        status="approved",
        requested_by=other,
    )
    school.supported_currencies.add(usd)
    student = Student.objects.create(
        school=school, admission_number="A1", full_name="Pupil", status="active"
    )
    link = StudentAccess.objects.create(
        user=user, student=student, relationship="parent", status="approved"
    )
    invoice = Invoice.objects.create(
        school=school,
        student=student,
        number="INV-1",
        currency=usd,
        total_amount=Decimal("100"),
        status="issued",
    )
    InvoiceLine.objects.create(
        invoice=invoice,
        position=1,
        description_snapshot="Tuition",
        quantity=1,
        unit_amount=100,
        line_amount=100,
    )
    merchant = MerchantAccount.objects.create(
        owner_kind="school",
        school=school,
        gateway="stripe",
        external_account_id="acct_school",
        settlement_currency=usd,
        status="enabled",
        verified_at=timezone.now(),
        verified_capabilities={"methods": ["card"], "cost_rate": "0.02", "cost_fixed": "0"},
        fee_bearer="platform",
    )
    platform = MerchantAccount.objects.create(
        owner_kind="platform",
        gateway="stripe",
        external_account_id="acct_platform",
        settlement_currency=usd,
        status="enabled",
    )
    policy = FeePolicy.objects.create(version=1, approved_at=timezone.now())
    return locals()
