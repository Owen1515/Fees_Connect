"""Transactional outbox delivery with short leases and bounded retry backoff."""

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

from .models import OutboxMessage
from .security import unseal


def deliver(row: OutboxMessage) -> None:
    """Execute one durable command; provider outcomes have their own idempotency."""
    payload = unseal(row.encrypted_payload_key)
    if row.kind == "task":
        from apps.payments.services.lifecycle import initiate, submit_refund

        {"initiate_payment": initiate, "refund": submit_refund}[row.topic](**payload)
        return
    subject = {
        "welcome": "Welcome to FeesConnect",
        "verification": "Verify your FeesConnect email",
        "password_reset": "Reset your FeesConnect password",
        "payment_success": "Payment confirmed",
        "payment_failed": "Payment could not be completed",
        "payment_pending": "Payment awaiting confirmation",
        "refund": "Refund processed",
        "receipt": "Your FeesConnect receipt",
        "test": "FeesConnect test email",
        "support": "Support request received",
    }.get(row.topic, "FeesConnect account update")
    context = {"title": subject, "support_email": settings.SUPPORT_EMAIL, **payload}
    message = EmailMultiAlternatives(
        subject,
        render_to_string(f"emails/{row.topic}.txt", context),
        settings.DEFAULT_FROM_EMAIL,
        [payload["to"]],
        reply_to=[settings.SUPPORT_EMAIL],
        headers={"Message-ID": f"<{row.pk}@feesconnect.com>"},
    )
    message.attach_alternative(render_to_string(f"emails/{row.topic}.html", context), "text/html")
    if payload.get("receipt_id"):
        from apps.payments.models import Receipt
        from apps.payments.services.documents import receipt_pdf

        receipt = Receipt.objects.get(pk=payload["receipt_id"])
        message.attach(receipt.number + ".pdf", receipt_pdf(receipt), "application/pdf")
    from email.mime.image import MIMEImage

    logo_path = settings.BASE_DIR / "static/feesconnect/assets/feesconnect-logo.png"
    logo = MIMEImage(logo_path.read_bytes(), _subtype="png")
    logo.add_header("Content-ID", "<feesconnect-logo>")
    logo.add_header("Content-Disposition", "inline", filename="feesconnect-logo.png")
    message.attach(logo)
    message.send(fail_silently=False)


@shared_task
def dispatch_outbox() -> int:
    """Deliver up to fifty due rows; recover abandoned leases after worker failure."""
    ids = list(
        OutboxMessage.objects.filter(
            Q(state__in=["pending", "retry"], next_attempt_at__lte=timezone.now())
            | Q(state="processing", locked_until__lt=timezone.now())
        ).values_list("pk", flat=True)[:50]
    )
    delivered = 0
    for pk in ids:
        with transaction.atomic():
            row = OutboxMessage.objects.select_for_update().get(pk=pk)
            if row.state == "sent" or (
                row.state == "processing" and row.locked_until and row.locked_until > timezone.now()
            ):
                continue
            row.state = "processing"
            row.locked_until = timezone.now() + timedelta(minutes=3)
            row.attempt_count += 1
            row.save()
        try:
            deliver(row)
        except Exception as exc:
            row.state = "dead_letter" if row.attempt_count >= 10 else "retry"
            row.last_error_code = type(exc).__name__
            row.next_attempt_at = timezone.now() + timedelta(
                seconds=min(3600, 2**row.attempt_count * 10)
            )
            row.save()
        else:
            row.state = "sent"
            row.sent_at = timezone.now()
            row.save()
            delivered += 1
    return delivered
