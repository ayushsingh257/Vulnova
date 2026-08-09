"""Data Transfer Objects for Enterprise Scanner Sandbox Infrastructure."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SandboxStatus(str, Enum):
    """Lifecycle status enum for ephemeral scanner sandboxes."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DESTROYED = "DESTROYED"


class SandboxSecurityConfigDTO(BaseModel):
    """Security constraints for scanner container sandbox isolation."""

    cpu_limit: str = Field(default="1.0", description="CPU quota allocation limit")
    memory_limit: str = Field(default="512m", description="Memory allocation limit")
    max_processes: int = Field(
        default=100, description="Process limit (nproc / pids_limit)"
    )
    execution_timeout_seconds: int = Field(
        default=1800, description="Max execution duration"
    )
    read_only_rootfs: bool = Field(
        default=True, description="Enforce read-only root filesystem"
    )
    non_root_uid: int = Field(default=10001, description="Non-root user UID (appuser)")
    non_root_gid: int = Field(default=10001, description="Non-root group GID")
    drop_capabilities: List[str] = Field(
        default_factory=lambda: ["ALL"], description="Linux capabilities to drop"
    )
    no_new_privileges: bool = Field(
        default=True, description="Prevent privilege escalation via setuid/setgid"
    )
    network_mode: str = Field(
        default="vulnova_sandbox_net", description="Isolated container network name"
    )
    prohibited_ip_ranges: List[str] = Field(
        default_factory=lambda: [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "127.0.0.1/8",
            "169.254.169.254/32",
        ],
        description="RFC1918 private IP and cloud metadata blocklist",
    )


class SandboxCreationRequestDTO(BaseModel):
    """Payload to request instantiation of a single-use scanner sandbox."""

    organization_id: UUID
    scan_job_id: UUID
    target_url: str
    enabled_plugins: List[str] = Field(default_factory=list)
    custom_security_config: Optional[SandboxSecurityConfigDTO] = None


class SandboxExecutionResultDTO(BaseModel):
    """Output metrics and findings from a sandboxed scanner run."""

    sandbox_id: UUID
    container_id: str
    scan_job_id: UUID
    status: SandboxStatus
    exit_code: int
    duration_seconds: float
    raw_findings: List[Dict[str, Any]] = Field(default_factory=list)
    error_log: Optional[str] = None
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)


class ScannerSandboxDTO(BaseModel):
    """API representation of a scanner execution sandbox."""

    id: UUID
    organization_id: UUID
    scan_job_id: UUID
    container_id: str
    image_name: str
    status: SandboxStatus
    cpu_limit: str
    memory_limit: str
    read_only_rootfs: bool
    network_mode: str
    exit_code: Optional[int] = None
    execution_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    destroyed_at: Optional[datetime] = None
