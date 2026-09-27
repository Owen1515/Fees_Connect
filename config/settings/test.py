"""Fast isolated unit tests; financial concurrency also runs against PostgreSQL in CI."""

from .dev import *  # noqa: F403

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
AXES_ENABLED = False
CELERY_TASK_ALWAYS_EAGER = True
DATA_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
ALLOWED_HOSTS = ["testserver", "localhost"]
