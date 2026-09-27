"""Django application registration."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Register the namespaced accounts application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
