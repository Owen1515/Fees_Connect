"""Django application registration."""

from django.apps import AppConfig


class FeesConfig(AppConfig):
    """Register the namespaced fees application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fees"
    label = "fees"
