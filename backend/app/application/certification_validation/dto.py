"""Data Transfer Objects (DTOs) for Security Control Plane Final Certification & Compliance Readiness Suite."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CertificationCategoryResultDTO(BaseModel):
    """Evaluation result for a single Security Certification category."""

    category_code: str = Field(
        ..., description="Certification category code e.g. CERTIFICATION1"
    )
    category_name: str = Field(
        ...,
        description="Certification category title e.g. OWASP Security Control Plane Certification",
    )
    status: str = Field(..., description="PASSED, FAILED, or WARNING")
    pass_rate_percentage: float = Field(
        ..., description="Pass rate percentage 0.0 - 100.0"
    )
    passed_assertions: int
    failed_assertions: int
    total_assertions: int
    affected_control: Optional[str] = Field(
        default=None, description="Platform security control evaluated"
    )
    failure_reason: Optional[str] = Field(
        default=None, description="Diagnostic explanation if certification fails"
    )
    remediation_guidance: str = Field(
        ...,
        description="Actionable technical steps to achieve certification compliance",
    )


class CertificationValidationSuiteResponse(BaseModel):
    """Complete evaluation response for the Security Control Plane Final Certification Suite."""

    suite_id: str = Field(
        ..., description="Runtime UUID correlation token for audit event tracking"
    )
    organization_id: str
    executed_at: str
    overall_status: str = Field(..., description="PASSED, DEGRADED, or CRITICAL")
    overall_certification_score: float = Field(
        ...,
        description="Aggregate percentage across all 10 Security Certification categories",
    )
    passed_categories: int
    failed_categories: int
    warning_categories: int
    total_categories: int = 10
    category_results: List[CertificationCategoryResultDTO]


class CertificationValidationSummaryDTO(BaseModel):
    """High-level summary metrics for Enterprise Security Certification status."""

    organization_id: str
    last_executed_at: Optional[str] = None
    overall_certification_score: float
    overall_status: str
    passed_categories: int
    failed_categories: int
