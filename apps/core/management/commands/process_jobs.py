"""Run one worker cycle locally without Redis/Celery processes."""

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.tasks import dispatch_outbox
from apps.payments.tasks import process_events, reconcile_pending


class Command(BaseCommand):
    """Development helper; production uses Celery beat and workers."""

    def handle(self, *args: Any, **options: Any) -> Any:
        """Process pending jobs synchronously from the developer terminal."""
        self.stdout.write(
            f"Outbox: {dispatch_outbox()}; events: {process_events()}; polled: {reconcile_pending()}"
        )
