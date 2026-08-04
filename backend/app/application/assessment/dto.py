"""Data Transfer Objects (DTOs) for Vulnerability Assessment Engine."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ScanPolicyDTO(BaseModel):
    """DTO representing an execution policy configuration."""

    concurrency_limit: int = 5
    rate_limit_rps: int = 10
    respect_robots_txt: bool = True
    scope_include_patterns: List[str] = Field(default_factory=list)
    scope_exclude_patterns: List[str] = Field(default_factory=list)
    max_crawl_depth: int = 3
    max_requests: int = 500
    timeout_seconds: float = 30.0
    stop_on_critical: bool = False


class ScanProfileDTO(BaseModel):
    """DTO describing an enterprise scan profile."""

    id: str
    name: str
    description: str
    plugin_ids: List[str] = Field(default_factory=list)
    default_policy: ScanPolicyDTO


class CreateAssessmentRequest(BaseModel):
    """Payload for triggering a security assessment scan.

    Phase 6.2: ``is_authorized_assessment`` is a mandatory legal declaration.
    Scans will be rejected (HTTP 403) if this field is not set to ``True``.
    """

    target_url: HttpUrl = Field(
        description="Target web asset URL to scan (must be HTTP/HTTPS)"
    )
    is_authorized_assessment: bool = Field(
        ...,
        description="Mandatory legal declaration confirming authorized security assessment consent. Must be True to proceed.",
    )
    authorization_scope: str = Field(
        default="full",
        description="Scope of authorization: 'full', 'passive_only', or 'custom'. Defaults to 'full'.",
    )
    profile_id: Optional[str] = Field(
        default="full_assessment",
        description="Enterprise scan profile ID (e.g. 'web_scan', 'api_scan', 'full_assessment'). Defaults to 'full_assessment'.",
    )
    plugins: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific plugin IDs to execute. Used when profile_id is 'custom_scan' or to override profile default plugins.",
    )
    policy_override: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional execution policy overrides (concurrency_limit, rate_limit_rps, auth_headers, auth_cookies, scope_exclude_patterns, etc.)",
    )


class EvidenceArtifactDTO(BaseModel):
    """DTO representing a proof evidence artifact attached to a finding."""

    id: str
    finding_id: str
    artifact_type: str
    storage_path: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    checksum: str
    created_at: str


class FindingDTO(BaseModel):
    """DTO representing a security finding/vulnerability."""

    id: str
    assessment_job_id: str
    plugin_id: str
    title: str
    description: str
    severity: str
    category: str
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    remediation: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    cvss: Optional[Dict[str, Any]] = None
    epss: Optional[Dict[str, Any]] = None
    risk_score: Optional[float] = None
    business_impact: Optional[str] = None
    confidence: Optional[str] = "HIGH"
    is_duplicate: bool = False
    canonical_finding_id: Optional[str] = None
    fix_sla_hours: Optional[int] = None
    evidence_count: int = 0
    evidence_available: bool = False
    artifacts: List[EvidenceArtifactDTO] = Field(default_factory=list)
    created_at: str


class AssessmentJobResponse(BaseModel):
    """Response model for an assessment job run."""

    id: str
    target_url: str
    status: str
    execution_state: str = "QUEUED"
    retry_count: int = 0
    max_retries: int = 3
    current_step: Optional[str] = None
    profile_id: str = "full_assessment"
    enabled_plugins: List[str] = Field(default_factory=list)
    policy: Optional[ScanPolicyDTO] = None
    total_findings: int = 0
    findings: List[FindingDTO] = Field(default_factory=list)
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class PluginMetadataDTO(BaseModel):
    """DTO describing a registered assessment plugin."""

    id: str
    name: str
    version: str
    description: str
    category: str
    author: str
    supported_asset_types: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)


class AssetInventoryDTO(BaseModel):
    """DTO representing high-level enterprise asset inventory posture."""

    id: str
    node_type: str
    name: str
    value: str
    risk_score: float = 0.0
    risk_level: str = "LOW"
    total_findings: int = 0
    findings_by_severity: Dict[str, int] = Field(default_factory=dict)
    technologies: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class AssetInventoryResponse(BaseModel):
    """Paginated response model for enterprise asset inventory posture."""

    total: int
    items: List[AssetInventoryDTO] = Field(default_factory=list)


class AssetDetailResponse(BaseModel):
    """Detailed response model for a single enterprise asset."""

    asset: AssetInventoryDTO
    technologies: List[Dict[str, Any]] = Field(default_factory=list)
    findings: List[FindingDTO] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)


class AssetSnapshotDTO(BaseModel):
    """DTO representing a point-in-time security posture snapshot."""

    id: str
    assessment_job_id: Optional[str] = None
    total_assets: int = 0
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    info_findings: int = 0
    avg_risk_score: float = 0.0
    max_risk_score: float = 0.0
    created_at: str


class AssetChangeEventDTO(BaseModel):
    """DTO describing a security posture delta change event."""

    id: str
    asset_node_id: Optional[str] = None
    assessment_job_id: Optional[str] = None
    change_type: str
    title: str
    description: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class RiskTrajectoryResponse(BaseModel):
    """Response model for historical risk posture trajectory and net delta."""

    current_avg_risk_score: float = 0.0
    previous_avg_risk_score: float = 0.0
    net_risk_delta: float = 0.0
    risk_trend_direction: str = "STABLE"  # INCREASING, DECREASING, STABLE
    total_snapshots: int = 0
    snapshots: List[AssetSnapshotDTO] = Field(default_factory=list)


class PostureTimelineResponse(BaseModel):
    """Response model for aggregated security posture event timeline."""

    total_events: int
    events: List[AssetChangeEventDTO] = Field(default_factory=list)


class TriageFindingRequest(BaseModel):
    """Request model for triaging a single security finding."""

    status: str  # CONFIRMED, FALSE_POSITIVE, RISK_ACCEPTED, REMEDIATED, REOPENED
    comment: Optional[str] = None
    risk_accepted_until: Optional[str] = None


class BulkTriageRequest(BaseModel):
    """Request model for bulk triaging multiple security findings."""

    finding_ids: List[str]
    status: str
    comment: Optional[str] = None


class CreateSuppressionRuleRequest(BaseModel):
    """Request model for creating an automated false-positive finding suppression rule."""

    name: str
    rule_type: str  # EXACT_CWE, TARGET_PATTERN, PLUGIN_ID, COMPOSITE
    reason: str
    plugin_id: Optional[str] = None
    cwe_id: Optional[str] = None
    target_pattern: Optional[str] = None
    expires_at: Optional[str] = None


class FindingTriageHistoryDTO(BaseModel):
    """DTO representing a single historical finding triage record."""

    id: str
    finding_id: str
    actor_user_id: Optional[str] = None
    previous_status: str
    new_status: str
    comment: Optional[str] = None
    risk_accepted_until: Optional[str] = None
    created_at: str


class SuppressionRuleDTO(BaseModel):
    """DTO representing an automated finding suppression rule."""

    id: str
    name: str
    rule_type: str
    reason: str
    plugin_id: Optional[str] = None
    cwe_id: Optional[str] = None
    target_pattern: Optional[str] = None
    is_active: bool = True
    created_by_user_id: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str


class TriageResponse(BaseModel):
    """Response model for finding triage operations."""

    finding_id: str
    previous_status: str
    new_status: str
    message: str


# ── Phase 6.1: Celery & Distributed Isolated Worker Sandbox Cluster DTOs ──


class SandboxConfigDTO(BaseModel):
    """DTO representing worker container sandbox security caps."""

    cpu_limit_vcpu: float = 1.0
    memory_limit_mb: int = 512
    read_only_rootfs: bool = True
    no_new_privs: bool = True
    run_as_uid: int = 10001


class WorkerNodeDTO(BaseModel):
    """DTO representing a registered Celery worker node in cluster."""

    id: str
    organization_id: str
    worker_id: str
    hostname: str
    status: str
    current_task_count: int
    max_concurrency: int
    memory_usage_mb: float
    cpu_percent: float
    queue_subscriptions: List[str] = Field(default_factory=list)
    sandbox_limits: SandboxConfigDTO
    last_heartbeat: str


class WorkerTaskExecutionDTO(BaseModel):
    """DTO representing an audit record of a task execution."""

    id: str
    task_id: str
    scan_id: Optional[str] = None
    organization_id: str
    requested_by: str
    worker_node_id: Optional[str] = None
    priority: str
    task_name: str
    state: str
    retry_count: int
    runtime_ms: int
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class DispatchScanRequest(BaseModel):
    """Request payload for dispatching a scan job to Celery priority queues.

    Phase 6.2: ``is_authorized_assessment`` is mandatory. Worker dispatch
    flow will reject jobs without validated authorization metadata.
    """

    scan_id: str = Field(..., description="UUID of security assessment job")
    profile_id: Optional[str] = Field(None, description="Optional scan profile ID")
    target_url: Optional[str] = Field(None, description="Optional target URL")
    priority: Optional[str] = Field(
        "scans.default",
        description="Priority queue (scans.high, scans.default, scans.low)",
    )
    is_authorized_assessment: bool = Field(
        ...,
        description="Mandatory legal declaration confirming authorized assessment consent.",
    )


class WorkerClusterMetricsDTO(BaseModel):
    """DTO representing overall worker cluster status and capacity metrics."""

    organization_id: str
    total_nodes: int
    active_nodes: int
    total_capacity: int
    current_active_tasks: int
    avg_cpu_percent: float
    avg_memory_usage_mb: float


# ── Phase 6.2: Target Scan Configuration & Authorization DTOs ──


class ScanTargetCreateRequest(BaseModel):
    """Request payload for registering a new scan target."""

    name: str = Field(..., description="Human-readable name for the scan target")
    target_url: HttpUrl = Field(
        ..., description="Target web asset URL to register (must be HTTP/HTTPS)"
    )
    environment: str = Field(
        default="PRODUCTION",
        description="Deployment environment: PRODUCTION, STAGING, DEVELOPMENT, TESTING",
    )


class ScanTargetUpdateRequest(BaseModel):
    """Request payload for updating an existing scan target."""

    name: Optional[str] = Field(None, description="Updated human-readable name")
    environment: Optional[str] = Field(
        None, description="Updated environment classification"
    )
    status: Optional[str] = Field(
        None, description="Updated status: ACTIVE, ARCHIVED, SUSPENDED"
    )


class ScanTargetResponse(BaseModel):
    """Response DTO representing a registered scan target."""

    id: str
    organization_id: str
    name: str
    target_url: str
    environment: str
    status: str
    is_ownership_verified: bool
    ownership_verification_token: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class PolicyValidationResult(BaseModel):
    """Result of the AssessmentPolicyEngine pre-scan authorization validation."""

    is_allowed: bool
    rejection_reason: Optional[str] = None
    scan_target_id: Optional[str] = None
    authorization_id: Optional[str] = None


# ── Phase 6.3: Scan Execution Lifecycle & Retry DTOs ──


class ScanStateTransitionRequest(BaseModel):
    """Request payload for manual state machine transition, retry, or cancellation."""

    target_state: str = Field(
        ...,
        description="Target lifecycle state (QUEUED, CRAWLING, ASSESSING, AI_ANALYSIS, COMPLETED, FAILED, CANCELLED, RETRYING)",
    )
    current_step: Optional[str] = Field(None, description="Optional current step label")
    reason: Optional[str] = Field(
        None, description="Reason for manual state change or cancellation"
    )


class ScanLifecycleStateDTO(BaseModel):
    """Detailed response DTO representing an assessment job's lifecycle state machine status."""

    job_id: str
    organization_id: str
    target_url: str
    execution_state: str
    status: str
    current_step: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    is_terminal: bool = False


