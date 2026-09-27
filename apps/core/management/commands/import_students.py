"""CSV pupil migration with explicit validation and an atomic commit option."""

import csv
import hashlib
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import ImportBatch, ImportRow
from apps.core.security import seal
from apps.fees.models import School, Student


class Command(BaseCommand):
    """Dry-run by default; --commit imports only validated school-specific pupil rows."""

    def add_arguments(self, parser: Any) -> Any:
        """Accept a local file, school and responsible operator."""
        parser.add_argument("file")
        parser.add_argument("--school", required=True)
        parser.add_argument("--operator", required=True)
        parser.add_argument("--commit", action="store_true")

    def handle(self, *args: Any, **options: Any) -> Any:
        """Validate all rows before any import writes; track applied source rows."""
        path = Path(options["file"])
        raw = path.read_bytes()
        rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
        seen = set()
        for index, row in enumerate(rows, 2):
            identifier = row.get("admission_number", "").strip().upper()
            if not identifier or identifier in seen or not row.get("full_name", "").strip():
                raise CommandError(f"Invalid or duplicate row {index}")
            if len(identifier) > 64 or len(row["full_name"]) > 160:
                raise CommandError(f"Overlong field in row {index}")
            row["admission_number"] = identifier
            seen.add(identifier)
        school = School.objects.get(code=options["school"])
        actor = User.objects.get(email=options["operator"], is_superuser=True)
        self.stdout.write(f"Validated {len(rows)} rows for {school.code}.")
        if not options["commit"]:
            return
        digest = hashlib.sha256(raw).hexdigest()
        with transaction.atomic():
            School.objects.select_for_update().get(pk=school.pk)
            if ImportBatch.objects.filter(
                school=school, source_sha256=digest, status="completed"
            ).exists():
                self.stdout.write("Already imported; no rows changed.")
                return
            batch = ImportBatch.objects.create(
                school=school,
                data_kind="students",
                source_filename=path.name,
                source_sha256=digest,
                source_system="csv",
                effective_cutover_at=timezone.now(),
                submitted_by=actor,
                approved_by=actor,
                status="applying",
                source_key=path.name,
            )
            for index, row in enumerate(rows, 1):
                student, created = Student.objects.get_or_create(
                    school=school,
                    admission_number=row["admission_number"],
                    defaults={
                        "full_name": row["full_name"],
                        "class_label": row.get("class_label", ""),
                        "status": "active",
                        "verified_by": actor,
                        "verified_at": timezone.now(),
                    },
                )
                if not created and student.full_name != row["full_name"]:
                    raise CommandError("Existing pupil mismatch; no rows committed.")
                ImportRow.objects.create(
                    batch=batch,
                    row_number=index,
                    external_id=row["admission_number"],
                    row_digest=hashlib.sha256(str(row).encode()).hexdigest(),
                    encrypted_source_key=seal(row),
                    status="applied",
                    target_type="fees.Student",
                    target_id=str(student.pk),
                    applied_at=timezone.now(),
                )
            batch.status = "completed"
            batch.applied_at = timezone.now()
            batch.totals = {"students": len(rows)}
            batch.save()
        self.stdout.write(
            "Import committed. Payer/student account links still require verification."
        )
