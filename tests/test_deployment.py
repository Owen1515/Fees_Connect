"""Regression coverage for the reported Render boot error and deployment wiring."""

import base64
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError

from config.deployment import https_origin, production_secret
from deployment import start

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("encoder", [base64.b64encode, base64.urlsafe_b64encode])
def test_render_generated_key_preserves_entropy_and_identity(encoder):
    """The exact 44-character Render format converts losslessly and consistently."""
    raw = secrets.token_bytes(32)
    encoded = encoder(raw).decode()
    key = production_secret(encoded)
    assert len(encoded) == 44
    assert len(key) == 64
    assert bytes.fromhex(key) == raw
    assert production_secret(encoded) == key


def test_existing_long_secret_is_not_rotated():
    """A valid manually installed secret retains existing Django signatures."""
    existing = secrets.token_urlsafe(48)
    assert production_secret(existing) == existing


@pytest.mark.parametrize(
    "value",
    [
        "",
        "short",
        "a" * 64,
        "replace-with-a-random-secret-of-at-least-50-characters",
        "local-only-replace-this-before-deployment-1234567890",
        base64.b64encode(bytes(32)).decode(),
        base64.b64encode(secrets.token_bytes(24)).decode(),
        " " + secrets.token_urlsafe(48),
    ],
)
def test_missing_weak_and_placeholder_keys_rejected(value):
    """Compatibility must never introduce fallback or per-process generated keys."""
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        production_secret(value)


@pytest.mark.parametrize(
    "url",
    [
        "http://feesconnect.com",
        "https://user:pw@example.com",
        "https://feesconnect.com/path",
        "https://feesconnect.com:bad",
        "https://*.onrender.com",
    ],
)
def test_unsafe_public_origins_rejected(url):
    """Email/gateway URLs cannot silently become HTTP, credentialled or wildcard URLs."""
    with pytest.raises(ImproperlyConfigured, match="SITE_URL"):
        https_origin(url)


