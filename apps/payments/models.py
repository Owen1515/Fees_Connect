"""Explicit schema for the payments domain; financial writes use services."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.base import Record


class MerchantAccount(Record):
    """Persist merchant account data with explicit ownership and history."""

    owner_kind = models.CharField(
        max_length=255, default="school", help_text="Owner kind for this MerchantAccount record."
    )
    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="School for this MerchantAccount record.",
    )
    gateway = models.CharField(
        max_length=255, default="", help_text="Gateway for this MerchantAccount record."
    )
    environment = models.CharField(
        max_length=255, default="test", help_text="Environment for this MerchantAccount record."
    )
    external_account_id = models.CharField(
        max_length=255, default="", help_text="External account id for this MerchantAccount record."
    )
    settlement_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Settlement currency for this MerchantAccount record.",
    )
    jurisdiction = models.CharField(
        max_length=255, default="", help_text="Jurisdiction for this MerchantAccount record."
    )
    status = models.CharField(
        max_length=255, default="pending", help_text="Status for this MerchantAccount record."
    )
    credential_secret_ref = models.CharField(
        max_length=255,
        default="",
        help_text="Credential secret ref for this MerchantAccount record.",
    )
    verified_capabilities = models.JSONField(
        default=dict, blank=True, help_text="Verified capabilities for this MerchantAccount record."
    )
    fee_bearer = models.CharField(
        max_length=255, default="platform", help_text="Fee bearer for this MerchantAccount record."
    )
    verified_at = models.DateTimeField(
        null=True, blank=True, help_text="Verified at for this MerchantAccount record."
    )
    payout_destination_fingerprint = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Payout destination fingerprint for this MerchantAccount record.",
    )
    capabilities_version = models.PositiveIntegerField(
        default=1, help_text="Capabilities version for this MerchantAccount record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["school", "gateway", "status"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(owner_kind__in=["school", "platform"]),
                name="ck_merchantaccount_owner_",
            ),
            models.CheckConstraint(
                condition=models.Q(gateway__in=["stripe", "paypal", "paynow", "bank_partner"]),
                name="ck_merchantaccount_gatewa",
            ),
            models.CheckConstraint(
                condition=models.Q(environment__in=["test", "live"]),
                name="ck_merchantaccount_enviro",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["pending", "enabled", "restricted", "disabled"]),
                name="ck_merchantaccount_status",
            ),
            models.CheckConstraint(
                condition=Q(owner_kind="school", school__isnull=False)
                | Q(owner_kind="platform", school__isnull=True),
                name="merchant_owner_scope",
            ),
            models.UniqueConstraint(
                fields=["gateway", "environment", "external_account_id", "settlement_currency"],
                name="payments_merchantaccount_u0",
            ),
        ]


class GatewayCustomer(Record):
    """Persist gateway customer data with explicit ownership and history."""

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="User for this GatewayCustomer record.",
    )
    merchant_account = models.ForeignKey(
        "payments.MerchantAccount",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Merchant account for this GatewayCustomer record.",
    )
    external_customer_id = models.CharField(
        max_length=255,
        default="",
        help_text="External customer id for this GatewayCustomer record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = []
        constraints = [
            models.UniqueConstraint(
                fields=["user", "merchant_account"], name="payments_gatewaycustomer_u0"
            ),
            models.UniqueConstraint(
                fields=["merchant_account", "external_customer_id"],
                name="payments_gatewaycustomer_u1",
            ),
        ]


class SavedPaymentMethod(Record):
    """Persist saved payment method data with explicit ownership and history."""

    customer = models.ForeignKey(
        "payments.GatewayCustomer",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Customer for this SavedPaymentMethod record.",
    )
    external_method_id = models.CharField(
        max_length=255,
        default="",
        help_text="External method id for this SavedPaymentMethod record.",
    )
    kind = models.CharField(
        max_length=255, default="", help_text="Kind for this SavedPaymentMethod record."
    )
    brand = models.CharField(
        max_length=255, null=True, blank=True, help_text="Brand for this SavedPaymentMethod record."
    )
    last_four = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Last four for this SavedPaymentMethod record.",
    )
    expiry_month = models.PositiveIntegerField(
        null=True, blank=True, help_text="Expiry month for this SavedPaymentMethod record."
    )
    expiry_year = models.PositiveIntegerField(
        null=True, blank=True, help_text="Expiry year for this SavedPaymentMethod record."
    )
    consented_at = models.DateTimeField(
        default=timezone.now, help_text="Consented at for this SavedPaymentMethod record."
    )
    consent_version = models.CharField(
        max_length=255, default="", help_text="Consent version for this SavedPaymentMethod record."
    )
    revoked_at = models.DateTimeField(
        null=True, blank=True, help_text="Revoked at for this SavedPaymentMethod record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["customer", "revoked_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "external_method_id"], name="payments_savedpaymentmet_u0"
            )
        ]


class FeePolicy(Record):
    """Persist fee policy data with explicit ownership and history."""

    version = models.PositiveIntegerField(default=0, help_text="Version for this FeePolicy record.")
    rate_bps = models.PositiveIntegerField(
        default=300, help_text="Rate bps for this FeePolicy record."
    )
    calculation_basis = models.CharField(
        max_length=255,
        default="principal",
        help_text="Calculation basis for this FeePolicy record.",
    )
    rounding_mode = models.CharField(
        max_length=255,
        default="ROUND_HALF_UP",
        help_text="Rounding mode for this FeePolicy record.",
    )
    effective_from = models.DateTimeField(
        default=timezone.now, help_text="Effective from for this FeePolicy record."
    )
    effective_until = models.DateTimeField(
        null=True, blank=True, help_text="Effective until for this FeePolicy record."
    )
    fx_cost_treatment = models.CharField(
        max_length=255, default="included", help_text="Fx cost treatment for this FeePolicy record."
    )
    shortfall_treatment = models.CharField(
        max_length=255,
        default="disable_route",
        help_text="Shortfall treatment for this FeePolicy record.",
    )
    charge_refund_policy = models.CharField(
        max_length=255,
        default="refundable",
        help_text="Charge refund policy for this FeePolicy record.",
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Approved by for this FeePolicy record.",
    )
    approved_at = models.DateTimeField(
        null=True, blank=True, help_text="Approved at for this FeePolicy record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["effective_from"])]
        constraints = [
            models.CheckConstraint(condition=Q(rate_bps=300), name="launch_charge_three_percent"),
            models.UniqueConstraint(fields=["version"], name="payments_feepolicy_u0"),
        ]


class FXQuote(Record):
    """Persist f x quote data with explicit ownership and history."""

    source_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Source currency for this FXQuote record.",
    )
    payer_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payer currency for this FXQuote record.",
    )
    rate = models.DecimalField(
        max_digits=24,
        decimal_places=12,
        default=Decimal("0"),
        help_text="Rate for this FXQuote record.",
    )
    source_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Source amount for this FXQuote record.",
    )
    payer_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Payer amount for this FXQuote record.",
    )
    provider = models.CharField(
        max_length=255, default="", help_text="Provider for this FXQuote record."
    )
    provider_quote_id = models.CharField(
        max_length=255, default="", help_text="Provider quote id for this FXQuote record."
    )
    merchant_account = models.ForeignKey(
        "payments.MerchantAccount",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Merchant account for this FXQuote record.",
    )
    executable = models.BooleanField(default=False, help_text="Executable for this FXQuote record.")
    quoted_at = models.DateTimeField(
        default=timezone.now, help_text="Quoted at for this FXQuote record."
    )
    expires_at = models.DateTimeField(
        default=timezone.now, help_text="Expires at for this FXQuote record."
    )
    rounding_delta = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Rounding delta for this FXQuote record.",
    )
    provider_cost_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        null=True,
        blank=True,
        help_text="Provider cost amount for this FXQuote record.",
    )
    provider_cost_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Provider cost currency for this FXQuote record.",
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Metadata for this FXQuote record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["expires_at"]),
            models.Index(fields=["source_currency", "payer_currency", "quoted_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["merchant_account", "provider", "provider_quote_id"],
                name="payments_fxquote_u0",
            ),
            models.CheckConstraint(condition=Q(source_amount__gte=0), name="payments_fxquote_m0"),
            models.CheckConstraint(condition=Q(payer_amount__gte=0), name="payments_fxquote_m1"),
            models.CheckConstraint(
                condition=Q(provider_cost_amount__gte=0), name="payments_fxquote_m2"
            ),
        ]


class PaymentQuote(Record):
    """Persist payment quote data with explicit ownership and history."""

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="User for this PaymentQuote record.",
    )
    invoice = models.ForeignKey(
        "fees.Invoice",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Invoice for this PaymentQuote record.",
    )
    school_merchant = models.ForeignKey(
        "payments.MerchantAccount",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="School merchant for this PaymentQuote record.",
    )
    platform_merchant = models.ForeignKey(
        "payments.MerchantAccount",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Platform merchant for this PaymentQuote record.",
    )
    policy = models.ForeignKey(
        "payments.FeePolicy",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Policy for this PaymentQuote record.",
    )
    fx_quote = models.OneToOneField(
        "payments.FXQuote",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Fx quote for this PaymentQuote record.",
    )
    principal_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Principal amount for this PaymentQuote record.",
    )
    charge_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Charge amount for this PaymentQuote record.",
    )
    invoice_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Invoice currency for this PaymentQuote record.",
    )
    payer_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Payer amount for this PaymentQuote record.",
    )
    payer_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payer currency for this PaymentQuote record.",
    )
    expected_provider_cost = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        null=True,
        blank=True,
        help_text="Expected provider cost for this PaymentQuote record.",
    )
    expected_cost_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Expected cost currency for this PaymentQuote record.",
    )
    expected_platform_margin = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Expected platform margin for this PaymentQuote record.",
    )
    expected_margin_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Expected margin currency for this PaymentQuote record.",
    )
    payment_method = models.CharField(
        max_length=255, default="", help_text="Payment method for this PaymentQuote record."
    )
    settlement_plan = models.JSONField(
        default=dict, blank=True, help_text="Settlement plan for this PaymentQuote record."
    )
    capabilities_version = models.PositiveIntegerField(
        default=0, help_text="Capabilities version for this PaymentQuote record."
    )
    expires_at = models.DateTimeField(
        default=timezone.now, help_text="Expires at for this PaymentQuote record."
    )
    accepted_at = models.DateTimeField(
        null=True, blank=True, help_text="Accepted at for this PaymentQuote record."
    )
    request_digest = models.CharField(
        max_length=255, default="", help_text="Request digest for this PaymentQuote record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["user", "expires_at"]),
            models.Index(fields=["invoice", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(principal_amount__gte=0), name="payments_paymentquote_m0"
            ),
            models.CheckConstraint(
                condition=Q(charge_amount__gte=0), name="payments_paymentquote_m1"
            ),
            models.CheckConstraint(
                condition=Q(payer_amount__gte=0), name="payments_paymentquote_m2"
            ),
            models.CheckConstraint(
                condition=Q(expected_provider_cost__gte=0), name="payments_paymentquote_m3"
            ),
        ]


class Payment(Record):
    """Persist payment data with explicit ownership and history."""

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="User for this Payment record.",
    )
    invoice = models.ForeignKey(
        "fees.Invoice",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Invoice for this Payment record.",
    )
    quote = models.OneToOneField(
        "payments.PaymentQuote",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Quote for this Payment record.",
    )
    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="School for this Payment record.",
    )
    merchant_account = models.ForeignKey(
        "payments.MerchantAccount",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Merchant account for this Payment record.",
    )
    reference = models.CharField(
        max_length=255, unique=True, help_text="Reference for this Payment record."
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Amount for this Payment record.",
    )
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Currency for this Payment record.",
    )
    principal_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Principal amount for this Payment record.",
    )
    principal_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Principal currency for this Payment record.",
    )
    charge_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Charge amount for this Payment record.",
    )
    charge_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Charge currency for this Payment record.",
    )
    gateway = models.CharField(
        max_length=255, default="", help_text="Gateway for this Payment record."
    )
    status = models.CharField(
        max_length=255, default="created", help_text="Status for this Payment record."
    )
    idempotency_key = models.CharField(
        max_length=255, default="", help_text="Idempotency key for this Payment record."
    )
    request_digest = models.CharField(
        max_length=255, default="", help_text="Request digest for this Payment record."
    )
    gateway_ref = models.CharField(
        max_length=255, null=True, blank=True, help_text="Gateway ref for this Payment record."
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Metadata for this Payment record."
    )
    succeeded_at = models.DateTimeField(
        null=True, blank=True, help_text="Succeeded at for this Payment record."
    )
    review_reason = models.TextField(
        null=True, blank=True, help_text="Review reason for this Payment record."
    )
    import_row = models.OneToOneField(
        "core.ImportRow",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Import row for this Payment record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["school", "status", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["invoice", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "created",
                        "pending",
                        "succeeded",
                        "failed",
                        "cancelled",
                        "partially_refunded",
                        "refunded",
                        "review",
                    ]
                ),
                name="ck_payment_status",
            ),
            models.UniqueConstraint(
                fields=["merchant_account", "gateway_ref"],
                condition=Q(gateway_ref__isnull=False),
                name="unique_gateway_capture",
            ),
            models.UniqueConstraint(fields=["user", "idempotency_key"], name="payments_payment_u0"),
            models.CheckConstraint(condition=Q(amount__gte=0), name="payments_payment_m0"),
            models.CheckConstraint(
                condition=Q(principal_amount__gte=0), name="payments_payment_m1"
            ),
            models.CheckConstraint(condition=Q(charge_amount__gte=0), name="payments_payment_m2"),
        ]


class PaymentAttempt(Record):
    """Persist payment attempt data with explicit ownership and history."""

    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payment for this PaymentAttempt record.",
    )
    attempt_number = models.PositiveIntegerField(
        default=0, help_text="Attempt number for this PaymentAttempt record."
    )
    provider_idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        help_text="Provider idempotency key for this PaymentAttempt record.",
    )
    provider_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Provider reference for this PaymentAttempt record.",
    )
    state = models.CharField(
        max_length=255, default="created", help_text="State for this PaymentAttempt record."
    )
    submitted_at = models.DateTimeField(
        null=True, blank=True, help_text="Submitted at for this PaymentAttempt record."
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Completed at for this PaymentAttempt record."
    )
    error_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Error code for this PaymentAttempt record.",
    )
    request_digest = models.CharField(
        max_length=255, default="", help_text="Request digest for this PaymentAttempt record."
    )
    safe_response = models.JSONField(
        default=dict, blank=True, help_text="Safe response for this PaymentAttempt record."
    )
    encrypted_poll_url = models.TextField(
        null=True, blank=True, help_text="Encrypted poll url for this PaymentAttempt record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["state", "updated_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    state__in=[
                        "created",
                        "submitting",
                        "unknown",
                        "pending",
                        "succeeded",
                        "failed",
                        "cancelled",
                    ]
                ),
                name="ck_paymentattempt_state",
            ),
            models.UniqueConstraint(
                fields=["payment", "attempt_number"], name="payments_paymentattempt_u0"
            ),
        ]


class InvoiceReservation(Record):
    """Persist invoice reservation data with explicit ownership and history."""

    invoice = models.ForeignKey(
        "fees.Invoice",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Invoice for this InvoiceReservation record.",
    )
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payment for this InvoiceReservation record.",
    )
    principal_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Principal amount for this InvoiceReservation record.",
    )
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Currency for this InvoiceReservation record.",
    )
    expires_at = models.DateTimeField(
        default=timezone.now, help_text="Expires at for this InvoiceReservation record."
    )
    status = models.CharField(
        max_length=255, default="active", help_text="Status for this InvoiceReservation record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["invoice", "status", "expires_at"]),
            models.Index(fields=["status", "expires_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["active", "consumed", "released", "expired"]),
                name="ck_invoicereservatio_status",
            ),
            models.CheckConstraint(
                condition=Q(principal_amount__gte=0), name="payments_invoicereser_m0"
            ),
        ]


class PaymentAllocation(Record):
    """Persist payment allocation data with explicit ownership and history."""

    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payment for this PaymentAllocation record.",
    )
    invoice = models.ForeignKey(
        "fees.Invoice",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Invoice for this PaymentAllocation record.",
    )
    principal_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Principal amount for this PaymentAllocation record.",
    )
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Currency for this PaymentAllocation record.",
    )
    allocated_at = models.DateTimeField(
        default=timezone.now, help_text="Allocated at for this PaymentAllocation record."
    )
    source_key = models.CharField(
        max_length=255, unique=True, help_text="Source key for this PaymentAllocation record."
    )
    allocated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Allocated by for this PaymentAllocation record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["invoice", "allocated_at"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(principal_amount__gte=0), name="payments_paymentalloc_m0"
            )
        ]


class AllocationAdjustment(Record):
    """Persist allocation adjustment data with explicit ownership and history."""

    allocation = models.ForeignKey(
        "payments.PaymentAllocation",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Allocation for this AllocationAdjustment record.",
    )
    refund = models.ForeignKey(
        "payments.Refund",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Refund for this AllocationAdjustment record.",
    )
    dispute = models.ForeignKey(
        "payments.Dispute",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Dispute for this AllocationAdjustment record.",
    )
    delta = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Delta for this AllocationAdjustment record.",
    )
    reason = models.CharField(
        max_length=255, default="", help_text="Reason for this AllocationAdjustment record."
    )
    source_key = models.CharField(
        max_length=255, unique=True, help_text="Source key for this AllocationAdjustment record."
    )
    effective_at = models.DateTimeField(
        default=timezone.now, help_text="Effective at for this AllocationAdjustment record."
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Approved by for this AllocationAdjustment record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["allocation", "effective_at"])]
        constraints = []


class Refund(Record):
    """Persist refund data with explicit ownership and history."""

    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payment for this Refund record.",
    )
    reference = models.CharField(
        max_length=255, unique=True, help_text="Reference for this Refund record."
    )
    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Requested by for this Refund record.",
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Approved by for this Refund record.",
    )
    principal_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Principal amount for this Refund record.",
    )
    principal_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Principal currency for this Refund record.",
    )
    payer_principal_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Payer principal amount for this Refund record.",
    )
    charge_refund_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Charge refund amount for this Refund record.",
    )
    payer_refund_total = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Payer refund total for this Refund record.",
    )
    payer_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payer currency for this Refund record.",
    )
    status = models.CharField(
        max_length=255, default="requested", help_text="Status for this Refund record."
    )
    reason = models.TextField(default="", help_text="Reason for this Refund record.")
    idempotency_key = models.CharField(
        max_length=255, unique=True, help_text="Idempotency key for this Refund record."
    )
    gateway_ref = models.CharField(
        max_length=255, null=True, blank=True, help_text="Gateway ref for this Refund record."
    )
    provider_cost_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        null=True,
        blank=True,
        help_text="Provider cost amount for this Refund record.",
    )
    provider_cost_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Provider cost currency for this Refund record.",
    )
    approved_at = models.DateTimeField(
        null=True, blank=True, help_text="Approved at for this Refund record."
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Completed at for this Refund record."
    )
    safe_metadata = models.JSONField(
        default=dict, blank=True, help_text="Safe metadata for this Refund record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["payment", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "requested",
                        "approved",
                        "submitting",
                        "unknown",
                        "pending",
                        "succeeded",
                        "failed",
                        "rejected",
                    ]
                ),
                name="ck_refund_status",
            ),
            models.CheckConstraint(condition=Q(principal_amount__gte=0), name="payments_refund_m0"),
            models.CheckConstraint(
                condition=Q(payer_principal_amount__gte=0), name="payments_refund_m1"
            ),
            models.CheckConstraint(
                condition=Q(charge_refund_amount__gte=0), name="payments_refund_m2"
            ),
            models.CheckConstraint(
                condition=Q(payer_refund_total__gte=0), name="payments_refund_m3"
            ),
            models.CheckConstraint(
                condition=Q(provider_cost_amount__gte=0), name="payments_refund_m4"
            ),
        ]


class WebhookEvent(Record):
    """Persist webhook event data with explicit ownership and history."""

    merchant_account = models.ForeignKey(
        "payments.MerchantAccount",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Merchant account for this WebhookEvent record.",
    )
    gateway = models.CharField(
        max_length=255, default="", help_text="Gateway for this WebhookEvent record."
    )
    dedupe_key = models.CharField(
        max_length=255, default="", help_text="Dedupe key for this WebhookEvent record."
    )
    external_event_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="External event id for this WebhookEvent record.",
    )
    event_type = models.CharField(
        max_length=255, default="", help_text="Event type for this WebhookEvent record."
    )
    payload_digest = models.CharField(
        max_length=255, default="", help_text="Payload digest for this WebhookEvent record."
    )
    encrypted_payload_key = models.TextField(
        null=True, blank=True, help_text="Encrypted payload key for this WebhookEvent record."
    )
    signature_verified_at = models.DateTimeField(
        default=timezone.now, help_text="Signature verified at for this WebhookEvent record."
    )
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Payment for this WebhookEvent record.",
    )
    processing_status = models.CharField(
        max_length=255,
        default="received",
        help_text="Processing status for this WebhookEvent record.",
    )
    attempt_count = models.PositiveIntegerField(
        default=0, help_text="Attempt count for this WebhookEvent record."
    )
    next_retry_at = models.DateTimeField(
        null=True, blank=True, help_text="Next retry at for this WebhookEvent record."
    )
    processed_at = models.DateTimeField(
        null=True, blank=True, help_text="Processed at for this WebhookEvent record."
    )
    error_code = models.CharField(
        max_length=255, null=True, blank=True, help_text="Error code for this WebhookEvent record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["processing_status", "next_retry_at"]),
            models.Index(fields=["payment", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    processing_status__in=[
                        "received",
                        "processing",
                        "processed",
                        "retry",
                        "dead_letter",
                    ]
                ),
                name="ck_webhookevent_proces",
            ),
            models.UniqueConstraint(
                fields=["merchant_account", "dedupe_key"], name="payments_webhookevent_u0"
            ),
        ]


class SettlementEntry(Record):
    """Persist settlement entry data with explicit ownership and history."""

    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payment for this SettlementEntry record.",
    )
    refund = models.ForeignKey(
        "payments.Refund",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Refund for this SettlementEntry record.",
    )
    dispute = models.ForeignKey(
        "payments.Dispute",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Dispute for this SettlementEntry record.",
    )
    merchant_account = models.ForeignKey(
        "payments.MerchantAccount",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Merchant account for this SettlementEntry record.",
    )
    beneficiary = models.CharField(
        max_length=255, default="", help_text="Beneficiary for this SettlementEntry record."
    )
    kind = models.CharField(
        max_length=255, default="", help_text="Kind for this SettlementEntry record."
    )
    direction = models.CharField(
        max_length=255, default="", help_text="Direction for this SettlementEntry record."
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Amount for this SettlementEntry record.",
    )
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Currency for this SettlementEntry record.",
    )
    provider_transaction_id = models.CharField(
        max_length=255,
        default="",
        help_text="Provider transaction id for this SettlementEntry record.",
    )
    provider_line_id = models.CharField(
        max_length=255, default="", help_text="Provider line id for this SettlementEntry record."
    )
    status = models.CharField(
        max_length=255, default="pending", help_text="Status for this SettlementEntry record."
    )
    settled_at = models.DateTimeField(
        null=True, blank=True, help_text="Settled at for this SettlementEntry record."
    )
    bank_payout_ref = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Bank payout ref for this SettlementEntry record.",
    )
    evidence_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Evidence key for this SettlementEntry record.",
    )
    reversal_of = models.OneToOneField(
        "payments.SettlementEntry",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Reversal of for this SettlementEntry record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["payment", "beneficiary"]),
            models.Index(fields=["merchant_account", "settled_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(beneficiary__in=["school", "platform", "provider"]),
                name="ck_settlemententry_benefi",
            ),
            models.CheckConstraint(
                condition=models.Q(direction__in=["credit", "debit"]),
                name="ck_settlemententry_direct",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["pending", "confirmed", "reversed"]),
                name="ck_settlemententry_status",
            ),
            models.UniqueConstraint(
                fields=["merchant_account", "provider_transaction_id", "provider_line_id"],
                name="payments_settlemententry_u0",
            ),
            models.CheckConstraint(condition=Q(amount__gte=0), name="payments_settlementen_m0"),
        ]


class ReconciliationRun(Record):
    """Persist reconciliation run data with explicit ownership and history."""

    merchant_account = models.ForeignKey(
        "payments.MerchantAccount",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Merchant account for this ReconciliationRun record.",
    )
    started_at = models.DateTimeField(
        default=timezone.now, help_text="Started at for this ReconciliationRun record."
    )
    finished_at = models.DateTimeField(
        null=True, blank=True, help_text="Finished at for this ReconciliationRun record."
    )
    period_start = models.DateTimeField(
        default=timezone.now, help_text="Period start for this ReconciliationRun record."
    )
    period_end = models.DateTimeField(
        default=timezone.now, help_text="Period end for this ReconciliationRun record."
    )
    status = models.CharField(
        max_length=255, default="running", help_text="Status for this ReconciliationRun record."
    )
    trigger = models.CharField(
        max_length=255, default="scheduled", help_text="Trigger for this ReconciliationRun record."
    )
    initiated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Initiated by for this ReconciliationRun record.",
    )
    counts = models.JSONField(
        default=dict, blank=True, help_text="Counts for this ReconciliationRun record."
    )
    report_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Report key for this ReconciliationRun record.",
    )
    error_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Error code for this ReconciliationRun record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["merchant_account", "period_start", "period_end"]),
            models.Index(fields=["status", "started_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["running", "completed", "failed"]),
                name="ck_reconciliationrun_status",
            ),
            models.UniqueConstraint(
                fields=["merchant_account"],
                condition=Q(status="running"),
                name="one_active_reconciliation",
            ),
        ]


class ReconciliationItem(Record):
    """Persist reconciliation item data with explicit ownership and history."""

    run = models.ForeignKey(
        "payments.ReconciliationRun",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Run for this ReconciliationItem record.",
    )
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Payment for this ReconciliationItem record.",
    )
    settlement_entry = models.ForeignKey(
        "payments.SettlementEntry",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Settlement entry for this ReconciliationItem record.",
    )
    source_reference = models.CharField(
        max_length=255, default="", help_text="Source reference for this ReconciliationItem record."
    )
    issue_type = models.CharField(
        max_length=255, default="", help_text="Issue type for this ReconciliationItem record."
    )
    expected_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        null=True,
        blank=True,
        help_text="Expected amount for this ReconciliationItem record.",
    )
    actual_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        null=True,
        blank=True,
        help_text="Actual amount for this ReconciliationItem record.",
    )
    currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Currency for this ReconciliationItem record.",
    )
    status = models.CharField(
        max_length=255, default="open", help_text="Status for this ReconciliationItem record."
    )
    resolution_note = models.TextField(
        null=True, blank=True, help_text="Resolution note for this ReconciliationItem record."
    )
    resolved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Resolved by for this ReconciliationItem record.",
    )
    resolved_at = models.DateTimeField(
        null=True, blank=True, help_text="Resolved at for this ReconciliationItem record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["payment", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["open", "resolved", "accepted_variance"]),
                name="ck_reconciliationite_status",
            ),
            models.UniqueConstraint(
                fields=["run", "source_reference", "issue_type"], name="payments_reconciliationi_u0"
            ),
            models.CheckConstraint(
                condition=Q(expected_amount__gte=0), name="payments_reconciliati_m0"
            ),
            models.CheckConstraint(
                condition=Q(actual_amount__gte=0), name="payments_reconciliati_m1"
            ),
        ]


class Receipt(Record):
    """Persist receipt data with explicit ownership and history."""

    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payment for this Receipt record.",
    )
    number = models.CharField(
        max_length=255, unique=True, help_text="Number for this Receipt record."
    )
    immutable_snapshot = models.JSONField(
        default=dict, blank=True, help_text="Immutable snapshot for this Receipt record."
    )
    pdf_key = models.CharField(
        max_length=255, null=True, blank=True, help_text="Pdf key for this Receipt record."
    )
    pdf_sha256 = models.CharField(
        max_length=255, null=True, blank=True, help_text="Pdf sha256 for this Receipt record."
    )
    rendering_status = models.CharField(
        max_length=255, default="pending", help_text="Rendering status for this Receipt record."
    )
    issued_at = models.DateTimeField(
        default=timezone.now, help_text="Issued at for this Receipt record."
    )
    template_version = models.CharField(
        max_length=255, default="1", help_text="Template version for this Receipt record."
    )
    last_error_code = models.CharField(
        max_length=255, null=True, blank=True, help_text="Last error code for this Receipt record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["rendering_status", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rendering_status__in=["pending", "ready", "failed"]),
                name="ck_receipt_render",
            )
        ]


class Dispute(Record):
    """Persist dispute data with explicit ownership and history."""

    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payment for this Dispute record.",
    )
    provider_reference = models.CharField(
        max_length=255, default="", help_text="Provider reference for this Dispute record."
    )
    payer_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
        help_text="Payer amount for this Dispute record.",
    )
    payer_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Payer currency for this Dispute record.",
    )
    reason = models.TextField(default="", help_text="Reason for this Dispute record.")
    status = models.CharField(
        max_length=255, default="open", help_text="Status for this Dispute record."
    )
    opened_at = models.DateTimeField(
        default=timezone.now, help_text="Opened at for this Dispute record."
    )
    response_due_at = models.DateTimeField(
        null=True, blank=True, help_text="Response due at for this Dispute record."
    )
    resolved_at = models.DateTimeField(
        null=True, blank=True, help_text="Resolved at for this Dispute record."
    )
    provider_fee = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        null=True,
        blank=True,
        help_text="Provider fee for this Dispute record.",
    )
    provider_fee_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Provider fee currency for this Dispute record.",
    )
    evidence_key = models.CharField(
        max_length=255, null=True, blank=True, help_text="Evidence key for this Dispute record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["status", "response_due_at"]),
            models.Index(fields=["payment", "opened_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["open", "won", "lost", "closed"]),
                name="ck_dispute_status",
            ),
            models.UniqueConstraint(
                fields=["payment", "provider_reference"], name="payments_dispute_u0"
            ),
            models.CheckConstraint(condition=Q(payer_amount__gte=0), name="payments_dispute_m0"),
            models.CheckConstraint(condition=Q(provider_fee__gte=0), name="payments_dispute_m1"),
        ]
