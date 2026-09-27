"""Factory-boy fixtures for extension tests and local anonymised data."""

import factory
from django.utils import timezone

from apps.accounts.models import User


class UserFactory(factory.django.DjangoModelFactory):
    """Generate unique verified identities without real personal data."""

    class Meta:
        """Target the custom email-based account model."""

        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.test")
    full_name = "Test User"
    email_verified_at = factory.LazyFunction(timezone.now)
    password = factory.PostGenerationMethodCall("set_password", "Strong-Test-Passphrase-173!")
