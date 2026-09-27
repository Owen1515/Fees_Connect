"""Versioned-by-contract session-authenticated API for first-party integrations."""

from typing import Any

from django.http import HttpRequest
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.access import invoices_for, payments_for
from apps.fees.services import balance
from apps.support.services import chat


class ChatInput(serializers.Serializer):
    """Validate external chat payloads before service invocation."""

    message = serializers.CharField(max_length=2000)
    request_id = serializers.CharField(max_length=128)
    conversation_id = serializers.UUIDField(required=False)


class ChatView(APIView):
    """Expose the stable authenticated support bridge."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat"

    def post(self, request: HttpRequest) -> Any:
        """Return a scoped idempotent reply; private conversations cannot be guessed."""
        data = ChatInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            result = chat(
                request.user,
                data.validated_data["message"],
                data.validated_data["request_id"],
                data.validated_data.get("conversation_id"),
            )
        except Exception as exc:
            from apps.support.models import ChatConversation

            if isinstance(exc, ChatConversation.DoesNotExist):
                return Response({"detail": "Conversation not found."}, status=404)
            raise
        return Response(result)


class PaymentListView(APIView):
    """Read scoped payment records without exposing metadata or provider secrets."""

    def get(self, request: HttpRequest) -> Any:
        """Return a bounded latest-payment listing."""
        return Response(
            [
                {
                    "id": str(p.pk),
                    "reference": p.reference,
                    "amount": str(p.amount),
                    "currency": p.currency_id,
                    "status": p.status,
                }
                for p in payments_for(request.user).order_by("-created_at")[:100]
            ]
        )


class InvoiceListView(APIView):
    """Read authorised invoices for a future first-party client."""

    def get(self, request: HttpRequest) -> Any:
        """Return principal liability and outstanding balance in invoice currency."""
        return Response(
            [
                {
                    "id": str(i.pk),
                    "number": i.number,
                    "currency": i.currency_id,
                    "total": str(i.total_amount),
                    "balance": str(balance(i)),
                }
                for i in invoices_for(request.user).order_by("-created_at")[:100]
            ]
        )
