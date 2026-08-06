"""Enterprise Structured Logging Service with Sensitive Data Masking & Security Audit Logging."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger("vulnova.observability")

# Keys that must be sanitized from structured log outputs
SENSITIVE_KEYS = {
    "password",
    "token",
    "secret",
    "jwt",
    "api_key",
    "key",
    "authorization",
    "mfa_secret",
    "backup_codes",
    "access_token",
    "refresh_token",
}


def mask_sensitive_data(event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively mask sensitive attributes in log dictionary outputs."""
    sanitized: Dict[str, Any] = {}
    for key, value in event_dict.items():
        key_lower = str(key).lower()
        if any(sens in key_lower for sens in SENSITIVE_KEYS):
            sanitized[key] = "******** [REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = mask_sensitive_data(value)
        elif isinstance(value, str) and re.search(
            r"bearer\s+[a-zA-Z0-9\._\-]+", value, re.I
        ):
            sanitized[key] = re.sub(
                r"bearer\s+[a-zA-Z0-9\._\-]+", "Bearer ********", value, flags=re.I
            )
        else:
            sanitized[key] = value
    return sanitized


class StructuredLoggingService:
    """Service formatting and emitting structured JSON log entries with context enrichment."""

    def __init__(self, service_name: str = "vulnova-backend") -> None:
        self.service_name = service_name
        self.environment = settings.environment

    def log_event(
        self,
        level: str,
        event_name: str,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format and emit a structured JSON log entry."""
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "environment": self.environment,
            "severity": level.upper(),
            "event": event_name,
            "request_id": request_id or "unknown",
            "correlation_id": correlation_id or request_id or "unknown",
        }
        if user_id:
            payload["user_id"] = user_id
        if organization_id:
            payload["organization_id"] = organization_id

        if extra:
            payload.update(extra)

        sanitized_payload = mask_sensitive_data(payload)

        # Remove "event" key from kwargs to avoid position vs keyword argument collision in structlog
        dispatch_kwargs = dict(sanitized_payload)
        dispatch_kwargs.pop("event", None)

        log_func = getattr(logger, level.lower(), logger.info)
        log_func(event_name, **dispatch_kwargs)

        return sanitized_payload

    def log_security_event(
        self,
        event_name: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Specialized logger for security audit events (AUTH_FAILURE, SUSPICIOUS_ACTIVITY, etc.)."""
        extra = details or {}
        extra["category"] = "SECURITY_AUDIT"
        return self.log_event(
            level="warning",
            event_name=f"security.{event_name}",
            user_id=user_id,
            organization_id=organization_id,
            extra=extra,
        )


# Global singleton instance
structured_logger = StructuredLoggingService()
