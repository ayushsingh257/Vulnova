from typing import List, Optional

from pydantic import BaseModel, Field


class DisasterRecoveryStatusDTO(BaseModel):
    """Current Disaster Recovery (DR) readiness status."""

    status: str = Field(
        ...,
        description="Overall DR operational status: READY, DEGRADED, FAILOVER_ACTIVE, RECOVERING",
    )
    rto_target_minutes: int = Field(default=60, description="RTO target in minutes")
    rpo_target_minutes: int = Field(default=5, description="RPO target in minutes")
    primary_database_status: str = Field(..., description="Primary database state")
    secondary_database_status: str = Field(..., description="Secondary replica state")
    redis_cluster_status: str = Field(..., description="Redis cache cluster status")
    last_backup_timestamp: Optional[str] = Field(
        default=None,
        description="Timestamp of latest verified backup archive",
    )
    last_dr_test_timestamp: Optional[str] = Field(
        default=None,
        description="Timestamp of latest DR simulation run",
    )
    active_recovery_id: Optional[str] = Field(
        default=None,
        description="Active recovery process ID if currently executing",
    )


class RecoveryExecutionDTO(BaseModel):
    """Summary of an executed recovery or simulation workflow."""

    recovery_id: str = Field(..., description="Unique recovery execution identifier")
    executed_at: str = Field(..., description="Execution start timestamp (ISO 8601)")
    recovery_type: str = Field(
        ...,
        description="Type: FAILOVER, ROLLBACK, PITR_RESTORE, SIMULATION",
    )
    stages_completed: List[str] = Field(
        default_factory=list,
        description="Completed recovery stages",
    )
    duration_seconds: float = Field(
        ..., description="Total execution duration in seconds"
    )
    rto_achieved_minutes: float = Field(
        ..., description="Achieved RTO duration in minutes"
    )
    rpo_estimated_minutes: float = Field(
        ..., description="Estimated data loss window in minutes"
    )
    rto_target_met: bool = Field(..., description="True if RTO < 60 min was met")
    rpo_target_met: bool = Field(..., description="True if RPO < 5 min was met")
    success: bool = Field(..., description="True if workflow completed without errors")
    details: str = Field(..., description="Summary details and validation notes")


class FailoverEventDTO(BaseModel):
    """Primary service failover event record."""

    event_id: str = Field(..., description="Unique failover event identifier")
    timestamp: str = Field(..., description="Event timestamp (ISO 8601)")
    triggered_by: str = Field(
        ...,
        description="Trigger source: AUTOMATED_DETECTOR, MANUAL_OPERATOR",
    )
    primary_endpoint: str = Field(..., description="Failed primary endpoint")
    secondary_endpoint: str = Field(..., description="Promoted secondary endpoint")
    status: str = Field(
        ...,
        description="State: TRIGGERED, IN_PROGRESS, COMPLETED, FAILED",
    )
    details: str = Field(
        ..., description="Operational details and health check results"
    )


class RollbackStatusDTO(BaseModel):
    """Application deployment rollback status."""

    rollback_id: str = Field(..., description="Unique rollback execution identifier")
    timestamp: str = Field(..., description="Rollback execution timestamp (ISO 8601)")
    current_version: str = Field(..., description="Version prior to rollback")
    target_version: str = Field(..., description="Version restored to")
    health_check_passed: bool = Field(
        ...,
        description="True if health validation passed after rollback",
    )
    status: str = Field(..., description="State: SUCCESS, FAILED")
    details: str = Field(..., description="Rollback execution summary")
