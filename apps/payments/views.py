"""Payment pages coordinate forms; trusted settlement remains in services."""

import csv
import uuid
from decimal import Decimal
from typing import Any

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.access import (
    history_payments_for,
    invoices_for,
    is_operator,
    payments_for,
    school_ids,
)
from apps.fees.services import balance

from .forms import CheckoutForm
from .models import PaymentQuote, Receipt, ReconciliationItem
from .services.checkout import create_payment, quote
from .services.documents import receipt_pdf
from .services.gateways.base import GatewayError
from .services.lifecycle import request_refund


@login_required
def checkout(request: HttpRequest, invoice_id: Any) -> Any:
    """Review a server-generated quote then confirm it through a CSRF-protected POST."""
    invoice = get_object_or_404(invoices_for(request.user, "pay"), pk=invoice_id)
    form = CheckoutForm(
        request.POST or None,
        invoice=invoice,
        initial={"amount": balance(invoice), "currency": invoice.currency_id},
    )
    if request.method == "POST":
        try:
            if request.POST.get("quote_id"):
                selected = get_object_or_404(
                    PaymentQuote,
                    pk=uuid.UUID(request.POST["quote_id"]),
                    user=request.user,
                    invoice=invoice,
                )
                payment = create_payment(
                    request.user,
                    selected.pk,
                    request.POST.get("idempotency_key", ""),
                    request.POST.get("phone", ""),
                )
                return redirect("payments:status", pk=payment.pk)
            if form.is_valid():
                data = form.cleaned_data
                selected = quote(
                    request.user,
                    invoice.pk,
                    data["amount"],
                    data["merchant"].pk,
                    data["method"],
                    data["currency"],
                )
                return render(
                    request,
                    "payments/review.html",
                    {
                        "quote": selected,
                        "invoice": invoice,
                        "phone": data["phone"],
                        "idempotency_key": str(uuid.uuid4()),
                        "title": "Review your payment",
                    },
                )
        except (ValueError, GatewayError, ObjectDoesNotExist) as exc:
            form.add_error(
                None,
                (
                    str(exc)
                    if not isinstance(exc, ObjectDoesNotExist)
                    else "This payment option is unavailable."
                ),
            )
    return render(
        request,
        "payments/checkout.html",
        {"form": form, "invoice": invoice, "title": "Pay school fees"},
    )


@login_required
def status(request: HttpRequest, pk: Any) -> Any:
    """Show verified state; a success URL never marks a payment paid."""
    payment = get_object_or_404(payments_for(request.user), pk=pk)
    template = (
        "success"
        if payment.succeeded_at
        else "failed" if payment.status in ["failed", "cancelled"] else "pending"
    )
    return render(
        request,
        f"payments/{template}.html",
        {"payment": payment, "title": "Payment " + payment.status},
    )


@login_required
def status_json(request: HttpRequest, pk: Any) -> Any:
    """Return local verified status only; polling never calls the gateway from a view."""
    payment = get_object_or_404(payments_for(request.user), pk=pk)
    from django.urls import reverse

    return JsonResponse(
        {
            "status": payment.status,
            "complete": bool(payment.succeeded_at) or payment.status in ["failed", "cancelled"],
            "url": reverse("payments:status", args=[pk]),
            "redirect_url": payment.metadata.get("redirect_url", ""),
        }
    )


@login_required
def history(request: HttpRequest) -> Any:
    """List the payer's own records or authorised school finance records."""
    return render(
        request,
        "payments/history.html",
        {
            "payments": history_payments_for(request.user)
            .select_related("school")
            .order_by("-created_at")[:200],
            "title": "Payment history",
        },
    )


@login_required
def receipt(request: HttpRequest, pk: Any, pdf: Any = False) -> Any:
    """Render a financial document after checking the current pupil/payer scope."""
    row = get_object_or_404(Receipt, payment_id=pk)
    allowed = (
        payments_for(request.user).filter(pk=pk).exists()
        or invoices_for(request.user, "history").filter(pk=row.payment.invoice_id).exists()
    )
    if not allowed:
        raise PermissionDenied
    if pdf:
        response = HttpResponse(receipt_pdf(row), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{row.number}.pdf"'
        return response
    return render(
        request,
        "payments/receipt.html",
        {"receipt": row, "data": row.immutable_snapshot, "title": "Receipt " + row.number},
    )


@login_required
def export_history(request: HttpRequest) -> Any:
    """Export scoped records and neutralise spreadsheet formula injection."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="payments.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["reference", "school", "amount", "currency", "principal", "charge", "status", "created_at"]
    )
    for p in history_payments_for(request.user).select_related("school").iterator():
        values = [
            p.reference,
            p.school.display_name,
            p.amount,
            p.currency_id,
            p.principal_amount,
            p.charge_amount,
            p.status,
            p.created_at.isoformat(),
        ]
        writer.writerow(
            [
                "'" + str(x) if str(x).startswith(("=", "+", "-", "@", chr(9), chr(13))) else str(x)
                for x in values
            ]
        )
    return response


@login_required
def refund(request: HttpRequest, pk: Any) -> Any:
    """Finance operator requests a refund; the gateway worker executes it."""
    from django import forms

    from apps.accounts.forms import BrandForm

    class RefundForm(BrandForm):
        """Require a refundable principal amount and an audit reason."""

        amount = forms.DecimalField(decimal_places=2, max_digits=20, min_value=Decimal(".01"))
        reason = forms.CharField(widget=forms.Textarea)

    if not is_operator(request.user):
        raise PermissionDenied
    form = RefundForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            request_refund(
                request.user, pk, form.cleaned_data["amount"], form.cleaned_data["reason"]
            )
        except ValueError as exc:
            form.add_error(None, str(exc))
        else:
            return redirect("payments:status", pk=pk)
    return render(request, "payments/refund.html", {"form": form, "title": "Request refund"})


@login_required
def reconciliation(request: HttpRequest) -> Any:
    """Display finance exceptions, restricted to assigned schools."""
    rows = ReconciliationItem.objects.select_related("run__merchant_account", "payment").order_by(
        "-created_at"
    )
    if not is_operator(request.user):
        rows = rows.filter(run__merchant_account__school_id__in=school_ids(request.user))
    return render(
        request,
        "payments/reconciliation.html",
        {"items": rows[:300], "title": "Payment reconciliation"},
    )
