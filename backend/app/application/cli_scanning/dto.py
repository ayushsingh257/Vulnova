"""Data Transfer Objects (DTOs) for CI/CD Pipeline Scanning CLI Tool."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CLITokenCreateRequest(BaseModel):
    """Payload to generate a new CLI API token for CI/CD pipelines."""

    name: str = Field(
        ..., description="Token identification name e.g. 'GitHub Actions Release Key'"
    )
    expires_in_days: Optional[int] = Field(
        default=90, description="Optional token expiration period in days"
    )


class CLITokenDTO(BaseModel):
    """CLI API token info (raw_token present only on creation)."""

    id: str
    name: str
    token_prefix: str
    raw_token: Optional[str] = Field(
        default=None, description="Raw token returned once upon creation"
    )
    last_used_at: Optional[str] = None
    created_at: str


class CLIScanStartRequest(BaseModel):
    """Payload to initiate a security scan from CI/CD pipeline."""

    target_url: str = Field(..., description="Target URL or repository path to analyze")
    profile_id: str = Field(
        default="full_assessment", description="Scan profile identifier"
    )
    project_name: Optional[str] = Field(
        default=None, description="Project or repository identifier"
    )
    branch: Optional[str] = Field(
        default=None, description="Git branch name e.g. main or feature/login"
    )
    commit_sha: Optional[str] = Field(default=None, description="Git commit SHA digest")


class CLIScanStatusResponse(BaseModel):
    """Scan execution status response for CLI polling."""

    scan_id: str
    status: str
    progress_percentage: int
    target_url: str
    started_at: str
    completed_at: Optional[str] = None


class CLIFindingSummaryDTO(BaseModel):
    """Severity breakdown metrics for pipeline scan results."""

    scan_id: str
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    total_count: int


class CLIPipelineGateRequest(BaseModel):
    """Pipeline security gate threshold rule check request."""

    scan_id: str = Field(..., description="Scan execution UUID to evaluate")
    max_critical: int = Field(
        default=0,
        description="Maximum allowed CRITICAL findings before pipeline failure",
    )
    max_high: int = Field(
        default=2, description="Maximum allowed HIGH findings before pipeline failure"
    )
    max_medium: int = Field(
        default=10,
        description="Maximum allowed MEDIUM findings before pipeline failure",
    )


class CLIPipelineGateResult(BaseModel):
    """Evaluation result for CI/CD build security gate."""

    gate_passed: bool
    exit_code: int = Field(
        ..., description="0 = Gate Passed, 1 = Gate Failed, 2 = Error"
    )
    summary_text: str
    failed_conditions: List[str] = Field(default_factory=list)


class CLIProjectDTO(BaseModel):
    """Registered project or repository metadata."""

    id: str
    name: str
    repo_url: Optional[str] = None
    last_scan_id: Optional[str] = None
    last_scan_status: Optional[str] = None
    updated_at: str
