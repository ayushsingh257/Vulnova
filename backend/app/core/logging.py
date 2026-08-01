import logging
import sys
from typing import Any, Dict

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """Simple JSON log formatter for production-grade structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format LogRecord into a JSON-compatible log entry string."""
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": settings.environment,
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        import json

        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """Initialize structured application logging."""
    logger = logging.getLogger("vulnova")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Prevent duplicating handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if settings.is_production:
            handler.setFormatter(JsonFormatter())
        else:
            formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
            )
            handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()
