"""Background task application; deployment selects settings through the environment."""

import os

from celery import Celery

# Server entrypoints must fail closed; manage.py explicitly selects dev locally.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
app = Celery("feesconnect")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
