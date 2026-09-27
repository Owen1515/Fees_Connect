"""Account workspace built from scoped selectors rather than browser demo state."""

from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.shortcuts import render

from apps.accounts.access import invoices_for, is_operator, payments_for, school_ids
from apps.fees.models import StudentAccess


@login_required
def home(request: HttpRequest) -> Any:
    """Render account records and role-appropriate navigation."""
    return render(
        request,
        "feesconnect/account.html",
        {
            "title": "Your FeesConnect workspace",
            "invoices": invoices_for(request.user).order_by("-created_at")[:5],
            "payments": payments_for(request.user).order_by("-created_at")[:5],
            "links": StudentAccess.objects.filter(user=request.user).select_related(
                "student__school"
            ),
            "school_admin": is_operator(request.user) or school_ids(request.user).exists(),
        },
    )
