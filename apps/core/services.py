"""Durable audit and transactional notification creation."""

from typing import Any

from django.utils import timezone

from .models import AuditEvent, OutboxMessage
from .security import seal


def audit(
    actor: Any, action: str, target: Any = None, school: Any = None, changes: Any = None
) -> None:
    """Append a redacted event; callers pass only non-secret changes."""
    AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        actor_snapshot=str(getattr(actor, "pk", "system")),
        school=school,
        action=action,
        target_type=target.__class__.__name__ if target else "",
        target_id=str(target.pk) if target else "",
        correlation_id="",
        occurred_at=timezone.now(),
        redacted_changes=changes or {},
    )


def queue_email(
    user: Any, topic: str, context: dict, key: str, attachments: Any = None
) -> OutboxMessage:
    """Persist an email in the caller's transaction; workers deliver it later."""
    message, _ = OutboxMessage.objects.get_or_create(
        dedupe_key=key,
        defaults={
            "user": user,
            "topic": topic,
            "template_name": topic,
            "template_version": "1",
            "encrypted_payload_key": seal({"to": user.email, **context}),
            "attachment_keys": attachments or [],
            "next_attempt_at": timezone.now(),
        },
    )
    return message
