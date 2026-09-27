"""Small JSON log formatter for systemd/Sentry-compatible event logs."""

import json
import logging


class JSONFormatter(logging.Formatter):
    """Format records without serialising request bodies or local variables."""

    def format(self, record: logging.LogRecord) -> str:
        """Return a JSON event with severity and logger context."""
        return json.dumps(
            {"level": record.levelname, "logger": record.name, "message": record.getMessage()}
        )
