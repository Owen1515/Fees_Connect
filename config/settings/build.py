"""Static asset collection only; never select this module for a running service."""

from .base import *  # noqa: F403

# This public build-only value is not used to sign sessions or encrypt user data.
SECRET_KEY = "build-only-no-runtime-credentials-are-required-for-static-collection"
# Static collection must never connect to a production database, broker or SMTP.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
