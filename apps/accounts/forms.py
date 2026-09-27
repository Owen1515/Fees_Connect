"""Forms retain the uploaded FeesConnect input and button conventions."""

from typing import Any

from crispy_forms.helper import FormHelper
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password


class BrandForm(forms.Form):
    """Provide one consistent crispy form presentation."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Attach template styling without Bootstrap's global CSS reset."""
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class RegisterForm(BrandForm):
    """Validate public account creation with unprivileged role choices."""

    email = forms.EmailField()
    full_name = forms.CharField(max_length=160)
    role = forms.ChoiceField(choices=[("parent", "Parent / guardian"), ("student", "Student")])
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    agree = forms.BooleanField(label="I accept the Terms and Privacy information.")

    def clean(self) -> Any:
        """Validate matching, strong passwords before any account is persisted."""
        data = super().clean()
        if data.get("password") != data.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        if data.get("password"):
            validate_password(data["password"])
        return data


class LoginForm(AuthenticationForm):
    """Authenticate email/password while protecting unverified accounts."""

    username = forms.EmailField(label="Email address")

    def clean_username(self) -> str:
        """Normalise email case before the authentication backend lookup."""
        return self.cleaned_data["username"].strip().lower()

    def confirm_login_allowed(self, user: Any) -> Any:
        """Require email ownership before starting an authenticated session."""
        super().confirm_login_allowed(user)
        if not user.email_verified_at:
            raise forms.ValidationError("Verify your email before logging in.")


class EmailForm(BrandForm):
    """Request account recovery without revealing account existence."""

    email = forms.EmailField()


class ResetForm(BrandForm):
    """Collect matching replacement passwords."""

    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self) -> Any:
        """Return strong matching values or attach readable validation errors."""
        data = super().clean()
        if data.get("password") != data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        if data.get("password"):
            validate_password(data["password"])
        return data


class OTPForm(BrandForm):
    """Accept a TOTP code or one-use recovery code."""

    token = forms.CharField(max_length=64, label="Authenticator or recovery code")


class ProfileForm(BrandForm):
    """Edit non-privileged contact fields only."""

    full_name = forms.CharField(max_length=160)
    phone = forms.CharField(max_length=32, required=False)
