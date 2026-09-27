"""Explicit schema for the support domain; financial writes use services."""

from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.base import Record


class SupportTicket(Record):
    """Persist support ticket data with explicit ownership and history."""

    reference = models.CharField(
        max_length=255, unique=True, help_text="Reference for this SupportTicket record."
    )
    opened_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Opened by for this SupportTicket record.",
    )
    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="School for this SupportTicket record.",
    )
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Payment for this SupportTicket record.",
    )
    subject = models.CharField(
        max_length=255, default="", help_text="Subject for this SupportTicket record."
    )
    category = models.CharField(
        max_length=255, default="general", help_text="Category for this SupportTicket record."
    )
    status = models.CharField(
        max_length=255, default="open", help_text="Status for this SupportTicket record."
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Assigned to for this SupportTicket record.",
    )
    resolved_at = models.DateTimeField(
        null=True, blank=True, help_text="Resolved at for this SupportTicket record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["opened_by", "created_at"]),
            models.Index(fields=["school", "status"]),
            models.Index(fields=["assigned_to", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["open", "in_progress", "waiting", "resolved", "closed"]
                ),
                name="ck_supportticket_status",
            )
        ]


class TicketMessage(Record):
    """Persist ticket message data with explicit ownership and history."""

    ticket = models.ForeignKey(
        "support.SupportTicket",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Ticket for this TicketMessage record.",
    )
    author = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Author for this TicketMessage record.",
    )
    author_kind = models.CharField(
        max_length=255, default="user", help_text="Author kind for this TicketMessage record."
    )
    body = models.TextField(default="", help_text="Body for this TicketMessage record.")
    visibility = models.CharField(
        max_length=255, default="requester", help_text="Visibility for this TicketMessage record."
    )
    sent_at = models.DateTimeField(
        default=timezone.now, help_text="Sent at for this TicketMessage record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["ticket", "sent_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(visibility__in=["requester", "internal"]),
                name="ck_ticketmessage_visibi",
            )
        ]


class ChatConversation(Record):
    """Persist chat conversation data with explicit ownership and history."""

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="User for this ChatConversation record.",
    )
    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="School for this ChatConversation record.",
    )
    status = models.CharField(
        max_length=255, default="open", help_text="Status for this ChatConversation record."
    )
    ticket = models.OneToOneField(
        "support.SupportTicket",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Ticket for this ChatConversation record.",
    )
    consent_version = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Consent version for this ChatConversation record.",
    )
    retention_until = models.DateTimeField(
        default=timezone.now, help_text="Retention until for this ChatConversation record."
    )
    last_activity_at = models.DateTimeField(
        default=timezone.now, help_text="Last activity at for this ChatConversation record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [
            models.Index(fields=["user", "last_activity_at"]),
            models.Index(fields=["retention_until"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["open", "closed", "escalated"]),
                name="ck_chatconversation_status",
            )
        ]


class ChatMessage(Record):
    """Persist chat message data with explicit ownership and history."""

    conversation = models.ForeignKey(
        "support.ChatConversation",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Conversation for this ChatMessage record.",
    )
    role = models.CharField(
        max_length=255, default="", help_text="Role for this ChatMessage record."
    )
    sequence = models.PositiveIntegerField(
        default=0, help_text="Sequence for this ChatMessage record."
    )
    content = models.TextField(default="", help_text="Content for this ChatMessage record.")
    request_key = models.CharField(
        max_length=255, null=True, blank=True, help_text="Request key for this ChatMessage record."
    )
    status = models.CharField(
        max_length=255, default="completed", help_text="Status for this ChatMessage record."
    )
    provider = models.CharField(
        max_length=255, null=True, blank=True, help_text="Provider for this ChatMessage record."
    )
    model_name = models.CharField(
        max_length=255, null=True, blank=True, help_text="Model name for this ChatMessage record."
    )
    upstream_request_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Upstream request id for this ChatMessage record.",
    )
    token_usage = models.JSONField(
        default=dict, blank=True, help_text="Token usage for this ChatMessage record."
    )
    redacted_error_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Redacted error code for this ChatMessage record.",
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["conversation", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["user", "assistant", "system"]),
                name="ck_chatmessage_role",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["pending", "completed", "failed"]),
                name="ck_chatmessage_status",
            ),
            models.UniqueConstraint(
                fields=["conversation", "request_key", "role"],
                condition=Q(request_key__isnull=False),
                name="chat_request_dedupe",
            ),
            models.UniqueConstraint(
                fields=["conversation", "sequence"], name="support_chatmessage_u0"
            ),
        ]
