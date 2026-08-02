"""Pure Domain Entities and Plugin Abstractions for Vulnerability Assessment Engine."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.domain.entities.discovery import AssetNode, AssetNodeType


class SeverityLevel(str, Enum):
    """Vulnerability Finding Severity Ratings (CVSS Alignment)."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class VulnerabilityCategory(str, Enum):
    """Vulnerability Classification Categories (OWASP Alignment)."""

    SECURITY_HEADER = "SECURITY_HEADER"
    MISCONFIGURATION = "MISCONFIGURATION"
    INFORMATION_DISCLOSURE = "INFORMATION_DISCLOSURE"
    AUTHENTICATION = "AUTHENTICATION"
    INJECTION = "INJECTION"
    SSRF = "SSRF"
    DESERIALIZATION = "DESERIALIZATION"
    OTHER = "OTHER"


class PluginStatus(str, Enum):
    """Lifecycle status of a security assessment plugin."""

    REGISTERED = "REGISTERED"
    LOADED = "LOADED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AssessmentJobStatus(str, Enum):
    """Execution status of an assessment job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class PluginMetadata:
    """Metadata describing a security assessment plugin."""

    id: str
    name: str
    version: str
    description: str
    category: VulnerabilityCategory
    author: str
    supported_asset_types: List[AssetNodeType] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)


@dataclass
class AssessmentContext:
    """Execution context passed to assessment plugins."""

    target_url: str
    target_domain: str
    organization_id: UUID
    asset_nodes: List[AssetNode] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Finding:
    """Pure domain entity representing a security finding/vulnerability."""

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    assessment_job_id: UUID = field(default_factory=uuid4)
    plugin_id: str = ""
    title: str = ""
    description: str = ""
    severity: SeverityLevel = SeverityLevel.INFO
    category: VulnerabilityCategory = VulnerabilityCategory.OTHER
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    remediation: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    asset_node_id: Optional[UUID] = None


@dataclass
class AssessmentResult:
    """Aggregate result from executing assessment plugins."""

    job_id: UUID
    status: AssessmentJobStatus
    findings: List[Finding] = field(default_factory=list)
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


class BaseAssessmentPlugin(ABC):
    """Abstract Base Class for all security assessment plugins."""

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @abstractmethod
    async def execute(self, ctx: AssessmentContext) -> List[Finding]:
        """Execute vulnerability scanning logic on the target context."""
        pass
