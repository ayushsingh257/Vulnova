"""Data Transfer Objects for Phase 12.6 AI Finding Confidence Scoring & Human-in-the-Loop Remediation Workflow."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Vulnerability finding confidence levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CONFIRMED = "CONFIRMED"


class VerificationStatus(str, Enum):
    """Automated re-probe finding verification lifecycle states."""

    UNVERIFIED = "UNVERIFIED"
    VERIFYING = "VERIFYING"
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ReviewDecision(str, Enum):
    """Human analyst review decisions."""

    CONFIRM = "CONFIRM"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    ACCEPT_RISK = "ACCEPT_RISK"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"


class RemediationStatus(str, Enum):
    """Human-in-the-loop remediation recommendation lifecycle states."""

    AI_RECOMMENDED = "AI_RECOMMENDED"
    ANALYST_REVIEW = "ANALYST_REVIEW"
    APPROVED_FOR_IMPLEMENTATION = "APPROVED_FOR_IMPLEMENTATION"
    IMPLEMENTED = "IMPLEMENTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class FindingConfidenceResultDTO(BaseModel):
    """DTO summarizing finding confidence calculation breakdown."""

    finding_id: UUID
    confidence_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall confidence score (0-100%)"
    )
    confidence_level: ConfidenceLevel
    evidence_quality_score: float = Field(..., ge=0.0, le=100.0)
    reproduction_score: float = Field(..., ge=0.0, le=100.0)
    ai_analysis_score: float = Field(..., ge=0.0, le=100.0)
    verification_status: VerificationStatus
    explanation: str


class FindingVerificationAttemptDTO(BaseModel):
    """DTO representing an automated re-probe finding verification attempt."""

    id: UUID
    organization_id: UUID
    finding_id: UUID
    verification_status: VerificationStatus
    strategy: str
    probe_response_status: Optional[int] = None
    probe_output: Optional[str] = None
    is_reproduced: bool
    created_at: datetime


class FindingReviewRequestDTO(BaseModel):
    """Request DTO for human analyst finding review."""

    decision: ReviewDecision
    comments: Optional[str] = Field(
        default=None, description="Analyst review justification notes"
    )


class FindingReviewDTO(BaseModel):
    """DTO representing a completed human analyst finding review."""

    id: UUID
    organization_id: UUID
    finding_id: UUID
    reviewer_id: UUID
    decision: ReviewDecision
    comments: Optional[str] = None
    evidence_snapshot: Optional[str] = None
    created_at: datetime


class RemediationApprovalDTO(BaseModel):
    """DTO representing a remediation plan approval transition."""

    id: UUID
    organization_id: UUID
    remediation_plan_id: UUID
    finding_id: UUID
    previous_state: str
    new_state: RemediationStatus
    action_by: UUID
    notes: Optional[str] = None
    created_at: datetime


class RemediationActionRequestDTO(BaseModel):
    """Request DTO to approve or reject an AI remediation recommendation."""

    notes: Optional[str] = Field(
        default=None, description="Approval or rejection notes from security analyst"
    )
