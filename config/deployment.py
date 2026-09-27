"""Validate deployment inputs without generating secrets or exposing their values."""

import base64
import binascii
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured


def production_secret(value: str) -> str:
    """Return a stable Django secret, or raise ImproperlyConfigured for unsafe input.

    Existing 50+ character secrets are preserved. Render generates a base64
    encoding of 32 random bytes: losslessly re-encode these as 64 hex characters
    to satisfy Django's length heuristic while preserving all 256 bits of entropy.
    No randomness is generated on startup, so web and Celery use the same key.
    """
    error = ImproperlyConfigured(
        "DJANGO_SECRET_KEY is missing or unsafe. Use Render generateValue: true "
        "(a base64-encoded 32-byte random key), or a random secret of at least "
        "50 characters. Never use a sample value from documentation."
    )
    if (
        not value
        or value != value.strip()
        or len(set(value)) < 5
        or value.lower().startswith(
            ("local-only", "replace", "change-me", "changeme", "django-insecure-")
        )
    ):
        raise error
    if len(value) >= 50:
        return value
    try:
        raw = base64.b64decode(value, altchars=b"-_", validate=True)
    except (ValueError, binascii.Error):
        raise error from None
    # Check canonical encoding to reject truncated/padded or merely similar input.
    canonical = {
        base64.b64encode(raw).decode("ascii"),
        base64.urlsafe_b64encode(raw).decode("ascii"),
    }
    if len(raw) != 32 or value not in canonical or len(set(raw)) < 5:
        raise error
    return raw.hex()


def https_origin(value: str) -> str:
    """Validate a configured public origin and return its hostname.

    Args: value is the public SITE_URL, without an application path.
    Returns: hostname used for Django's explicit allowlist.
    Raises: ImproperlyConfigured if the origin is malformed or not HTTPS.
    """
    try:
        parsed = urlsplit(value)
        port = parsed.port
        valid = (
            parsed.scheme == "https"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
            and "*" not in value
            and not any(char.isspace() for char in value)
            and (port is None or 1 <= port <= 65535)
        )
    except ValueError:
        valid = False
    if not valid:
        raise ImproperlyConfigured(
            "SITE_URL must be an HTTPS origin without a path or credentials."
        )
    return parsed.hostname
