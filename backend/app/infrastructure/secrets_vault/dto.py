"""Data Transfer Objects (DTOs) for Enterprise Secrets Vault & KMS Infrastructure (Phase 12.8)."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class KMSProviderType(str, Enum):
    """Supported External Key Management System Providers."""

    LOCAL = "local"
    VAULT = "vault"
    AWS_KMS = "aws_kms"
    GCP_KMS = "gcp_kms"


class SecretType(str, Enum):
    """Classification types for managed enterprise secrets."""

    INTEGRATION_TOKEN = "INTEGRATION_TOKEN"
    API_KEY = "API_KEY"
    CLOUD_CREDENTIAL = "CLOUD_CREDENTIAL"
    CERTIFICATE = "CERTIFICATE"
    GENERIC = "GENERIC"


class SecretStatus(str, Enum):
    """Lifecycle status for a stored secret vault entry."""

    ACTIVE = "ACTIVE"
    ROTATED = "ROTATED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class RotationStatus(str, Enum):
    """Lifecycle status for an automated rotation policy."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    PENDING_REVIEW = "PENDING_REVIEW"


class CreateSecretRequestDTO(BaseModel):
    """Request payload for storing a new envelope-encrypted secret."""

    secret_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier name for the secret",
    )
    secret_type: SecretType = Field(
        default=SecretType.GENERIC,
        description="Category classification of the secret",
    )
    plaintext_value: str = Field(
        ...,
        min_length=1,
        description="Plaintext secret value to be envelope encrypted",
    )
    rotation_interval_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Automated rotation interval in days (default: 90 days)",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Arbitrary non-sensitive metadata and tags",
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional absolute expiration duration in days",
    )


class SecretResponseDTO(BaseModel):
    """Public metadata response for a stored secret (never contains plaintext)."""

    id: UUID
    organization_id: UUID
    secret_name: str
    secret_type: SecretType
    provider: str
    masked_value: str
    key_version: int
    status: SecretStatus
    metadata: Dict[str, Any]
    rotation_interval_days: int
    last_rotated_at: Optional[datetime] = None
    next_rotation_due: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SecretDecryptedDTO(BaseModel):
    """Authorized access response containing decrypted plaintext secret."""

    id: UUID
    secret_name: str
    secret_type: SecretType
    plaintext_value: str
    key_version: int
    accessed_at: datetime


class RotateSecretRequestDTO(BaseModel):
    """Request payload to trigger on-demand rotation of a secret."""

    new_plaintext_value: Optional[str] = Field(
        default=None,
        description="Optional new secret value. If omitted, re-encrypts current payload with fresh DEK.",
    )
    reason: Optional[str] = Field(
        default="Manual rotation requested by administrator",
        description="Audit reason for the secret rotation",
    )


class SecretRotationStatusDTO(BaseModel):
    """Aggregated rotation health and compliance metrics across organizational secrets."""

    total_secrets: int
    active_rotations: int
    due_in_7_days: int
    due_in_30_days: int
    overdue_rotations: int
    active_provider: str


class KMSHealthDTO(BaseModel):
    """Health check diagnosis for configured Key Management System providers."""

    provider: str
    is_healthy: bool
    kek_id: str
    latency_ms: float
    details: Dict[str, Any]
    checked_at: datetime
