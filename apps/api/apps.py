"""Django application registration."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """Register the namespaced api application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    label = "api"
