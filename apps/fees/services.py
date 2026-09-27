"""School-scoped balances and student onboarding."""

from decimal import Decimal
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.access import is_operator, school_ids
from apps.core.services import audit

from .models import Invoice, InvoiceAdjustment, Student, StudentAccess


def balance(invoice: Invoice) -> Decimal:
    """Compute liability less net principal allocations, excluding customer charges."""
    from apps.payments.models import AllocationAdjustment, PaymentAllocation

    def total(queryset: Any, field: str) -> Decimal:
        """Coalesce empty aggregate results to an exact decimal zero."""
        return queryset.aggregate(v=Sum(field))["v"] or Decimal("0")

    return (
        invoice.total_amount
        + total(InvoiceAdjustment.objects.filter(invoice=invoice), "amount_delta")
        - total(PaymentAllocation.objects.filter(invoice=invoice), "principal_amount")
        - total(AllocationAdjustment.objects.filter(allocation__invoice=invoice), "delta")
    )


@transaction.atomic
def request_student_link(
    user: Any, school: Any, admission_number: str, full_name: str, relationship: str
) -> Any:
    """Create a pending claim without disclosing existing pupil names or balances."""
    if school.status != "approved":
        raise ValueError("School is not approved.")
    student, _ = Student.objects.get_or_create(
        school=school,
        admission_number=admission_number.strip().upper(),
        defaults={"full_name": full_name, "submitted_by": user},
    )
    link, _ = StudentAccess.objects.get_or_create(
        user=user, student=student, defaults={"relationship": relationship}
    )
    audit(user, "student_link_requested", link, school)
    return link


@transaction.atomic
def approve_link(actor: Any, link: Any) -> Any:
    """Approve a verified pupil relationship only within an authorised school."""
    link = StudentAccess.objects.select_for_update().select_related("student").get(pk=link.pk)
    if not is_operator(actor) and link.student.school_id not in school_ids(actor):
        raise PermissionDenied
    if link.user_id == actor.pk:
        raise PermissionDenied("Another authorised person must verify your link.")
    link.status = "approved"
    link.reviewed_by = actor
    link.reviewed_at = timezone.now()
    link.save()
    student = link.student
    student.status = "active"
    student.verified_by = actor
    student.verified_at = timezone.now()
    student.save()
    audit(actor, "student_link_approved", link, student.school)
