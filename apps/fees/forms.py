from decimal import Decimal

"""Validated school and pupil forms using the existing design classes."""

from django import forms

from apps.accounts.forms import BrandForm

from .models import School


class StudentForm(BrandForm):
    """Request a verified student/guardian relationship."""

    school = forms.ModelChoiceField(queryset=School.objects.filter(status="approved"))
    admission_number = forms.CharField(max_length=64)
    full_name = forms.CharField(max_length=160)
    relationship = forms.ChoiceField(
        choices=[
            ("self", "I am the student"),
            ("parent", "Parent"),
            ("guardian", "Guardian"),
            ("sponsor", "Sponsor"),
        ]
    )


class SchoolForm(BrandForm):
    """Submit a school for manual platform approval."""

    legal_name = forms.CharField(max_length=160)
    display_name = forms.CharField(max_length=160)
    registration_number = forms.CharField(max_length=64)
    contact_email = forms.EmailField()
    contact_phone = forms.CharField(max_length=32, required=False)
    address = forms.CharField(widget=forms.Textarea)


class InvoiceForm(BrandForm):
    """Issue one itemised fee demand for a verified pupil."""

    student_id = forms.UUIDField()
    number = forms.CharField(max_length=64)
    description = forms.CharField(max_length=200)
    amount = forms.DecimalField(max_digits=20, decimal_places=2, min_value=Decimal("0.01"))
    currency = forms.ChoiceField(choices=[("USD", "USD"), ("ZWG", "ZiG")])
    due_on = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
