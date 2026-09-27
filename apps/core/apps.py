"""Django application registration."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Register the namespaced core application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
