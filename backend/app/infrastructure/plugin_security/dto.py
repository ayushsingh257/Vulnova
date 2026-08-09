"""DTOs and Data Transfer Objects for Phase 12.7 Plugin Security Architecture."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PluginCapability(str, Enum):
    """Enforceable plugin runtime capability permissions."""

    NETWORK_HTTP = "network:http"
    NETWORK_DNS = "network:dns"
    NETWORK_TCP = "network:tcp"
    FILESYSTEM_READ = "filesystem:read"
    FILESYSTEM_WRITE = "filesystem:write"
    PROCESS_EXECUTE = "process:execute"


class PublisherTrustStatus(str, Enum):
    """Trust status for plugin publishers."""

    TRUSTED = "TRUSTED"
    REVOKED = "REVOKED"
    PENDING = "PENDING"
    UNTRUSTED = "UNTRUSTED"


class PluginVerificationStatus(str, Enum):
    """Result status of cryptographic plugin signature verification."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    REVOKED_PUBLISHER = "REVOKED_PUBLISHER"
    UNKNOWN_PUBLISHER = "UNKNOWN_PUBLISHER"
    CAPABILITY_VIOLATION = "CAPABILITY_VIOLATION"


class PluginManifestDTO(BaseModel):
    """Specification manifest defining plugin metadata and declared capabilities."""

    plugin_id: str = Field(..., description="Unique identifier of plugin")
    name: str = Field(..., description="Human readable plugin name")
    version: str = Field(..., description="Semantic version")
    publisher_id: str = Field(..., description="Identifier of publisher")
    description: str = Field(default="", description="Plugin description")
    entrypoint: str = Field(default="", description="Module/Callable entrypoint")
    capabilities: List[PluginCapability] = Field(
        default_factory=list, description="Declared runtime capabilities"
    )
    package_hash: str = Field(..., description="SHA-256 checksum of plugin package")
    min_platform_version: Optional[str] = Field(
        default=None, description="Minimum platform version"
    )
    signature: Optional[str] = Field(
        default=None, description="Ed25519 signature in hex format"
    )


class RegisterPublisherRequestDTO(BaseModel):
    """Request payload to register or trust a plugin publisher."""

    publisher_id: str = Field(..., description="Unique publisher identifier")
    publisher_name: str = Field(
        ..., description="Human-readable publisher organization"
    )
    public_key_hex: str = Field(
        ..., description="Ed25519 public key in hex (32 bytes / 64 hex chars)"
    )
    contact_email: Optional[str] = Field(
        default=None, description="Security contact email"
    )


class RevokePublisherRequestDTO(BaseModel):
    """Request payload to revoke a plugin publisher's trust."""

    reason: str = Field(..., description="Reason for revocation")


class RotatePublisherKeyRequestDTO(BaseModel):
    """Request payload to rotate a publisher's public key."""

    new_public_key_hex: str = Field(..., description="New Ed25519 public key in hex")
    reason: Optional[str] = Field(default=None, description="Reason for key rotation")


class TrustedPublisherDTO(BaseModel):
    """Details of a registered trusted publisher."""

    id: UUID
    organization_id: UUID
    publisher_id: str
    publisher_name: str
    public_key_hex: str
    public_key_fingerprint: str
    trust_status: PublisherTrustStatus
    contact_email: Optional[str] = None
    verified_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    created_at: datetime


class PluginSignatureVerificationResultDTO(BaseModel):
    """Result of cryptographic signature validation for a plugin manifest."""

    plugin_id: str
    publisher_id: str
    public_key_fingerprint: Optional[str] = None
    is_valid: bool
    verification_status: PluginVerificationStatus
    trust_status: PublisherTrustStatus
    verified_at: datetime
    details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class PluginExecutionRequestDTO(BaseModel):
    """Request payload to execute a security plugin in an isolated sandbox."""

    plugin_id: str = Field(..., description="Plugin identifier to execute")
    target_url: str = Field(..., description="Target URL / host")
    scan_context: Dict[str, Any] = Field(
        default_factory=dict, description="Scan execution parameters"
    )
    timeout_seconds: int = Field(
        default=30, ge=1, le=300, description="Execution timeout in seconds"
    )
    memory_limit_mb: int = Field(
        default=256, ge=64, le=1024, description="Memory limit in MB"
    )
    cpu_limit: float = Field(default=1.0, ge=0.1, le=4.0, description="CPU core quota")


class PluginExecutionResultDTO(BaseModel):
    """Outcome of a sandboxed plugin execution."""

    execution_id: UUID
    plugin_id: str
    status: str = Field(
        ..., description="SUCCESS, BLOCKED, TIMEOUT, FAILED, PERMISSION_DENIED"
    )
    findings_count: int = 0
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    duration_ms: float = 0.0
    exit_code: int = 0
    sandbox_driver: str = "subprocess"
    capabilities_used: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class PluginSecurityReportDTO(BaseModel):
    """Comprehensive zero-trust security audit report for a registered plugin."""

    plugin_id: str
    name: str
    version: str
    publisher_id: str
    publisher_name: str
    signature_valid: bool
    trust_status: PublisherTrustStatus
    capabilities: List[PluginCapability]
    sandbox_enforced: bool
    last_verified_at: Optional[datetime] = None
    total_executions: int = 0
    blocked_executions: int = 0
    created_at: Optional[datetime] = None
