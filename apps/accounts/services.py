"""Account lifecycle with single-use tokens and deferred email delivery."""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.core.services import audit, queue_email

from .models import AccountToken, RoleAssignment, User


def issue_token(user: User, purpose: str) -> None:
    """Queue an expiring verification/reset link without storing its plaintext token."""
    raw = secrets.token_urlsafe(32)
    record = AccountToken.objects.create(
        user=user,
        purpose=purpose,
        token_digest=hashlib.sha256(raw.encode()).hexdigest(),
        email_snapshot=user.email,
        expires_at=timezone.now() + timedelta(hours=24 if purpose == "verification" else 1),
        issued_auth_version=user.auth_version,
    )
    name = "accounts:verify" if purpose == "verification" else "accounts:reset_confirm"
    queue_email(
        user,
        "verification" if purpose == "verification" else "password_reset",
        {"link": settings.SITE_URL + reverse(name, args=[raw])},
        f"token:{record.pk}",
    )


@transaction.atomic
def register(email: str, full_name: str, password: str, role: str) -> None:
    """Register a parent/student; privileged roles cannot be self-assigned."""
    if role not in {"parent", "student"}:
        raise ValueError("Choose parent or student.")
    if User.objects.filter(email__iexact=email).exists():
        return  # Keep registration responses independent of account existence.
    user = User(email=email.lower(), full_name=full_name)
    validate_password(password, user)
    user.set_password(password)
    user.save()
    group, _ = Group.objects.get_or_create(name=role)
    RoleAssignment.objects.create(user=user, group=group)
    issue_token(user, "verification")
    queue_email(user, "welcome", {}, f"welcome:{user.pk}")
    audit(user, "registered", user)


@transaction.atomic
def consume_token(raw: str, purpose: str, password: str | None = None) -> User:
    """Consume once and revoke sibling tokens; raise ValueError on invalid links."""
    record = (
        AccountToken.objects.select_for_update()
        .filter(token_digest=hashlib.sha256(raw.encode()).hexdigest(), purpose=purpose)
        .first()
    )
    if not record or record.consumed_at or record.revoked_at or record.expires_at <= timezone.now():
        raise ValueError("This link is invalid or has expired.")
    user = User.objects.select_for_update().get(pk=record.user_id)
    if record.email_snapshot != user.email or record.issued_auth_version != user.auth_version:
        raise ValueError("This link is no longer valid.")
    if purpose == "verification":
        user.email_verified_at = timezone.now()
    else:
        validate_password(password, user)
        user.set_password(password)
        user.auth_version += 1
    user.save()
    record.consumed_at = timezone.now()
    record.save(update_fields=["consumed_at"])
    AccountToken.objects.filter(user=user, purpose=purpose, consumed_at=None).update(
        revoked_at=timezone.now()
    )
    audit(user, purpose + "_completed", user)
    return user