class DistributedLockStatusDTO(BaseModel):
    """Response DTO describing the distributed Redis lock status of a scan target."""

    target_url: str
    is_locked: bool
    lock_key: str
    owner_id: Optional[str] = None
    acquired_at: Optional[str] = None
    ttl_seconds: int = 3600


# ── Phase 6.4: Real-Time WebSocket Scan Event Stream DTOs ──


class ScanStreamEventDTO(BaseModel):
    """DTO representing a single real-time scan stream event payload."""

    event_id: str
    job_id: str
    organization_id: str
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class ScanEventHistoryResponse(BaseModel):
    """Response model for REST scan execution event history queries."""

    job_id: str
    total_events: int
    events: List[ScanStreamEventDTO] = Field(default_factory=list)


# ── Phase 6.5: Distributed Scan Scheduler & Recurrence Engine DTOs ──


class CreateScanScheduleRequest(BaseModel):
    """Request payload for creating a recurring scan schedule."""

    scan_target_id: str = Field(..., description="UUID of registered scan target")
    name: str = Field(
        ..., description="Human-readable schedule name", min_length=2, max_length=150
    )
    cron_expression: str = Field(
        "0 0 * * *",
        description="Standard 5-part cron expression (e.g., '0 0 * * *' for daily midnight)",
    )
    frequency: str = Field(
        "DAILY",
        description="Recurrence frequency: HOURLY, DAILY, WEEKLY, MONTHLY, CUSTOM_CRON",
    )
    profile_id: str = Field("full_assessment", description="Scan profile identifier")
    enabled_plugins: Optional[List[str]] = Field(
        None, description="Optional list of enabled plugin IDs"
    )


class UpdateScanScheduleRequest(BaseModel):
    """Request payload for modifying an existing scan schedule."""

    name: Optional[str] = Field(None, min_length=2, max_length=150)
    cron_expression: Optional[str] = Field(None)
    frequency: Optional[str] = Field(None)
    profile_id: Optional[str] = Field(None)
    enabled_plugins: Optional[List[str]] = Field(None)


class ScanScheduleResponse(BaseModel):
    """Response payload representing a scan schedule."""

    id: str
    organization_id: str
    scan_target_id: str
    name: str
    cron_expression: str
    frequency: str
    status: str
    profile_id: str
    enabled_plugins: Optional[List[str]] = None
    total_runs_count: int
    next_run_at: str
    last_run_at: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    updated_at: str


class ScanScheduleListResponse(BaseModel):
    """Response payload for listing tenant scan schedules."""

    total_count: int
    schedules: List[ScanScheduleResponse] = Field(default_factory=list)


class WorkerAutoscaleMetricsResponse(BaseModel):
    """Response payload describing worker cluster capacity and scaling recommendations."""

    active_workers_count: int
    idle_workers_count: int
    pending_queue_depth: int
    recommended_workers_count: int
    scaling_action_suggested: str
    timestamp: str
