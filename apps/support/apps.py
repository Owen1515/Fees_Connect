"""Django application registration."""

from django.apps import AppConfig


class SupportConfig(AppConfig):
    """Register the namespaced support application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.support"
    label = "support"
