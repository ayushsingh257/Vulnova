"""Data Transfer Objects (DTOs) for Dependency Security Audit & SCA Enforcement Suite."""

from typing import List, Optional

from pydantic import BaseModel, Field


class SCACategoryResultDTO(BaseModel):
    """Evaluation result for a single Software Composition Analysis category."""

    category_code: str = Field(..., description="SCA Category code e.g. SCA1")
    category_name: str = Field(
        ..., description="SCA Category title e.g. Known CVE Vulnerability Audit"
    )
    status: str = Field(..., description="PASSED, FAILED, or WARNING")
    pass_rate_percentage: float = Field(
        ..., description="Pass rate percentage 0.0 - 100.0"
    )
    passed_assertions: int
    failed_assertions: int
    total_assertions: int
    finding_count: int = 0
    affected_package: Optional[str] = Field(
        default=None, description="Sample dependency package or manifest file evaluated"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Diagnostic explanation if status is FAILED or WARNING",
    )
    remediation_guidance: str = Field(
        ..., description="Actionable technical steps to remediate dependency risk"
    )


class SCAValidationSuiteResponse(BaseModel):
    """Complete evaluation response for the Dependency Security & SCA Enforcement Suite."""

    suite_id: str = Field(
        ..., description="Runtime UUID correlation token for audit event tracking"
    )
    organization_id: str
    executed_at: str
    overall_status: str = Field(..., description="PASSED, DEGRADED, or CRITICAL")
    overall_pass_rate: float = Field(
        ..., description="Aggregate percentage across all 10 SCA categories"
    )
    passed_categories: int
    failed_categories: int
    warning_categories: int
    total_categories: int = 10
    category_results: List[SCACategoryResultDTO]


class SCAValidationSummaryDTO(BaseModel):
    """High-level health summary metrics for Dependency Security & SCA status."""

    organization_id: str
    last_executed_at: Optional[str] = None
    overall_pass_rate: float
    overall_status: str
    passed_categories: int
    failed_categories: int
