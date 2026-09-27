"""Idempotently create currency and permission reference data, never live merchants."""

from typing import Any

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Currency
from apps.payments.models import FeePolicy


class Command(BaseCommand):
    """Install non-secret reference records for a new environment."""

    def handle(self, *args: Any, **options: Any) -> Any:
        """Create supported currencies, role bundles and the 3% launch policy."""
        for code, label, symbol in [
            ("USD", "US dollar", "$"),
            ("ZWG", "ZiG", "ZiG"),
            ("GBP", "Pound sterling", "£"),
            ("EUR", "Euro", "€"),
        ]:
            Currency.objects.get_or_create(
                code=code, defaults={"display_name": label, "symbol": symbol}
            )
        for role in ["parent", "student", "school_admin", "super_admin"]:
            group, _ = Group.objects.get_or_create(name=role)
            if role == "school_admin":
                group.permissions.set(Permission.objects.filter(content_type__app_label="fees"))
        FeePolicy.objects.get_or_create(
            version=1, defaults={"approved_at": timezone.now(), "rate_bps": 300}
        )
        self.stdout.write(
            "Reference data installed. No merchant accounts or credentials were created."
        )
