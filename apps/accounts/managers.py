"""Email-first user manager shared by registration and management commands."""

from typing import Any

from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Create users without a username field."""

    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> Any:
        """Create an ordinary user; raise ValueError when email is absent."""
        if not email:
            raise ValueError("Email is required.")
        user = self.model(email=email.strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra: Any) -> Any:
        """Create a verified operator account via a trusted terminal."""
        from django.utils import timezone

        extra.update(is_staff=True, is_superuser=True, email_verified_at=timezone.now())
        return self.create_user(email, password, **extra)
