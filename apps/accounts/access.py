"""Central object-level permission selectors; all HTML and API paths reuse these."""

from typing import Any

from django.db.models import Q

from apps.fees.models import Invoice, StudentAccess

from .models import RoleAssignment


def school_ids(user: Any) -> Any:
    """Return the schools where the user has an active school administrator role."""
    return RoleAssignment.objects.filter(
        user=user, status="active", group__name="school_admin"
    ).values_list("school_id", flat=True)


def is_operator(user: Any) -> bool:
    """Return whether a trusted platform-wide operator permission was assigned."""
    return (
        user.is_superuser
        or RoleAssignment.objects.filter(
            user=user, status="active", school=None, group__name="super_admin"
        ).exists()
    )


def invoices_for(user: Any, purpose: str = "view") -> Any:
    """Return only invoices accessible through approved school/pupil associations."""
    if is_operator(user):
        return Invoice.objects.all()
    field = {"pay": "can_pay", "history": "can_view_history"}.get(purpose, "can_view_invoices")
    pupils = StudentAccess.objects.filter(user=user, status="approved", **{field: True}).values(
        "student_id"
    )
    return Invoice.objects.filter(
        Q(student_id__in=pupils) | Q(school_id__in=school_ids(user))
    ).distinct()


def payments_for(user: Any) -> Any:
    """Expose own payments or school-admin records; guardians use masked pupil receipts."""
    from apps.payments.models import Payment

    if is_operator(user):
        return Payment.objects.all()
    return Payment.objects.filter(Q(user=user) | Q(school_id__in=school_ids(user))).distinct()


def history_payments_for(user: Any) -> Any:
    """Expose masked payment history for approved pupils as well as the payer's own records."""
    from apps.payments.models import Payment

    if is_operator(user):
        return Payment.objects.all()
    pupils = StudentAccess.objects.filter(
        user=user, status="approved", can_view_history=True
    ).values("student_id")
    return Payment.objects.filter(
        Q(user=user) | Q(school_id__in=school_ids(user)) | Q(invoice__student_id__in=pupils)
    ).distinct()
