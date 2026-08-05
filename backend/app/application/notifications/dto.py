"""Data Transfer Objects (DTOs) for Enterprise Notifications & Alert Webhooks."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateChannelRequest(BaseModel):
    """Payload to create a new webhook notification channel."""

    provider: str = Field(..., description="Provider type: 'slack' or 'teams'")
    name: str = Field(..., description="Human-readable channel name, e.g. #sec-alerts")
    webhook_url: str = Field(..., description="Incoming Webhook URL")
    event_types: List[str] = Field(
        default_factory=lambda: [
            "CRITICAL_FINDING_DISCOVERED",
            "HIGH_FINDING_DISCOVERED",
            "SCAN_COMPLETED",
            "SCAN_FAILED",
            "COMPLIANCE_SCORE_DROPPED",
        ],
        description="List of subscribed event types",
    )
    min_severity: str = Field(
        default="HIGH",
        description="Minimum severity filter: CRITICAL, HIGH, MEDIUM, ALL",
    )


class UpdateChannelRequest(BaseModel):
    """Payload to update an existing webhook notification channel."""

    name: Optional[str] = None
    webhook_url: Optional[str] = None
    event_types: Optional[List[str]] = None
    min_severity: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationChannelDTO(BaseModel):
    """Notification channel details with masked secret webhook URL."""

    id: str
    provider: str
    name: str
    webhook_url_masked: str
    event_types: List[str]
    min_severity: str
    is_active: bool
    created_at: str


class NotificationRuleDTO(BaseModel):
    """Notification rule configuration overview."""

    id: str
    name: str
    event_types: List[str]
    min_severity: str
    min_risk_score: float = 7.0
    is_enabled: bool = True


class SecurityNotificationEventDTO(BaseModel):
    """Canonical security notification event payload dispatched across providers."""

    event_type: str = Field(
        ...,
        description="Event type, e.g. CRITICAL_FINDING_DISCOVERED, SCAN_COMPLETED, COMPLIANCE_SCORE_DROPPED",
    )
    title: str = Field(..., description="Event title summary")
    description: str = Field(..., description="Detailed markdown/text description")
    severity: str = Field(
        default="HIGH", description="Severity label: CRITICAL, HIGH, MEDIUM, LOW, INFO"
    )
    risk_score: Optional[float] = Field(
        default=None, description="Risk score numeric value"
    )
    target_asset: Optional[str] = Field(
        default=None, description="Affected asset name or URL"
    )
    finding_id: Optional[str] = Field(
        default=None, description="Associated finding UUID"
    )
    scan_id: Optional[str] = Field(
        default=None, description="Associated scan/assessment UUID"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context payload"
    )


class NotificationDeliveryResponse(BaseModel):
    """Delivery result for a dispatched webhook notification."""

    channel_id: str
    provider: str
    event_type: str
    status: str = Field(..., description="'DELIVERED' or 'FAILED'")
    status_code: int = Field(..., description="HTTP response status code from provider")
    delivered_at: str
    error_message: Optional[str] = None


class TestNotificationRequest(BaseModel):
    """Payload to trigger a test alert delivery."""

    channel_id: str = Field(..., description="Channel ID to test")
