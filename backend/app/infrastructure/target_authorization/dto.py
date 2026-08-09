"""Data Transfer Objects for Phase 12.5 Target Verification & Authorization System."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VerificationType(str, Enum):
    """Supported target ownership verification challenge methods."""

    DNS_TXT = "DNS_TXT"
    HTTP_WELL_KNOWN = "HTTP_WELL_KNOWN"


class VerificationStatus(str, Enum):
    """Target verification challenge lifecycle states."""

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class ApprovalStatus(str, Enum):
    """Scan approval request states for sensitive target assets."""

    REQUESTED = "REQUESTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TargetVerificationChallengeCreateDTO(BaseModel):
    """Request DTO to initiate a target verification challenge."""

    verification_type: VerificationType = Field(
        default=VerificationType.DNS_TXT,
        description="Verification method: DNS_TXT or HTTP_WELL_KNOWN",
    )


class TargetVerificationChallengeDTO(BaseModel):
    """Response DTO representing a target verification challenge."""

    id: UUID
    target_id: UUID
    organization_id: UUID
    challenge_token: str
    verification_type: VerificationType
    status: VerificationStatus
    verification_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    verified_at: Optional[datetime] = None
    expires_at: datetime
    instructions: Optional[str] = None


class TargetVerificationResultDTO(BaseModel):
    """DTO summarizing the result of a target verification execution."""

    challenge_id: UUID
    target_id: UUID
    verified: bool
    status: VerificationStatus
    message: str
    verified_at: Optional[datetime] = None
    evidence: Optional[Dict[str, Any]] = None


class ScanApprovalRequestCreateDTO(BaseModel):
    """Request DTO to request scan authorization for a sensitive target asset."""

    target_id: UUID
    scan_job_id: Optional[UUID] = None
    reason: Optional[str] = Field(
        default=None,
        description="Business justification for scanning sensitive IP/environment",
    )


class ScanApprovalRequestDTO(BaseModel):
    """Response DTO for scan approval request."""

    id: UUID
    organization_id: UUID
    scan_job_id: Optional[UUID] = None
    target_id: UUID
    requested_by: UUID
    approved_by: Optional[UUID] = None
    status: ApprovalStatus
    reason: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None


class ScanAuthorizationResultDTO(BaseModel):
    """DTO representing pre-scan target authorization pipeline evaluation."""

    authorized: bool
    is_verified: bool
    requires_approval: bool = False
    approval_status: Optional[ApprovalStatus] = None
    reason: str
    target_id: Optional[UUID] = None
    target_url: Optional[str] = None
