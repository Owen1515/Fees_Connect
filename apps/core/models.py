"""Explicit schema for the core domain; financial writes use services."""

from django.db import models
from django.utils import timezone

from apps.core.base import Record


class Currency(Record):
    id = None  # ISO code replaces the UUID inherited by other records.
    """Persist currency data with explicit ownership and history."""
    code = models.CharField(
        max_length=3, primary_key=True, help_text="Code for this Currency record."
    )
    display_name = models.CharField(
        max_length=255, default="", help_text="Display name for this Currency record."
    )
    symbol = models.CharField(
        max_length=255, default="", help_text="Symbol for this Currency record."
    )
    minor_units = models.PositiveIntegerField(
        default=2, help_text="Minor units for this Currency record."
    )
    is_active = models.BooleanField(default=True, help_text="Is active for this Currency record.")

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = []
        constraints = []


class AuditEvent(Record):
    """Persist audit event data with explicit ownership and history."""

    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Actor for this AuditEvent record.",
    )
    actor_snapshot = models.CharField(
        max_length=255, default="", help_text="Actor snapshot for this AuditEvent record."
    )
    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="School for this AuditEvent record.",
    )
    action = models.CharField(
        max_length=255, default="", help_text="Action for this AuditEvent record."
    )
    target_type = models.CharField(
        max_length=255, default="", help_text="Target type for this AuditEvent record."
    )
    target_id = models.CharField(
        max_length=255, null=True, blank=True, help_text="Target id for this AuditEvent record."
    )
    correlation_id = models.CharField(
        max_length=255, default="", help_text="Correlation id for this AuditEvent record."
    )
    occurred_at = models.DateTimeField(
        default=timezone.now, help_text="Occurred at for this AuditEvent record."
    )
    redacted_changes = models.JSONField(
        default=dict, blank=True, help_text="Redacted changes for this AuditEvent record."
    )
    outcome = models.CharField(
        max_length=255, default="success", help_text="Outcome for this AuditEvent record."
    )
    ip_digest = models.CharField(
        max_length=255, null=True, blank=True, help_text="Ip digest for this AuditEvent record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["school", "occurred_at"]),
            models.Index(fields=["actor", "occurred_at"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["correlation_id"]),
        ]
        constraints = []


class OutboxMessage(Record):
    """Persist outbox message data with explicit ownership and history."""

    kind = models.CharField(
        max_length=255, default="email", help_text="Kind for this OutboxMessage record."
    )
    topic = models.CharField(
        max_length=255, default="", help_text="Topic for this OutboxMessage record."
    )
    dedupe_key = models.CharField(
        max_length=255, unique=True, help_text="Dedupe key for this OutboxMessage record."
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="User for this OutboxMessage record.",
    )
    aggregate_type = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Aggregate type for this OutboxMessage record.",
    )
    aggregate_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Aggregate id for this OutboxMessage record.",
    )
    template_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Template name for this OutboxMessage record.",
    )
    template_version = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Template version for this OutboxMessage record.",
    )
    encrypted_payload_key = models.TextField(
        default="", help_text="Encrypted payload key for this OutboxMessage record."
    )
    attachment_keys = models.JSONField(
        default=dict, blank=True, help_text="Attachment keys for this OutboxMessage record."
    )
    state = models.CharField(
        max_length=255, default="pending", help_text="State for this OutboxMessage record."
    )
    attempt_count = models.PositiveIntegerField(
        default=0, help_text="Attempt count for this OutboxMessage record."
    )
    next_attempt_at = models.DateTimeField(
        null=True, blank=True, help_text="Next attempt at for this OutboxMessage record."
    )
    locked_until = models.DateTimeField(
        null=True, blank=True, help_text="Locked until for this OutboxMessage record."
    )
    sent_at = models.DateTimeField(
        null=True, blank=True, help_text="Sent at for this OutboxMessage record."
    )
    provider_message_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Provider message id for this OutboxMessage record.",
    )
    last_error_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Last error code for this OutboxMessage record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["state", "next_attempt_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(kind__in=["email", "task"]), name="ck_outboxmessage_kind"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    state__in=["pending", "processing", "sent", "retry", "dead_letter"]
                ),
                name="ck_outboxmessage_state",
            ),
        ]


class ImportBatch(Record):
    """Persist import batch data with explicit ownership and history."""

    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="School for this ImportBatch record.",
    )
    data_kind = models.CharField(
        max_length=255, default="", help_text="Data kind for this ImportBatch record."
    )
    source_filename = models.CharField(
        max_length=255, default="", help_text="Source filename for this ImportBatch record."
    )
    source_sha256 = models.CharField(
        max_length=255, default="", help_text="Source sha256 for this ImportBatch record."
    )
    source_system = models.CharField(
        max_length=255, default="", help_text="Source system for this ImportBatch record."
    )
    schema_version = models.CharField(
        max_length=255, default="1", help_text="Schema version for this ImportBatch record."
    )
    effective_cutover_at = models.DateTimeField(
        default=timezone.now, help_text="Effective cutover at for this ImportBatch record."
    )
    submitted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Submitted by for this ImportBatch record.",
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Approved by for this ImportBatch record.",
    )
    status = models.CharField(
        max_length=255, default="uploaded", help_text="Status for this ImportBatch record."
    )
    dry_run_report_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Dry run report key for this ImportBatch record.",
    )
    source_key = models.CharField(
        max_length=255, default="", help_text="Source key for this ImportBatch record."
    )
    totals = models.JSONField(
        default=dict, blank=True, help_text="Totals for this ImportBatch record."
    )
    applied_at = models.DateTimeField(
        null=True, blank=True, help_text="Applied at for this ImportBatch record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["school", "status", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "uploaded",
                        "validated",
                        "rejected",
                        "applying",
                        "completed",
                        "failed",
                    ]
                ),
                name="ck_importbatch_status",
            )
        ]


class ImportRow(Record):
    """Persist import row data with explicit ownership and history."""

    batch = models.ForeignKey(
        "core.ImportBatch",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Batch for this ImportRow record.",
    )
    row_number = models.PositiveIntegerField(
        default=0, help_text="Row number for this ImportRow record."
    )
    external_id = models.CharField(
        max_length=255, null=True, blank=True, help_text="External id for this ImportRow record."
    )
    row_digest = models.CharField(
        max_length=255, default="", help_text="Row digest for this ImportRow record."
    )
    encrypted_source_key = models.TextField(
        default="", help_text="Encrypted source key for this ImportRow record."
    )
    validation_errors = models.JSONField(
        default=dict, blank=True, help_text="Validation errors for this ImportRow record."
    )
    status = models.CharField(
        max_length=255, default="pending", help_text="Status for this ImportRow record."
    )
    target_type = models.CharField(
        max_length=255, null=True, blank=True, help_text="Target type for this ImportRow record."
    )
    target_id = models.CharField(
        max_length=255, null=True, blank=True, help_text="Target id for this ImportRow record."
    )
    applied_at = models.DateTimeField(
        null=True, blank=True, help_text="Applied at for this ImportRow record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["batch", "status"]),
            models.Index(fields=["target_type", "target_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["pending", "valid", "invalid", "applied", "skipped"]
                ),
                name="ck_importrow_status",
            ),
            models.UniqueConstraint(fields=["batch", "row_number"], name="core_importrow_u0"),
        ]
