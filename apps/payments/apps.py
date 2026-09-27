"""Django application registration."""

from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    """Register the namespaced payments application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    label = "payments"
