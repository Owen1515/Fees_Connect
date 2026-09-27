"""Reconcile external settlement evidence against agreed school/platform proceeds."""

from decimal import Decimal
from typing import Any

from apps.payments.models import ReconciliationItem, SettlementEntry


def check_settlement(run: Any, payment: Any) -> None:
    """Flag missing or short school proceeds; do not infer a bank payout from capture."""
    entries = SettlementEntry.objects.filter(
        payment=payment,
        status="confirmed",
        beneficiary="school",
        currency=payment.principal_currency,
        kind="school_principal",
    )
    actual = sum(
        (e.amount if e.direction == "credit" else -e.amount for e in entries), Decimal("0")
    )
    if actual != payment.principal_amount:
        ReconciliationItem.objects.get_or_create(
            run=run,
            source_reference=payment.reference,
            issue_type="split_mismatch",
            defaults={
                "payment": payment,
                "expected_amount": payment.principal_amount,
                "actual_amount": actual,
                "currency": payment.principal_currency,
                "resolution_note": "Awaiting matching school settlement evidence.",
            },
        )
    platform = SettlementEntry.objects.filter(
        payment=payment, status="confirmed", beneficiary="platform"
    )
    if not platform.exists():
        ReconciliationItem.objects.get_or_create(
            run=run,
            source_reference=payment.reference,
            issue_type="missing_platform_credit",
            defaults={
                "payment": payment,
                "currency": payment.charge_currency,
                "resolution_note": "No confirmed FeesConnect credit evidence.",
            },
        )
