"""Operator administration; financial evidence is read-only and cannot be deleted."""

from typing import Any

from django.apps import apps
from django.contrib import admin
from django.http import HttpRequest

from apps.core.services import audit


class OperatorAdmin(admin.ModelAdmin):
    """Only Django superusers may access operational records in this admin site."""

    list_per_page = 50

    def has_module_permission(self, request: HttpRequest) -> Any:
        """Keep cross-school administration restricted to trusted operators."""
        return request.user.is_superuser

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> Any:
        """Require platform operator identity for every model."""
        return request.user.is_superuser

    def has_add_permission(self, request: HttpRequest) -> Any:
        """Configuration creation is reserved for trusted operators."""
        return request.user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> Any:
        """Configuration changes require operator authority."""
        return request.user.is_superuser

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> Any:
        """Deactivate records instead of deleting financial history."""
        return False

    def save_model(self, request: HttpRequest, obj: Any, form: Any, change: Any) -> Any:
        """Record every operator configuration change in the audit trail."""
        super().save_model(request, obj, form, change)
        audit(request.user, "admin_updated" if change else "admin_created", obj)


class EvidenceAdmin(OperatorAdmin):
    """Expose evidence for review without permitting arbitrary monetary edits."""

    def has_add_permission(self, request: HttpRequest) -> Any:
        """Evidence must originate in transactional services."""
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> Any:
        """Financial values and audit records are immutable through admin."""
        return False


CONFIG = {
    "Currency",
    "School",
    "AcademicPeriod",
    "FeeCategory",
    "FeeSchedule",
    "MerchantAccount",
    "FeePolicy",
    "RoleAssignment",
}
for label in ["accounts", "fees", "payments", "core", "support"]:
    for model in apps.get_app_config(label).get_models():
        if model.__name__ == "User":
            continue
        admin.site.register(model, OperatorAdmin if model.__name__ in CONFIG else EvidenceAdmin)
admin.site.site_header = "FeesConnect operations"
admin.site.site_title = "FeesConnect"