def test_production_settings_start_with_render_key(tmp_path):
    """Load the real production module in a clean process and check host/proxy settings."""
    raw = secrets.token_bytes(32)
    environment = os.environ | {
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "DJANGO_SECRET_KEY": base64.b64encode(raw).decode(),
        "DATA_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "MS_TENANT_ID": "local-test-tenant",
        "MS_CLIENT_ID": "local-test-client",
        "MS_CLIENT_SECRET": "local-test-value",
        "SENTRY_DSN": "",
        "DATABASE_URL": "postgresql://test:test@127.0.0.1:1/test",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "SITE_URL": "https://feesconnect-actual.onrender.com",
        "RENDER_EXTERNAL_HOSTNAME": "feesconnect-actual.onrender.com",
        "DJANGO_ALLOWED_HOSTS": "feesconnect.com,www.feesconnect.com",
        "TRUST_PROXY_HEADERS": "false",
        "STATIC_ROOT": str(tmp_path),
    }
    code = """
import django, json
django.setup()
from django.conf import settings
from django.test import Client
c = Client(HTTP_HOST='feesconnect-actual.onrender.com')
assert c.get('/healthz/').status_code == 200
assert c.get('/').status_code == 301
assert c.get('/readyz/').status_code == 503
print(json.dumps({'key': settings.SECRET_KEY, 'hosts': settings.ALLOWED_HOSTS,
                 'origins': settings.CSRF_TRUSTED_ORIGINS,
                 'trust_ip': settings.TRUST_PROXY_HEADERS, 'debug': settings.DEBUG}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout.strip().splitlines()[-1])
    assert data["key"] == raw.hex()
    assert "feesconnect-actual.onrender.com" in data["hosts"]
    assert "https://feesconnect-actual.onrender.com" in data["origins"]
    assert not data["debug"] and not data["trust_ip"]
    # Missing provider credentials produce a configuration error, never a dummy backend.
    environment["MS_CLIENT_ID"] = ""
    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0 and "MS_CLIENT_ID" in result.stderr
    assert environment["MS_CLIENT_SECRET"] not in result.stderr


def test_blueprint_uses_the_docker_startup_path():
    """Every service references the corrected image/roles and shares runtime secrets."""
    blueprint = yaml.safe_load((ROOT / "render.yaml").read_text())
    services = {service["name"]: service for service in blueprint["services"]}
    web = services["feesconnect-web"]
    assert web["preDeployCommand"] == "python deployment/start.py release"
    assert web["healthCheckPath"] == "/readyz/"
    for name, role in [
        ("feesconnect-web", "web"),
        ("feesconnect-worker", "worker"),
        ("feesconnect-beat", "beat"),
    ]:
        service = services[name]
        assert service["runtime"] == "docker"
        assert service["dockerCommand"] == f"python deployment/start.py {role}"
        assert "buildCommand" not in service and "startCommand" not in service
        variables = {entry["key"]: entry for entry in service["envVars"]}
        assert variables["REDIS_URL"]["fromService"]["type"] == "keyvalue"
        if role != "web":
            for key in [
                "DJANGO_SECRET_KEY",
                "DATA_ENCRYPTION_KEY",
                "MS_TENANT_ID",
                "MS_CLIENT_ID",
                "MS_CLIENT_SECRET",
                "SITE_URL",
            ]:
                assert variables[key]["fromService"]["envVarKey"] == key
    assert services["feesconnect-redis"]["maxmemoryPolicy"] == "noeviction"


def test_port_and_role_selection(monkeypatch):
    """Render's dynamic PORT is honoured without shell interpolation."""
    monkeypatch.setenv("PORT", "10000")
    assert "0.0.0.0:10000" in start.command_for("web")
    assert "worker" in start.command_for("worker")
    assert "beat" in start.command_for("beat")
    monkeypatch.setenv("PORT", "bad;command")
    with pytest.raises(ValueError, match="PORT"):
        start.command_for("web")
    with pytest.raises(ValueError, match="role"):
        start.command_for("invalid")


def test_only_release_applies_migrations(monkeypatch):
    """Starting replicas waits for migrations; only the pre-deploy role mutates schema."""
    calls = []
    monkeypatch.setattr(start, "manage", lambda *args: calls.append(args))
    monkeypatch.setattr(start.os, "chdir", lambda path: None)
    monkeypatch.setattr(start.os, "execvp", lambda *args: None)
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "config.settings.prod")
    monkeypatch.setattr(sys, "argv", ["start.py", "release"])
    start.main()
    assert ("migrate", "--noinput") in calls
    calls.clear()
    monkeypatch.setattr(sys, "argv", ["start.py", "worker"])
    start.main()
    assert len(calls) == 1 and "--require-migrations" in calls[0]


def test_build_settings_cannot_start_a_server(monkeypatch):
    """A credentials-free build profile must never be used for runtime requests."""
    monkeypatch.setattr(start.os, "chdir", lambda path: None)
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "config.settings.build")
    with pytest.raises(ValueError, match="runtime"):
        start.main()


@pytest.mark.django_db
def test_wait_for_services_checks_schema():
    """The readiness gate succeeds on the fully migrated isolated test database."""
    call_command("wait_for_services", timeout=1, require_migrations=True)


def test_wait_has_finite_deadline_and_redacts_connection_error(monkeypatch):
    """Startup exits with actionable context without disclosing driver error secrets."""
    from apps.core.management.commands import wait_for_services as wait

    connection = MagicMock()
    connection.cursor.side_effect = RuntimeError("password=do-not-print-this")
    monkeypatch.setattr(wait, "connection", connection)
    monkeypatch.setattr(wait.time, "monotonic", iter([0, 2]).__next__)
    with pytest.raises(CommandError) as exc:
        call_command("wait_for_services", timeout=1)
    assert "timed out" in str(exc.value)
    assert "do-not-print-this" not in str(exc.value)
