"""Data Transfer Objects (DTOs) for Security Configuration & Infrastructure Validation Suite."""

from typing import List, Optional

from pydantic import BaseModel, Field


class InfrastructureValidationCategoryResultDTO(BaseModel):
    """Evaluation result for a single Infrastructure Security validation category."""

    category_code: str = Field(
        ..., description="Infrastructure Security Category code e.g. INFRA1"
    )
    category_name: str = Field(
        ...,
        description="Infrastructure Security Category title e.g. Secure Configuration Management",
    )
    status: str = Field(..., description="PASSED, FAILED, or WARNING")
    pass_rate_percentage: float = Field(
        ..., description="Pass rate percentage 0.0 - 100.0"
    )
    passed_assertions: int
    failed_assertions: int
    total_assertions: int
    finding_count: int = 0
    affected_component: Optional[str] = Field(
        default=None, description="Sample infrastructure layer or component evaluated"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Diagnostic explanation if status is FAILED or WARNING",
    )
    remediation_guidance: str = Field(
        ...,
        description="Actionable technical steps to resolve infrastructure security risk",
    )


class InfrastructureValidationSuiteResponse(BaseModel):
    """Complete evaluation response for the Infrastructure Security Validation Suite."""

    suite_id: str = Field(
        ..., description="Runtime UUID correlation token for audit event tracking"
    )
    organization_id: str
    executed_at: str
    overall_status: str = Field(..., description="PASSED, DEGRADED, or CRITICAL")
    overall_pass_rate: float = Field(
        ..., description="Aggregate percentage across all 10 Infrastructure categories"
    )
    passed_categories: int
    failed_categories: int
    warning_categories: int
    total_categories: int = 10
    category_results: List[InfrastructureValidationCategoryResultDTO]


class InfrastructureValidationSummaryDTO(BaseModel):
    """High-level health summary metrics for Infrastructure Security validation status."""

    organization_id: str
    last_executed_at: Optional[str] = None
    overall_pass_rate: float
    overall_status: str
    passed_categories: int
    failed_categories: int
