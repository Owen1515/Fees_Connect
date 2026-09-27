"""Import operator-verified settlement statement rows without treating screenshots as proof."""

import csv
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.services import audit
from apps.payments.models import MerchantAccount, Payment, SettlementEntry


class Command(BaseCommand):
    """Validate statement rows; only --commit writes confirmed provider evidence."""

    def add_arguments(self, parser: Any) -> Any:
        """Require an external bank/provider statement and a responsible operator."""
        parser.add_argument("file")
        parser.add_argument("--operator", required=True)
        parser.add_argument("--commit", action="store_true")

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> Any:
        """Idempotently import trusted settlement rows and preserve their source IDs."""
        actor = User.objects.get(email=options["operator"], is_superuser=True)
        rows = list(csv.DictReader(Path(options["file"]).read_text().splitlines()))
        validated = []
        for row in rows:
            payment = Payment.objects.get(
                reference=row["payment_reference"], succeeded_at__isnull=False
            )
            merchant = MerchantAccount.objects.get(pk=row["merchant_account_id"])
            if merchant.gateway != payment.gateway:
                raise CommandError("Provider mismatch.")
            if row["beneficiary"] == "school" and merchant.school_id != payment.school_id:
                raise CommandError("School mismatch.")
            if row["beneficiary"] == "platform" and merchant.owner_kind != "platform":
                raise CommandError("Platform beneficiary mismatch.")
            if row["beneficiary"] not in ["school", "platform", "provider"] or row[
                "direction"
            ] not in ["credit", "debit"]:
                raise CommandError("Invalid settlement direction or beneficiary.")
            amount = Decimal(row["amount"])
            if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal(".01")):
                raise CommandError("Invalid settlement amount.")
            validated.append((row, payment, merchant, amount))
        if not options["commit"]:
            self.stdout.write(
                f"Validated {len(rows)} rows; add --commit after verifying the statement."
            )
            return
        for row, payment, merchant, amount in validated:
            record, created = SettlementEntry.objects.get_or_create(
                merchant_account=merchant,
                provider_transaction_id=row["provider_transaction_id"],
                provider_line_id=row["provider_line_id"],
                defaults={
                    "payment": payment,
                    "beneficiary": row["beneficiary"],
                    "kind": row["kind"],
                    "direction": row["direction"],
                    "amount": amount,
                    "currency_id": row["currency"],
                    "status": "confirmed",
                    "settled_at": timezone.now(),
                    "bank_payout_ref": row.get("bank_payout_ref", ""),
                    "evidence_key": Path(options["file"]).name,
                },
            )
            if not created and (
                record.amount != amount
                or record.currency_id != row["currency"]
                or record.payment_id != payment.pk
            ):
                raise CommandError("Existing statement row differs; investigate before importing.")
            if created:
                audit(actor, "settlement_imported", record, payment.school)
        self.stdout.write(f"Imported {len(rows)} rows idempotently.")
