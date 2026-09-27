"""Apply a restrictive browser policy to HTML and API responses."""

from typing import Any

from django.http import HttpRequest


class SecurityHeadersMiddleware:
    """Keep scripts local and protect same-origin forms and document access."""

    def __init__(self, get_response: Any) -> None:
        """Store the next middleware callable."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        """Attach security headers without modifying application content."""
        response = self.get_response(request)
        response["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        response["Referrer-Policy"] = "same-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.user.is_authenticated:
            response["Cache-Control"] = "private, no-store"
        return response


class TrustedProxyMiddleware:
    """Accept the client IP only behind the configured local trusted Nginx boundary."""

    def __init__(self, get_response: Any) -> None:
        """Store the next request handler."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        """Validate Nginx's overwritten X-Real-IP before using it for throttles."""
        import ipaddress

        from django.conf import settings

        if getattr(settings, "TRUST_PROXY_HEADERS", False):
            candidate = request.META.get("HTTP_X_REAL_IP", "")
            try:
                request.META["REMOTE_ADDR"] = str(ipaddress.ip_address(candidate))
            except ValueError:
                pass
        return self.get_response(request)
