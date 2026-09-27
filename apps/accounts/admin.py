"""Restricted user administration with Django's password hashing forms."""

from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.http import HttpRequest

from .models import User


class AddUserForm(UserCreationForm):
    """Create email-based users using Django's password confirmation logic."""

    class Meta:
        """Limit editable fields in account creation."""

        model = User
        fields = ("email", "full_name")


class EditUserForm(UserChangeForm):
    """Display the password hash read-only; password changes use Django's flow."""

    class Meta:
        """Bind the custom user model."""

        model = User
        fields = "__all__"


@admin.register(User)
class AccountAdmin(UserAdmin):
    """Only superusers can administer identities or grant elevated permissions."""

    add_form = AddUserForm
    form = EditUserForm
    ordering = ("email",)
    list_display = ("email", "full_name", "is_active", "email_verified_at")
    search_fields = ("email", "full_name")
    fieldsets = (
        (None, {"fields": ("email", "password", "full_name", "phone")}),
        (
            "Access",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "email_verified_at",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = ((None, {"fields": ("email", "full_name", "password1", "password2")}),)

    def has_module_permission(self, request: HttpRequest) -> Any:
        """Deny unscoped staff access."""
        return request.user.is_superuser

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> Any:
        """Restrict personal data to platform operators."""
        return request.user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> Any:
        """Restrict account/permission changes to platform operators."""
        return request.user.is_superuser

    def has_add_permission(self, request: HttpRequest) -> Any:
        """Restrict account creation in admin."""
        return request.user.is_superuser

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> Any:
        """Preserve linked records; deactivate accounts instead."""
        return False
