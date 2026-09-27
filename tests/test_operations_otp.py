"""Operational commands, OTP enforcement and database portability checks."""

import io
import json
from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.core.models import ImportRow
from apps.fees.models import School, Student


def code(device):
    """Generate the current test authenticator response using the real OTP algorithm."""
    return str(
        totp(
            device.bin_key, step=device.step, t0=device.t0, digits=device.digits, drift=device.drift
        )
    )


def test_otp_enrolment_login_and_replay(world, client, settings):
    """Enrolment requires proof and login requires a fresh OTP or recovery token."""
    client.force_login(world["user"])
    assert client.get("/accounts/2fa/setup/").status_code == 200
    device = TOTPDevice.objects.get(user=world["user"])
    response = client.post("/accounts/2fa/setup/", {"token": code(device)})
    assert response.status_code == 200 and len(response.context["codes"]) == 10
    recovery = response.context["codes"][0]
    client.post("/accounts/logout/")
    response = client.post(
        "/accounts/login/", {"username": world["user"].email, "password": "Complex-passphrase-581!"}
    )
    assert response.url == "/accounts/2fa/verify/"
    assert client.get("/account/").status_code == 302
    assert client.post("/accounts/2fa/verify/", {"token": "invalid"}).status_code == 200
    from datetime import timedelta

    from django_otp.plugins.otp_static.models import StaticDevice

    StaticDevice.objects.filter(user=world["user"]).update(
        throttling_failure_timestamp=timezone.now() - timedelta(seconds=5)
    )
    assert client.post("/accounts/2fa/verify/", {"token": recovery}).status_code == 302
    assert client.get("/account/").status_code == 200
    client.post("/accounts/logout/")
    client.post(
        "/accounts/login/", {"username": world["user"].email, "password": "Complex-passphrase-581!"}
    )
    assert client.post("/accounts/2fa/verify/", {"token": recovery}).status_code == 200


def test_privileged_otp_enforcement(world, client, settings):
    """A privileged password-only session cannot enter the operations site."""
    settings.ENFORCE_ADMIN_2FA = True
    world["user"].is_staff = True
    world["user"].save()
    client.force_login(world["user"])
    assert client.get("/admin/").url == "/accounts/2fa/setup/"


def test_reference_data_schema_and_migration(world, tmp_path):
    """Reference setup is repeatable and pupil import is atomic and idempotent."""
    operator = world["other"]
    operator.is_superuser = True
    operator.save()
    call_command("bootstrap", stdout=io.StringIO())
    call_command("bootstrap", stdout=io.StringIO())
    out = io.StringIO()
    call_command("export_schema", stdout=out)
    assert len(json.loads(out.getvalue())) == 39
    path = tmp_path / "students.csv"
    path.write_text("admission_number,full_name,class_label\nB2,Second Pupil,Form 1\n")
    args = {"school": world["school"].code, "operator": operator.email, "stdout": io.StringIO()}
    call_command("import_students", str(path), **args)
    assert not Student.objects.filter(admission_number="B2").exists()
    call_command("import_students", str(path), commit=True, **args)
    call_command("import_students", str(path), commit=True, **args)
    assert Student.objects.filter(admission_number="B2").count() == 1
    assert ImportRow.objects.count() == 1
    school = School.objects.create(
        code="NEW",
        legal_name="New",
        display_name="New",
        requested_by=world["user"],
        contact_email="new@example.test",
    )
    call_command(
        "approve_school",
        "NEW",
        operator=operator.email,
        admin_email=world["user"].email,
        stdout=io.StringIO(),
    )
    school.refresh_from_db()
    assert school.status == "approved"


def test_local_worker_and_test_email(world):
    """A developer can verify asynchronous mail without a running broker."""
    from django.core import mail

    call_command("send_test_email", world["user"].email, stdout=io.StringIO())
    call_command("process_jobs", stdout=io.StringIO())
    assert len(mail.outbox) == 1


def test_health_failure(client):
    """Readiness signals dependency failure without returning exception details."""
    with patch("apps.core.views.cache.set", side_effect=OSError):
        response = client.get("/readyz/")
        assert response.status_code == 503
