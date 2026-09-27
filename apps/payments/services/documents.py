"""Private receipt and invoice rendering with no arbitrary network fetching."""

import hashlib
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template.loader import render_to_string

from apps.payments.models import Receipt


def pdf_bytes(template: str, context: dict) -> bytes:
    """Render escaped document HTML; disallow external or user-supplied resources."""
    from weasyprint import HTML

    def deny_fetch(url: Any, *args: Any, **kwargs: Any) -> Any:
        """Reject all external resources; document styles are embedded and fixed."""
        raise ValueError("External PDF resources are disabled.")

    return HTML(string=render_to_string(template, context), url_fetcher=deny_fetch).write_pdf()


def receipt_pdf(receipt: Receipt) -> bytes:
    """Generate once, store privately and return verified receipt bytes."""
    if receipt.pdf_key and default_storage.exists(receipt.pdf_key):
        with default_storage.open(receipt.pdf_key, "rb") as stream:
            return stream.read()
    content = pdf_bytes(
        "payments/receipt_pdf.html", {"receipt": receipt, "data": receipt.immutable_snapshot}
    )
    key = default_storage.save(f"receipts/{receipt.pk}.pdf", ContentFile(content))
    receipt.pdf_key = key
    receipt.pdf_sha256 = hashlib.sha256(content).hexdigest()
    receipt.rendering_status = "ready"
    receipt.save()
    return content
