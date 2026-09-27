"""Thin HTML authentication controllers using Django CSRF and service validation."""

from typing import Any

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django_otp import login as otp_login
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.core.security import throttle
from apps.core.services import audit

from . import forms, services
from .models import User


def form_page(request: HttpRequest, template: Any, form: Any, title: Any, **extra: Any) -> Any:
    """Render an uploaded/auth-matching form template with escaped errors."""
    return render(request, template, {"form": form, "title": title, **extra})


def register(request: HttpRequest) -> Any:
    """Register public parent/student accounts and queue verification asynchronously."""
    form = forms.RegisterForm(request.POST or None)
    if request.method == "POST":
        throttle(request, "register", 5)
        if form.is_valid():
            try:
                services.register(
                    **{k: form.cleaned_data[k] for k in ["email", "full_name", "password", "role"]}
                )
            except IntegrityError:
                pass  # A concurrent duplicate remains indistinguishable.
            return redirect("accounts:verification_sent")
    return form_page(request, "feesconnect/register.html", form, "Create your account")


def login(request: HttpRequest) -> Any:
    """Start a session only after password and any enrolled OTP challenge succeed."""
    form = forms.LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            request.session.cycle_key()
            request.session["otp_pending_user"] = str(user.pk)
            request.session.set_expiry(300)
            return redirect("accounts:otp_verify")
        auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        audit(user, "login", user)
        return redirect("dashboard:home")
    return form_page(request, "feesconnect/login.html", form, "Welcome back")


@require_POST
def logout(request: HttpRequest) -> Any:
    """Destroy the session only on a CSRF-protected POST."""
    audit(request.user, "logout")
    auth_logout(request)
    return redirect("core:home")


def request_token(request: HttpRequest, purpose: Any = "password_reset") -> Any:
    """Issue recovery/verification email using an identical public response."""
    form = forms.EmailForm(request.POST or None)
    if request.method == "POST":
        throttle(request, "account-email", 5)
        if form.is_valid():
            user = User.objects.filter(
                email__iexact=form.cleaned_data["email"], is_active=True
            ).first()
            if user and (purpose == "verification" or user.email_verified_at):
                services.issue_token(user, purpose)
            return redirect(
                "accounts:verification_sent" if purpose == "verification" else "accounts:reset_sent"
            )
    template = "resend-verification" if purpose == "verification" else "forgot-password"
    return form_page(
        request,
        f"feesconnect/{template}.html",
        form,
        "Verify your email" if purpose == "verification" else "Reset your password",
    )


def verify(request: HttpRequest, token: Any) -> Any:
    """Consume email verification on explicit POST, avoiding email-scanner activation."""
    if request.method == "POST":
        try:
            services.consume_token(token, "verification")
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            return redirect("accounts:verification_confirmed")
    return form_page(request, "feesconnect/verify.html", None, "Confirm your email")


def reset_confirm(request: HttpRequest, token: Any) -> Any:
    """Set a strong replacement password and invalidate old sessions."""
    form = forms.ResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.consume_token(token, "password_reset", form.cleaned_data["password"])
        except (ValueError, ValidationError) as exc:
            form.add_error(None, str(exc))
        else:
            return redirect("accounts:reset_complete")
    return form_page(request, "feesconnect/reset.html", form, "Choose a new password")


def otp_verify(request: HttpRequest) -> Any:
    """Validate an enrolled device under row lock and prevent OTP replay."""
    user = (
        request.user
        if request.user.is_authenticated
        else (
            User.objects.filter(pk=request.session.get("otp_pending_user")).first()
            if request.session.get("otp_pending_user")
            else None
        )
    )
    if not user or not user.is_active:
        return redirect("accounts:login")
    form = forms.OTPForm(request.POST or None)
    if request.method == "POST":
        throttle(request, "otp", 10)
        if form.is_valid():
            with transaction.atomic():
                devices = list(
                    TOTPDevice.objects.select_for_update().filter(user=user, confirmed=True)
                )
                devices += list(StaticDevice.objects.select_for_update().filter(user=user))
                for device in devices:
                    if device.verify_token(form.cleaned_data["token"]):
                        auth_login(
                            request, user, backend="django.contrib.auth.backends.ModelBackend"
                        )
                        otp_login(request, device)
                        request.session.pop("otp_pending_user", None)
                        request.session.set_expiry(43200)
                        audit(user, "otp_login", user)
                        return redirect("dashboard:home")
            form.add_error("token", "Invalid or expired code.")
    return form_page(request, "accounts/otp_verify.html", form, "Two-factor verification")


@login_required
def otp_setup(request: HttpRequest) -> Any:
    """Enroll an authenticator; show recovery codes once after successful proof."""
    if TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
        return redirect("accounts:otp_verify")
    device, _ = TOTPDevice.objects.get_or_create(
        user=request.user, name="authenticator", confirmed=False
    )
    form = forms.OTPForm(request.POST or None)
    if request.method == "POST":
        throttle(request, "otp-setup", 10)
        if form.is_valid():
            with transaction.atomic():
                device = TOTPDevice.objects.select_for_update().get(pk=device.pk)
                if device.verify_token(form.cleaned_data["token"]):
                    device.confirmed = True
                    device.save()
                    otp_login(request, device)
                    backup = StaticDevice.objects.create(user=request.user, name="recovery")
                    codes = [StaticToken.random_token() for _ in range(10)]
                    for code in codes:
                        StaticToken.objects.create(device=backup, token=code)
                    return render(
                        request,
                        "accounts/recovery.html",
                        {"codes": codes, "title": "Save your recovery codes"},
                    )
            form.add_error("token", "Invalid code.")
    import base64
    import io

    import qrcode

    image = io.BytesIO()
    qrcode.make(device.config_url).save(image, format="PNG")
    qr_data = "data:image/png;base64," + base64.b64encode(image.getvalue()).decode()
    return form_page(
        request,
        "accounts/otp_setup.html",
        form,
        "Set up two-factor authentication",
        otp_uri=device.config_url,
        qr_data=qr_data,
        secret=device.key,
    )


@login_required
def profile(request: HttpRequest) -> Any:
    """Update contact fields; email/role changes require separate verification."""
    form = forms.ProfileForm(
        request.POST or None,
        initial={"full_name": request.user.full_name, "phone": request.user.phone},
    )
    if request.method == "POST" and form.is_valid():
        for key, value in form.cleaned_data.items():
            setattr(request.user, key, value)
        request.user.save()
        audit(request.user, "profile_updated", request.user)
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return form_page(request, "accounts/profile.html", form, "Profile and settings")


@login_required
def password_change(request: HttpRequest) -> Any:
    """Require the current password and invalidate all prior sessions on success."""
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.auth_version += 1
        user.save(update_fields=["auth_version"])
        audit(user, "password_changed", user)
        auth_logout(request)
        return redirect("accounts:login")
    return form_page(request, "accounts/profile.html", form, "Change password")
