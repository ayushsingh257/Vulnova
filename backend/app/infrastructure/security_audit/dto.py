"""Data Transfer Objects for Enterprise Security Audit & Penetration Testing Framework."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuditSeverity(str, Enum):
    """Vulnerability Severity Classification."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AuditFindingStatus(str, Enum):
    """Security Audit Finding Lifecycle State."""

    OPEN = "OPEN"
    REMEDIATED = "REMEDIATED"
    ACCEPTED_RISK = "ACCEPTED_RISK"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class AuditCategory(str, Enum):
    """Security Audit Analysis Categories."""

    SAST = "SAST"
    SCA = "SCA"
    CONFIGURATION = "CONFIGURATION"
    API_SECURITY = "API_SECURITY"
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION_RBAC = "AUTHORIZATION_RBAC"
    SECRET_DETECTION = "SECRET_DETECTION"
    CONTAINER_SECURITY = "CONTAINER_SECURITY"


class SecurityAuditFindingDTO(BaseModel):
    """Detailed finding discovered during security audit."""

    id: UUID
    finding_id: str
    category: str
    title: str
    description: str
    severity: str
    location: str
    remediation_status: str = "OPEN"
    remediation_guidance: str
    cwe_id: Optional[str] = None
    risk_score: float = 0.0
    discovered_at: datetime
    remediated_at: Optional[datetime] = None
    remediation_notes: Optional[str] = None
    remediated_by: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class SecurityAuditExecutionDTO(BaseModel):
    """Result of a comprehensive security audit run."""

    audit_id: UUID
    organization_id: UUID
    executed_at: datetime
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    open_findings_count: int
    remediated_findings_count: int
    overall_security_score: float
    status: str = "PASSED"
    categories_analyzed: List[str] = Field(default_factory=list)
    findings: List[SecurityAuditFindingDTO] = Field(default_factory=list)
    audit_integrity_sha256: str
    summary: str


class SecurityAuditStatusDTO(BaseModel):
    """High-level security audit posture summary."""

    status: str = "HEALTHY"
    last_audit_id: Optional[UUID] = None
    last_audit_timestamp: Optional[datetime] = None
    total_scans_executed: int = 0
    total_vulnerabilities_tracked: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    remediation_rate_percentage: float = 100.0
    compliance_grade: str = "A+"


class RunSecurityAuditRequestDTO(BaseModel):
    """Payload to trigger an automated security audit run."""

    categories: Optional[List[str]] = None
    include_dynamic_checks: bool = True
    details: Dict[str, Any] = Field(default_factory=dict)


class RemediateFindingRequestDTO(BaseModel):
    """Payload to update finding remediation status."""

    status: AuditFindingStatus = AuditFindingStatus.REMEDIATED
    remediation_notes: str = Field(..., min_length=5)
    remediated_by: Optional[str] = None
