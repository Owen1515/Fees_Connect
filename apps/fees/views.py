"""Authorised school, pupil and invoice pages."""

import uuid
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.access import invoices_for, is_operator, school_ids
from apps.accounts.views import form_page
from apps.core.services import audit
from apps.payments.services.documents import pdf_bytes

from .forms import InvoiceForm, SchoolForm, StudentForm
from .models import Invoice, InvoiceLine, School, Student, StudentAccess
from .services import approve_link, balance, request_student_link


@login_required
def student_register(request: HttpRequest) -> Any:
    """Collect student details and send the association for school review."""
    form = StudentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        request_student_link(request.user, **form.cleaned_data)
        messages.success(request, "Your details have been submitted for school verification.")
        return redirect("dashboard:home")
    return form_page(
        request, "fees/student_register.html", form, "Register a student or link a child"
    )


@login_required
def school_register(request: HttpRequest) -> Any:
    """Create a pending school; self-registration does not grant school-admin access."""
    form = SchoolForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        School.objects.create(
            code="SCH-" + uuid.uuid4().hex[:12].upper(),
            requested_by=request.user,
            **form.cleaned_data,
        )
        messages.success(request, "School submitted for manual approval.")
        return redirect("dashboard:home")
    return form_page(request, "fees/school_register.html", form, "Register your school")


@login_required
def invoice_list(request: HttpRequest) -> Any:
    """List only invoices visible through verified pupil/school associations."""
    rows = list(
        invoices_for(request.user)
        .select_related("student", "school", "currency")
        .order_by("-created_at")[:200]
    )
    for row in rows:
        row.outstanding = balance(row)
    return render(request, "fees/invoices.html", {"invoices": rows, "title": "Invoices and fees"})


@login_required
def invoice_detail(request: HttpRequest, pk: Any, pdf: Any = False) -> Any:
    """Render/download an invoice only after an object-level access check."""
    invoice = get_object_or_404(invoices_for(request.user), pk=pk)
    context = {
        "invoice": invoice,
        "lines": InvoiceLine.objects.filter(invoice=invoice),
        "balance": balance(invoice),
        "title": "Invoice " + invoice.number,
    }
    if pdf:
        response = HttpResponse(
            pdf_bytes("fees/invoice_pdf.html", context), content_type="application/pdf"
        )
        response["Content-Disposition"] = f'attachment; filename="invoice-{invoice.pk}.pdf"'
        return response
    return render(request, "fees/invoice.html", context)


@login_required
def school_workspace(request: HttpRequest) -> Any:
    """Review pupil links within assigned schools; approvals require POST and CSRF."""
    ids = (
        School.objects.values_list("pk", flat=True)
        if is_operator(request.user)
        else school_ids(request.user)
    )
    if not ids.exists():
        raise PermissionDenied
    if request.method == "POST":
        try:
            uuid.UUID(request.POST.get("link_id", ""))
        except ValueError:
            raise PermissionDenied("Invalid student-link request.")
        link = get_object_or_404(
            StudentAccess, pk=uuid.UUID(request.POST.get("link_id", "")), student__school_id__in=ids
        )
        approve_link(request.user, link)
        messages.success(request, "Student association verified.")
        return redirect("fees:school_workspace")
    return render(
        request,
        "fees/school_workspace.html",
        {
            "title": "School administration",
            "links": StudentAccess.objects.filter(
                student__school_id__in=ids, status="pending"
            ).select_related("student", "user"),
            "students": Student.objects.filter(school_id__in=ids, status="active")[:200],
        },
    )


@login_required
def issue_invoice(request: HttpRequest) -> Any:
    """Issue an invoice atomically and freeze the initial line amount."""
    form = InvoiceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        student = get_object_or_404(Student, pk=form.cleaned_data["student_id"], status="active")
        if not is_operator(request.user) and student.school_id not in school_ids(request.user):
            raise PermissionDenied
        data = form.cleaned_data
        if not student.school.supported_currencies.filter(pk=data["currency"]).exists():
            form.add_error("currency", "School does not bill in this currency.")
        else:
            try:
                with transaction.atomic():
                    invoice = Invoice.objects.create(
                        school=student.school,
                        student=student,
                        number=data["number"],
                        currency_id=data["currency"],
                        status="issued",
                        issued_at=timezone.now(),
                        due_on=data["due_on"],
                        total_amount=data["amount"],
                        issued_by=request.user,
                    )
                    InvoiceLine.objects.create(
                        invoice=invoice,
                        position=1,
                        description_snapshot=data["description"],
                        quantity=1,
                        unit_amount=data["amount"],
                        line_amount=data["amount"],
                    )
                    audit(request.user, "invoice_issued", invoice, student.school)
                return redirect("fees:invoice", pk=invoice.pk)
            except IntegrityError:
                form.add_error("number", "Invoice number already exists for this school.")
    return form_page(request, "fees/invoice_form.html", form, "Issue an invoice")
