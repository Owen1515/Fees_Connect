"""Revoke stale sessions and require 2FA before privileged account use."""

import time
from typing import Any

from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpRequest
from django.shortcuts import redirect

from .access import is_operator, school_ids


class AccountSecurityMiddleware:
    """Enforce inactivity and auth-version checks centrally."""

    def __init__(self, get_response: Any) -> None:
        """Store the next middleware callable."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        """Invalidate stale sessions; guide privileged users through OTP setup."""
        if request.user.is_authenticated:
            last = request.session.get("last_activity", time.time())
            if (
                request.session.get("auth_version", request.user.auth_version)
                != request.user.auth_version
                or time.time() - last > 1800
            ):
                logout(request)
                return redirect("accounts:login")
            request.session["last_activity"] = time.time()
            request.session["auth_version"] = request.user.auth_version
            privileged = (
                request.user.is_staff
                or is_operator(request.user)
                or school_ids(request.user).exists()
            )
            if (
                privileged
                and getattr(settings, "ENFORCE_ADMIN_2FA", True)
                and not request.user.is_verified()
            ):
                if request.path not in [
                    "/accounts/2fa/setup/",
                    "/accounts/2fa/verify/",
                    "/accounts/logout/",
                ]:
                    return redirect("accounts:otp_setup")
        return self.get_response(request)
