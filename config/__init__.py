"""Expose the Celery application to Django's task registry."""

from .celery import app as celery_app

__all__ = ["celery_app"]
