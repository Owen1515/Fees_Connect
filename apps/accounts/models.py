"""Explicit schema for the accounts domain; financial writes use services."""

from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.base import Record


class RoleAssignment(Record):
    """Persist role assignment data with explicit ownership and history."""

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="User for this RoleAssignment record.",
    )
    group = models.ForeignKey(
        "auth.Group",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Group for this RoleAssignment record.",
    )
    school = models.ForeignKey(
        "fees.School",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="School for this RoleAssignment record.",
    )
    status = models.CharField(
        max_length=255, default="active", help_text="Status for this RoleAssignment record."
    )
    granted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Granted by for this RoleAssignment record.",
    )
    granted_at = models.DateTimeField(
        default=timezone.now, help_text="Granted at for this RoleAssignment record."
    )
    revoked_at = models.DateTimeField(
        null=True, blank=True, help_text="Revoked at for this RoleAssignment record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["school", "status", "user"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["active", "revoked"]),
                name="ck_roleassignment_status",
            ),
            models.UniqueConstraint(
                fields=["user", "group", "school"],
                condition=Q(status="active", school__isnull=False),
                name="role_school_active",
            ),
            models.UniqueConstraint(
                fields=["user", "group"],
                condition=Q(status="active", school__isnull=True),
                name="role_global_active",
            ),
        ]


class AccountToken(Record):
    """Persist account token data with explicit ownership and history."""

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="User for this AccountToken record.",
    )
    purpose = models.CharField(
        max_length=255, default="", help_text="Purpose for this AccountToken record."
    )
    token_digest = models.CharField(
        max_length=255, unique=True, help_text="Token digest for this AccountToken record."
    )
    email_snapshot = models.EmailField(
        max_length=254, help_text="Email snapshot for this AccountToken record."
    )
    expires_at = models.DateTimeField(
        default=timezone.now, help_text="Expires at for this AccountToken record."
    )
    consumed_at = models.DateTimeField(
        null=True, blank=True, help_text="Consumed at for this AccountToken record."
    )
    revoked_at = models.DateTimeField(
        null=True, blank=True, help_text="Revoked at for this AccountToken record."
    )
    issued_auth_version = models.PositiveIntegerField(
        default=0, help_text="Issued auth version for this AccountToken record."
    )

    class Meta:
        """Declare database guarantees and query indexes."""

        indexes = [models.Index(fields=["user", "purpose", "expires_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(purpose__in=["verification", "password_reset"]),
                name="ck_accounttoken_purpos",
            )
        ]


from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db.models.functions import Lower

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, Record):
    """Email identity; permissions additionally require verified pupil or school scope."""

    email = models.EmailField(unique=True, help_text="Canonical lowercase login address.")
    full_name = models.CharField(max_length=160, help_text="User-provided display name.")
    phone = models.CharField(max_length=32, blank=True, help_text="Optional contact number.")
    email_verified_at = models.DateTimeField(
        null=True, blank=True, help_text="Successful email challenge timestamp."
    )
    is_active = models.BooleanField(default=True, help_text="Whether authentication is allowed.")
    is_staff = models.BooleanField(
        default=False, help_text="Access to the restricted operator admin site."
    )
    date_joined = models.DateTimeField(default=timezone.now, help_text="Account creation date.")
    preferred_currency = models.ForeignKey(
        "core.Currency",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        help_text="Preferred display currency.",
    )
    locale = models.CharField(max_length=12, default="en-gb", help_text="Language preference.")
    auth_version = models.PositiveIntegerField(
        default=0, help_text="Increment to invalidate prior sessions and tokens."
    )
    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        """Enforce case-insensitive identity independently of form validation."""

        constraints = [models.UniqueConstraint(Lower("email"), name="user_email_casefold_unique")]
        indexes = [models.Index(fields=["is_active", "created_at"])]
