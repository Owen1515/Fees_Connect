"""Manual school approval and scoped administrator assignment."""

from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import RoleAssignment, User
from apps.core.services import audit
from apps.fees.models import School


class Command(BaseCommand):
    """Approve only after independent school and bank-ownership verification."""

    def add_arguments(self, parser: Any) -> Any:
        """Require the school, reviewer and verified school administrator."""
        parser.add_argument("school_code")
        parser.add_argument("--operator", required=True)
        parser.add_argument("--admin-email", required=True)

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> Any:
        """Persist review and role assignment together."""
        actor = User.objects.get(email=options["operator"], is_superuser=True)
        administrator = User.objects.get(
            email=options["admin_email"], email_verified_at__isnull=False
        )
        school = School.objects.select_for_update().get(code=options["school_code"])
        if actor == school.requested_by:
            raise CommandError("A different operator must review the school.")
        school.status = "approved"
        school.reviewed_by = actor
        school.reviewed_at = timezone.now()
        school.save()
        school.supported_currencies.set(["USD", "ZWG"])
        group = Group.objects.get(name="school_admin")
        RoleAssignment.objects.get_or_create(
            user=administrator,
            group=group,
            school=school,
            status="active",
            defaults={"granted_by": actor},
        )
        audit(actor, "school_approved", school, school)
        self.stdout.write("School approved; merchant setup remains separate.")
