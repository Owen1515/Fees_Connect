"""Requeue one already-authenticated event; business transitions remain idempotent."""

from typing import Any

from django.core.management.base import BaseCommand

from apps.payments.models import WebhookEvent


class Command(BaseCommand):
    """Replay without accepting unsigned payloads or rewriting provider evidence."""

    def add_arguments(self, parser: Any) -> Any:
        """Require an existing event UUID."""
        parser.add_argument("event_id")

    def handle(self, *args: Any, **options: Any) -> Any:
        """Reset processing metadata only."""
        row = WebhookEvent.objects.get(pk=options["event_id"])
        row.processing_status = "received"
        row.next_retry_at = None
        row.error_code = None
        row.attempt_count = 0
        row.save()
        self.stdout.write("Event queued for safe replay.")
