"""Common persisted record identity and timestamp conventions."""

import uuid

from django.db import models


class Record(models.Model):
    """Abstract base shared by auditable business records."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Opaque stable record identifier.",
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="UTC creation timestamp.")
    updated_at = models.DateTimeField(auto_now=True, help_text="UTC last write timestamp.")

    class Meta:
        """Do not create a table for the abstract base."""

        abstract = True

    def __str__(self) -> str:
        """Return an operator-friendly reference without exposing personal data."""
        return str(
            getattr(self, "display_name", None)
            or getattr(self, "reference", None)
            or getattr(self, "number", None)
            or getattr(self, "gateway", None)
            or self.pk
        )
