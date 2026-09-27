from decimal import Decimal
from typing import Any

"""Payment forms validate amounts before the service repeats financial checks."""

from django import forms

from apps.accounts.forms import BrandForm

from .models import MerchantAccount


class CheckoutForm(BrandForm):
    """Choose an eligible school merchant and a payer-funded fee amount."""

    amount = forms.DecimalField(max_digits=20, decimal_places=2, min_value=Decimal("0.01"))
    merchant = forms.ModelChoiceField(
        queryset=MerchantAccount.objects.none(), label="Payment provider"
    )
    method = forms.ChoiceField(
        choices=[
            ("card", "Visa / Mastercard / virtual card"),
            ("paypal", "PayPal"),
            ("ecocash", "EcoCash"),
            ("onemoney", "OneMoney"),
            ("bank", "Bank transfer"),
            ("hosted", "Other Paynow methods"),
            ("sepa_debit", "SEPA"),
        ]
    )
    currency = forms.ChoiceField(
        choices=[("USD", "USD"), ("ZWG", "ZiG"), ("GBP", "GBP"), ("EUR", "EUR")]
    )
    phone = forms.RegexField(
        regex=r"^\+?[0-9]{7,15}$", required=False, label="Mobile money phone number"
    )

    def __init__(self, *args: Any, invoice: Any = None, **kwargs: Any) -> None:
        """Restrict merchant choices to this invoice's school and currency."""
        super().__init__(*args, **kwargs)
        self.fields["merchant"].queryset = MerchantAccount.objects.filter(
            school=invoice.school, status="enabled", settlement_currency=invoice.currency
        )

    def clean(self) -> Any:
        """Require a phone for mobile push payment methods."""
        data = super().clean()
        if data.get("method") in ["ecocash", "onemoney"] and not data.get("phone"):
            self.add_error("phone", "Enter your mobile money number.")
        return data
