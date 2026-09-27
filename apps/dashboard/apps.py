"""Django application registration."""

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Register the namespaced dashboard application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    label = "dashboard"
