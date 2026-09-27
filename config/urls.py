"""Canonical namespaced routes and compatibility paths for every uploaded HTML file."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.core import views as errors

handler403 = errors.error403
handler404 = errors.error404
handler500 = errors.error500
urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("account/", include("apps.dashboard.urls")),
    path("fees/", include("apps.fees.urls")),
    path("payments/", include("apps.payments.urls")),
    path("support/", include("apps.support.urls")),
    path("api/", include("apps.api.urls")),
    path("", include("apps.core.urls")),
]
# Old HTML URLs redirect to the canonical view; none are silently dropped.
ALIASES = {
    "index": "core:home",
    "home": "core:home",
    "auth": "accounts:login",
    "login": "accounts:login",
    "register": "accounts:register",
    "account": "dashboard:home",
    "demo": "core:demo",
    "privacy": "core:privacy",
    "forgot-password": "accounts:reset_request",
    "resend-verification": "accounts:resend",
    "reset": "accounts:reset_request",
    "verify": "accounts:resend",
}
for old, name in ALIASES.items():
    urlpatterns.append(
        path(
            old + ".html",
            RedirectView.as_view(pattern_name=name, permanent=False),
            name="legacy_" + old,
        )
    )
