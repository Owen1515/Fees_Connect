"""Encryption and bounded request throttling used by account and payment services."""

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest


def cipher() -> Fernet:
    """Return configured encryption; development derives a non-production key."""
    key = settings.DATA_ENCRYPTION_KEY
    if not key:
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def seal(value: dict | str) -> str:
    """Encrypt JSON so tokens and private provider payloads are opaque at rest."""
    return cipher().encrypt(json.dumps(value).encode()).decode()


def unseal(value: str) -> Any:
    """Decrypt an application-owned payload; invalid ciphertext raises InvalidToken."""
    return json.loads(cipher().decrypt(value.encode()))


def throttle(request: HttpRequest, scope: str, limit: int = 10) -> None:
    """Enforce a shared-cache fixed-window request limit; raise PermissionDenied."""
    digest = hashlib.sha256(str(request.META.get("REMOTE_ADDR", "")).encode()).hexdigest()
    key = f"limit:{scope}:{digest}"
    if cache.add(key, 1, 900):
        return
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, 900)
        count = 1
    if count > limit:
        raise PermissionDenied("Too many requests. Please try again later.")
