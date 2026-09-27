"""Customer support pages with user-scoped thread visibility."""

from typing import Any

from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.forms import BrandForm

from .models import SupportTicket, TicketMessage
from .services import ticket


class TicketForm(BrandForm):
    """Collect a support request without sensitive payment details."""

    subject = forms.CharField(max_length=160)
    body = forms.CharField(max_length=4000, widget=forms.Textarea)


@login_required
def home(request: HttpRequest) -> Any:
    """Create tickets and display only the current user's support history."""
    form = TicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = ticket(request.user, **form.cleaned_data)
        return redirect("support:ticket", pk=record.pk)
    return render(
        request,
        "support/home.html",
        {
            "form": form,
            "tickets": SupportTicket.objects.filter(opened_by=request.user),
            "title": "Support",
        },
    )


@login_required
def detail(request: HttpRequest, pk: Any) -> Any:
    """Show only customer-visible messages from an owned ticket."""
    record = get_object_or_404(SupportTicket, pk=pk, opened_by=request.user)
    return render(
        request,
        "support/ticket.html",
        {
            "ticket": record,
            "thread": TicketMessage.objects.filter(ticket=record, visibility="requester").order_by(
                "sent_at"
            ),
            "title": record.reference,
        },
    )
