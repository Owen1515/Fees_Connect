"""Export every database field for future migration mapping."""

import json
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Describe business models without exposing database row contents."""

    def handle(self, *args: Any, **options: Any) -> Any:
        """Write model fields, types and relationship targets as JSON."""
        result = {}
        for label in ["accounts", "core", "fees", "payments", "support"]:
            for model in apps.get_app_config(label).get_models():
                result[model._meta.label] = [
                    {
                        "name": f.name,
                        "type": f.get_internal_type(),
                        "null": f.null,
                        "unique": f.unique,
                        "related_model": f.related_model._meta.label if f.is_relation else None,
                        "help_text": str(f.help_text),
                    }
                    for f in model._meta.fields
                ]
        self.stdout.write(json.dumps(result, indent=2))
