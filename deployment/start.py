"""One startup path for Docker/Render; exec keeps Gunicorn/Celery as PID 1."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def positive_integer(name: str, default: int, maximum: int) -> int:
    """Read a bounded process/port setting or raise ValueError naming its variable."""
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        raise ValueError(f"{name} must be an integer.") from None
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}.")
    return value


def command_for(role: str) -> list[str]:
    """Build a shell-free command for the selected service role.

    Returns an argument list for execvp. Raises ValueError on invalid settings
    or an unsupported role. No credentials are placed in command arguments.
    """
    if role == "web":
        return [
            "gunicorn",
            "config.wsgi:application",
            "--bind",
            f"0.0.0.0:{positive_integer('PORT', 8000, 65535)}",
            "--workers",
            str(positive_integer("WEB_CONCURRENCY", 2, 32)),
            "--timeout",
            "120",
            "--access-logfile",
            "-",
            "--error-logfile",
            "-",
        ]
    if role == "worker":
        return [
            "celery",
            "-A",
            "config",
            "worker",
            "--loglevel=info",
            "--concurrency",
            str(positive_integer("CELERY_WORKER_CONCURRENCY", 1, 32)),
        ]
    if role == "beat":
        return [
            "celery",
            "-A",
            "config",
            "beat",
            "--loglevel=info",
            "--schedule=/tmp/feesconnect-celerybeat-schedule",
        ]
    raise ValueError("Choose a service role: web, worker, beat or release.")


def manage(*arguments: str) -> None:
    """Run a management command and propagate failure before starting a service."""
    subprocess.run([sys.executable, "manage.py", *arguments], cwd=ROOT, check=True)


def main() -> None:
    """Validate runtime selection, wait for dependencies, then start the service."""
    os.chdir(ROOT)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
    module = os.environ["DJANGO_SETTINGS_MODULE"]
    if module == "config.settings.build" or (
        os.environ.get("RENDER") == "true"
        and module not in {"config.settings.prod", "config.settings.render"}
    ):
        raise ValueError("Render runtime must use config.settings.prod or config.settings.render.")
    role = sys.argv[1] if len(sys.argv) == 2 else ""
    timeout = str(positive_integer("STARTUP_TIMEOUT", 120, 600))
    if role == "release":
        # One pre-deploy task owns schema changes; web/worker/beat never race migrate.
        manage("check", "--deploy", "--fail-level", "WARNING")
        manage("wait_for_services", "--timeout", timeout)
        manage("migrate", "--noinput")
        return
    command = command_for(role)
    manage("wait_for_services", "--timeout", timeout, "--require-migrations")
    os.execvp(command[0], command)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        # Django has already reported configuration errors without revealing keys.
        print(f"FeesConnect startup failed: {exc}", file=sys.stderr)
        sys.exit(1)
