"""Production settings for both Render and the documented private-Nginx VPS."""

import ssl

import sentry_sdk
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

from config.deployment import https_origin, production_secret

from .base import *  # noqa: F403

# Preserve valid existing secrets and accept Render's 256-bit generated key format.
SECRET_KEY = production_secret(SECRET_KEY)  # noqa: F405

# Report all missing deployment credentials together, without printing any values.
_configuration_errors = []
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":  # noqa: F405
    _configuration_errors.append("DATABASE_URL must point to PostgreSQL")
try:
    Fernet(DATA_ENCRYPTION_KEY.encode("ascii"))  # noqa: F405
except (ValueError, TypeError, UnicodeEncodeError):
    _configuration_errors.append("DATA_ENCRYPTION_KEY must be a valid 32-byte Fernet key")
for _name in ("MS_TENANT_ID", "MS_CLIENT_ID", "MS_CLIENT_SECRET"):
    if not globals()[_name]:
        _configuration_errors.append(f"{_name} is required for Microsoft 365 OAuth2")
if not env("REDIS_URL", default=""):  # noqa: F405
    _configuration_errors.append("REDIS_URL must be supplied for shared throttles and Celery")
if _configuration_errors:
    raise ImproperlyConfigured("Production configuration: " + "; ".join(_configuration_errors))

# SITE_URL is shared with workers so email links and gateway returns agree.
_public_hostname = https_origin(SITE_URL)  # noqa: F405
_render_hostname = env("RENDER_EXTERNAL_HOSTNAME", default="")  # noqa: F405
ALLOWED_HOSTS = list(
    dict.fromkeys(
        [*ALLOWED_HOSTS, _public_hostname]  # noqa: F405
        + ([_render_hostname] if _render_hostname else [])
    )
)
CSRF_TRUSTED_ORIGINS = list(
    dict.fromkeys(
        env.list(  # noqa: F405
            "CSRF_TRUSTED_ORIGINS",
            default=["https://feesconnect.com", "https://www.feesconnect.com"],
        )
        + [SITE_URL]  # noqa: F405
        + ([f"https://{_render_hostname}"] if _render_hostname else [])
    )
)

# TLS terminates at Render's edge or the supplied private VPS Nginx proxy.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Status-only probes must execute checks rather than return a misleading 301.
SECURE_REDIRECT_EXEMPT = [r"^healthz/$", r"^readyz/$"]
# X-Real-IP is safe only if an operator's own Nginx overwrites it. Render does not
# use that VPS assumption; leave this false unless the private proxy is verified.
TRUST_PROXY_HEADERS = env.bool("TRUST_PROXY_HEADERS", default=False)  # noqa: F405

# Bound datastore connection delays so failed readiness probes do not hang.
DATABASES["default"].setdefault("OPTIONS", {}).setdefault("connect_timeout", 3)  # noqa: F405
CACHES["default"]["OPTIONS"] = {"socket_connect_timeout": 2, "socket_timeout": 2}  # noqa: F405
# External TLS Redis URLs must validate certificates; internal URLs use redis://.
if REDIS_URL.startswith("rediss://"):  # noqa: F405
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

# The retired SECURE_BROWSER_XSS_FILTER is replaced by the existing CSP middleware.
sentry_sdk.init(
    dsn=env("SENTRY_DSN", default=""), send_default_pii=False, traces_sample_rate=0.05
)  # noqa: F405
