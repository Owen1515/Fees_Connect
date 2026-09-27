"""Explicit schema for the fees domain; financial writes use services."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.core.base import Record


class School(Record):
    """Persist school data with explicit ownership and history."""

    code = models.CharField(max_length=255, unique=True, help_text="Code for this School record.")
    legal_name = models.CharField(
        max_length=255, default="", help_text="Legal name for this School record."
    )
    display_name = models.CharField(
        max_length=255, default="", help_text="Display name for this School record."
    )
    registration_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Registration number for this School record.",
    )
    country_code = models.CharField(
        max_length=255, default="ZW", help_text="Country code for this School record."
    )
    address = models.TextField(default="", help_text="Address for this School record.")
    contact_email = models.EmailField(
        max_length=254, help_text="Contact email for this School record."
    )
    contact_phone = models.CharField(
        max_length=255, null=True, blank=True, help_text="Contact phone for this School record."
    )
    status = models.CharField(
        max_length=255, default="pending", help_text="Status for this School record."
    )
    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Requested by for this School record.",
    )
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Reviewed by for this School record.",
    )
    reviewed_at = models.DateTimeField(
        null=True, blank=True, help_text="Reviewed at for this School record."
    )
    review_reason = models.TextField(default="", help_text="Review reason for this School record.")
    supported_currencies = models.ManyToManyField(
        "core.Currency", help_text="Supported currencies for this School record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["status", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["pending", "approved", "rejected", "suspended"]),
                name="ck_school_status",
            )
        ]


class AcademicPeriod(Record):
    """Persist academic period data with explicit ownership and history."""

    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="School for this AcademicPeriod record.",
    )
    code = models.CharField(
        max_length=255, default="", help_text="Code for this AcademicPeriod record."
    )
    label = models.CharField(
        max_length=255, default="", help_text="Label for this AcademicPeriod record."
    )
    starts_on = models.DateField(help_text="Starts on for this AcademicPeriod record.")
    ends_on = models.DateField(help_text="Ends on for this AcademicPeriod record.")
    is_active = models.BooleanField(
        default=True, help_text="Is active for this AcademicPeriod record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["school", "is_active"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gte=F("starts_on")), name="period_date_order"
            ),
            models.UniqueConstraint(fields=["school", "code"], name="fees_academicperiod_u0"),
        ]


class Student(Record):
    """Persist student data with explicit ownership and history."""

    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="School for this Student record.",
    )
    admission_number = models.CharField(
        max_length=255, default="", help_text="Admission number for this Student record."
    )
    full_name = models.CharField(
        max_length=255, default="", help_text="Full name for this Student record."
    )
    class_label = models.CharField(
        max_length=255, null=True, blank=True, help_text="Class label for this Student record."
    )
    status = models.CharField(
        max_length=255, default="pending", help_text="Status for this Student record."
    )
    submitted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Submitted by for this Student record.",
    )
    verified_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Verified by for this Student record.",
    )
    verified_at = models.DateTimeField(
        null=True, blank=True, help_text="Verified at for this Student record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["school", "status", "class_label"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["pending", "active", "inactive", "rejected"]),
                name="ck_student_status",
            ),
            models.UniqueConstraint(fields=["school", "admission_number"], name="fees_student_u0"),
        ]


class StudentAccess(Record):
    """Persist student access data with explicit ownership and history."""

    student = models.ForeignKey(
        "fees.Student",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Student for this StudentAccess record.",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="User for this StudentAccess record.",
    )
    relationship = models.CharField(
        max_length=255, default="self", help_text="Relationship for this StudentAccess record."
    )
    status = models.CharField(
        max_length=255, default="pending", help_text="Status for this StudentAccess record."
    )
    can_pay = models.BooleanField(default=True, help_text="Can pay for this StudentAccess record.")
    can_view_invoices = models.BooleanField(
        default=True, help_text="Can view invoices for this StudentAccess record."
    )
    can_view_history = models.BooleanField(
        default=True, help_text="Can view history for this StudentAccess record."
    )
    requested_at = models.DateTimeField(
        default=timezone.now, help_text="Requested at for this StudentAccess record."
    )
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Reviewed by for this StudentAccess record.",
    )
    reviewed_at = models.DateTimeField(
        null=True, blank=True, help_text="Reviewed at for this StudentAccess record."
    )
    verification_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Verification reference for this StudentAccess record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["student", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(relationship__in=["self", "parent", "guardian", "sponsor"]),
                name="ck_studentaccess_relati",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["pending", "approved", "rejected", "revoked"]),
                name="ck_studentaccess_status",
            ),
            models.UniqueConstraint(
                fields=["student"],
                condition=Q(status="approved", relationship="self"),
                name="one_verified_student_user",
            ),
            models.UniqueConstraint(fields=["student", "user"], name="fees_studentaccess_u0"),
        ]


class FeeCategory(Record):
    """Persist fee category data with explicit ownership and history."""

    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="School for this FeeCategory record.",
    )
    code = models.CharField(
        max_length=255, default="", help_text="Code for this FeeCategory record."
    )
    name = models.CharField(
        max_length=255, default="", help_text="Name for this FeeCategory record."
    )
    description = models.TextField(default="", help_text="Description for this FeeCategory record.")
    is_active = models.BooleanField(
        default=True, help_text="Is active for this FeeCategory record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["school", "is_active"])]
        constraints = [
            models.UniqueConstraint(fields=["school", "code"], name="fees_feecategory_u0")
        ]


class FeeSchedule(Record):
    """Persist fee schedule data with explicit ownership and history."""

    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="School for this FeeSchedule record.",
    )
    period = models.ForeignKey(
        "fees.AcademicPeriod",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Period for this FeeSchedule record.",
    )
    category = models.ForeignKey(
        "fees.FeeCategory",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Category for this FeeSchedule record.",
    )
    code = models.CharField(
        max_length=255, default="", help_text="Code for this FeeSchedule record."
    )
    revision = models.PositiveIntegerField(
        default=1, help_text="Revision for this FeeSchedule record."
    )
    class_label = models.CharField(
        max_length=255, null=True, blank=True, help_text="Class label for this FeeSchedule record."
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Amount for this FeeSchedule record.",
    )
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Currency for this FeeSchedule record.",
    )
    is_active = models.BooleanField(
        default=True, help_text="Is active for this FeeSchedule record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["school", "period", "is_active"])]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "code", "revision"], name="fees_feeschedule_u0"
            ),
            models.CheckConstraint(condition=Q(amount__gte=0), name="fees_feeschedule_m0"),
        ]


class Invoice(Record):
    """Persist invoice data with explicit ownership and history."""

    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="School for this Invoice record.",
    )
    student = models.ForeignKey(
        "fees.Student",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Student for this Invoice record.",
    )
    period = models.ForeignKey(
        "fees.AcademicPeriod",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Period for this Invoice record.",
    )
    number = models.CharField(
        max_length=255, default="", help_text="Number for this Invoice record."
    )
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Currency for this Invoice record.",
    )
    status = models.CharField(
        max_length=255, default="draft", help_text="Status for this Invoice record."
    )
    issued_at = models.DateTimeField(
        null=True, blank=True, help_text="Issued at for this Invoice record."
    )
    due_on = models.DateField(null=True, blank=True, help_text="Due on for this Invoice record.")
    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Total amount for this Invoice record.",
    )
    document_key = models.CharField(
        max_length=255, null=True, blank=True, help_text="Document key for this Invoice record."
    )
    document_sha256 = models.CharField(
        max_length=255, null=True, blank=True, help_text="Document sha256 for this Invoice record."
    )
    import_row = models.OneToOneField(
        "core.ImportRow",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Import row for this Invoice record.",
    )
    issued_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Issued by for this Invoice record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["school", "status", "due_on"]),
            models.Index(fields=["student", "issued_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "issued", "void"]), name="ck_invoice_status"
            ),
            models.UniqueConstraint(fields=["school", "number"], name="fees_invoice_u0"),
            models.CheckConstraint(condition=Q(total_amount__gte=0), name="fees_invoice_m0"),
        ]


class InvoiceLine(Record):
    """Persist invoice line data with explicit ownership and history."""

    invoice = models.ForeignKey(
        "fees.Invoice",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Invoice for this InvoiceLine record.",
    )
    position = models.PositiveIntegerField(
        default=0, help_text="Position for this InvoiceLine record."
    )
    category = models.ForeignKey(
        "fees.FeeCategory",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Category for this InvoiceLine record.",
    )
    schedule = models.ForeignKey(
        "fees.FeeSchedule",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Schedule for this InvoiceLine record.",
    )
    description_snapshot = models.TextField(
        default="", help_text="Description snapshot for this InvoiceLine record."
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("1"),
        help_text="Quantity for this InvoiceLine record.",
    )
    unit_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Unit amount for this InvoiceLine record.",
    )
    line_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Line amount for this InvoiceLine record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = []
        constraints = [
            models.UniqueConstraint(fields=["invoice", "position"], name="fees_invoiceline_u0"),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="fees_invoiceline_m0"),
            models.CheckConstraint(condition=Q(unit_amount__gte=0), name="fees_invoiceline_m1"),
            models.CheckConstraint(condition=Q(line_amount__gte=0), name="fees_invoiceline_m2"),
        ]


class InvoiceAdjustment(Record):
    """Persist invoice adjustment data with explicit ownership and history."""

    invoice = models.ForeignKey(
        "fees.Invoice",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Invoice for this InvoiceAdjustment record.",
    )
    amount_delta = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Amount delta for this InvoiceAdjustment record.",
    )
    reason = models.TextField(default="", help_text="Reason for this InvoiceAdjustment record.")
    source_key = models.CharField(
        max_length=255, default="", help_text="Source key for this InvoiceAdjustment record."
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Approved by for this InvoiceAdjustment record.",
    )
    effective_at = models.DateTimeField(
        default=timezone.now, help_text="Effective at for this InvoiceAdjustment record."
    )
    document_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Document key for this InvoiceAdjustment record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["invoice", "effective_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["invoice", "source_key"], name="fees_invoiceadjustme_u0"
            )
        ]
