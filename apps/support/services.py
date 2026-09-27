from typing import Any

from django.contrib.auth import get_user_model

"""Stable support API with deterministic guidance and optional provider substitution."""
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.services import queue_email

from .models import ChatConversation, ChatMessage, SupportTicket, TicketMessage

FAQ = [
    (
        ("pay", "payment", "fees"),
        "Open Invoices and fees, choose an invoice, enter the full or partial amount and review the total. The combined transaction charge is 3% of the school-fee amount.",
    ),
    (
        ("receipt", "invoice", "download"),
        "Invoices and payment history contain view and PDF download links. Access starts after your school verifies your pupil association.",
    ),
    (
        ("pending", "ecocash"),
        "Keep the pending page open and confirm the mobile prompt. Do not pay again while the first payment is pending. Contact support if it remains unresolved.",
    ),
    (
        ("school", "student", "child", "link"),
        "Register your school details or link a child from your account. The school verifies the association before financial records become accessible.",
    ),
    (
        ("refund",),
        "Please open a support request with your payment reference. Finance staff review refunds; the assistant cannot issue refunds or change bank details.",
    ),
]


def answer(text: str) -> str:
    """Return curated guidance without sending pupil data to an external model."""
    text = text.casefold()
    for keys, value in FAQ:
        if any(key in text for key in keys):
            return value
    return "I can explain payments, invoices, receipts and school verification. For account-specific assistance, open a support request. Never share passwords, card numbers or security codes here."


@transaction.atomic
def chat(user: Any, text: str, request_key: str, conversation_id: Any = None) -> dict:
    """Persist one idempotent user/assistant turn within the user's conversation."""
    if not text.strip() or len(text) > 2000 or not request_key or len(request_key) > 128:
        raise ValueError("Enter a message up to 2,000 characters and a request identifier.")
    if conversation_id:
        conversation = ChatConversation.objects.select_for_update().get(
            pk=conversation_id, user=user
        )
    else:
        # Lock user creation of initial turns so a retried key cannot create two conversations.
        get_user_model().objects.select_for_update().get(pk=user.pk)
        old = ChatMessage.objects.filter(
            conversation__user=user, request_key=request_key, role="assistant"
        ).first()
        if old:
            return {"conversation_id": str(old.conversation_id), "reply": old.content}
        conversation = ChatConversation.objects.create(
            user=user,
            retention_until=timezone.now() + timedelta(days=90),
            last_activity_at=timezone.now(),
        )
    old = ChatMessage.objects.filter(
        conversation=conversation, request_key=request_key, role="assistant"
    ).first()
    if old:
        return {"conversation_id": str(conversation.pk), "reply": old.content}
    sequence = ChatMessage.objects.filter(conversation=conversation).count() + 1
    ChatMessage.objects.create(
        conversation=conversation,
        role="user",
        sequence=sequence,
        content=text,
        request_key=request_key,
    )
    reply = answer(text)
    ChatMessage.objects.create(
        conversation=conversation,
        role="assistant",
        sequence=sequence + 1,
        content=reply,
        request_key=request_key,
        provider="curated-faq",
    )
    conversation.last_activity_at = timezone.now()
    conversation.save()
    return {"conversation_id": str(conversation.pk), "reply": reply}


@transaction.atomic
def ticket(user: Any, subject: str, body: str) -> Any:
    """Open a user-owned support ticket and queue an acknowledgement."""
    record = SupportTicket.objects.create(
        reference="FC-S-" + uuid.uuid4().hex[:12].upper(), opened_by=user, subject=subject
    )
    TicketMessage.objects.create(ticket=record, author=user, body=body)
    queue_email(user, "support", {"reference": record.reference}, "ticket:" + str(record.pk))
    return record
