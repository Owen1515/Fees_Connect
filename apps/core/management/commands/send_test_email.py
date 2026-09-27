"""Queue a test email without blocking an HTTP request."""

import uuid
from typing import Any

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.core.services import queue_email


class Command(BaseCommand):
    """Queue a test message for an existing verified account."""

    help = "Queue a Microsoft 365 test email; run the worker or process_jobs to deliver."

    def add_arguments(self, parser: Any) -> Any:
        """Require an explicit recipient account."""
        parser.add_argument("email")

    def handle(self, *args: Any, **options: Any) -> Any:
        """Create a durable test-email request."""
        user = User.objects.get(email=options["email"])
        row = queue_email(user, "test", {}, "test:" + uuid.uuid4().hex)
        self.stdout.write(f"Queued {row.pk}; inspect outbox state after delivery.")
