"""Bounded startup gate for database, cache and the committed migration state."""

import time
from typing import Any

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    """Wait for shared infrastructure without migrating from every replica."""

    def add_arguments(self, parser: Any) -> None:
        """Accept a finite deadline and optional schema-readiness requirement."""
        parser.add_argument("--timeout", type=int, default=120)
        parser.add_argument("--require-migrations", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        """Return when ready or raise CommandError after the bounded deadline.

        Database and cache exceptions are reported by class only, keeping
        credentials and connection URLs out of deployment logs.
        """
        timeout = options["timeout"]
        if not 1 <= timeout <= 600:
            raise CommandError("--timeout must be between 1 and 600 seconds.")
        deadline = time.monotonic() + timeout
        while True:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                cache.set("startup-readiness", "ok", 10)
                if cache.get("startup-readiness") != "ok":
                    raise RuntimeError("Cache readback failed")
                if options["require_migrations"]:
                    executor = MigrationExecutor(connection)
                    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                        raise RuntimeError("Migrations not yet applied")
            except Exception as exc:
                connection.close()
                if time.monotonic() >= deadline:
                    raise CommandError(
                        "Startup timed out waiting for PostgreSQL, Redis or migrations. "
                        "Check same-region internal URLs and the web pre-deploy migration logs. "
                        f"Last error type: {type(exc).__name__}."
                    ) from None
                self.stdout.write(f"Waiting for services/schema ({type(exc).__name__})...")
                time.sleep(min(2, max(0, deadline - time.monotonic())))
            else:
                self.stdout.write("PostgreSQL, cache and requested schema checks passed.")
                return
