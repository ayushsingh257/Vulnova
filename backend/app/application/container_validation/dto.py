"""Data Transfer Objects (DTOs) for Container Image Security & Runtime Hardening Suite."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ContainerCategoryResultDTO(BaseModel):
    """Evaluation result for a single Container Security & Hardening category."""

    category_code: str = Field(
        ..., description="Container Category code e.g. CONTAINER1"
    )
    category_name: str = Field(
        ...,
        description="Container Category title e.g. Base Image CVE Vulnerability Audit",
    )
    status: str = Field(..., description="PASSED, FAILED, or WARNING")
    pass_rate_percentage: float = Field(
        ..., description="Pass rate percentage 0.0 - 100.0"
    )
    passed_assertions: int
    failed_assertions: int
    total_assertions: int
    finding_count: int = 0
    affected_container: Optional[str] = Field(
        default=None, description="Sample container profile or Dockerfile evaluated"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Diagnostic explanation if status is FAILED or WARNING",
    )
    remediation_guidance: str = Field(
        ..., description="Actionable technical steps to harden container profile"
    )


class ContainerValidationSuiteResponse(BaseModel):
    """Complete evaluation response for the Container Image Security Audit & Runtime Hardening Suite."""

    suite_id: str = Field(
        ..., description="Runtime UUID correlation token for audit event tracking"
    )
    organization_id: str
    executed_at: str
    overall_status: str = Field(..., description="PASSED, DEGRADED, or CRITICAL")
    overall_pass_rate: float = Field(
        ..., description="Aggregate percentage across all 10 Container categories"
    )
    passed_categories: int
    failed_categories: int
    warning_categories: int
    total_categories: int = 10
    category_results: List[ContainerCategoryResultDTO]


class ContainerValidationSummaryDTO(BaseModel):
    """High-level health summary metrics for Container Security status."""

    organization_id: str
    last_executed_at: Optional[str] = None
    overall_pass_rate: float
    overall_status: str
    passed_categories: int
    failed_categories: int
