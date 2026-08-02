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


class ConfidenceLevel(str, Enum):
    """Confidence rating of vulnerability detection accuracy."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AssetCriticality(str, Enum):
    """Business criticality rating of target asset."""

    CRITICAL = "CRITICAL"  # 1.5x risk multiplier
    HIGH = "HIGH"  # 1.2x risk multiplier
    MEDIUM = "MEDIUM"  # 1.0x risk multiplier
    LOW = "LOW"  # 0.8x risk multiplier


@dataclass
class CVSSMetrics:
    """CVSS v3.1 / v4 scoring parameters."""

    version: str = "3.1"
    base_score: float = 0.0
    vector_string: Optional[str] = None
    exploitability_score: Optional[float] = None
    impact_score: Optional[float] = None


@dataclass
class EPSSMetrics:
    """EPSS (Exploit Prediction Scoring System) parameters."""

    epss_score: float = 0.0  # 0.0 to 1.0 probability
    percentile: float = 0.0  # 0.0 to 1.0 percentile rank


@dataclass
class RiskMetrics:
    """Composite risk score and remediation SLA metrics."""

    composite_risk_score: float = 0.0  # 0.0 to 100.0
    business_impact: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW
    fix_sla_hours: int = 336  # Hours until SLA breach
    risk_level: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW


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
    asset_criticality: AssetCriticality = AssetCriticality.MEDIUM
    options: Dict[str, Any] = field(default_factory=dict)


class EvidenceType(str, Enum):
    """Classification types of evidence artifacts captured during assessment."""

    SCREENSHOT = "SCREENSHOT"
    DOM_SNAPSHOT = "DOM_SNAPSHOT"
    HTTP_REQUEST = "HTTP_REQUEST"
    HTTP_RESPONSE = "HTTP_RESPONSE"
    COOKIE_DATA = "COOKIE_DATA"
    HEADER_DATA = "HEADER_DATA"
    REDIRECT_CHAIN = "REDIRECT_CHAIN"
    TIMELINE_EVENT = "TIMELINE_EVENT"


@dataclass
class EvidenceArtifact:
    """Pure domain entity representing a proof artifact attached to a finding."""

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    finding_id: UUID = field(default_factory=uuid4)
    artifact_type: EvidenceType = EvidenceType.HTTP_RESPONSE
    storage_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: str = ""
    created_at: Optional[Any] = None


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

    # Phase 4.5 Intelligence & Normalization Extensions
    cvss: Optional[CVSSMetrics] = None
    epss: Optional[EPSSMetrics] = None
    risk: Optional[RiskMetrics] = None
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    is_duplicate: bool = False
    canonical_finding_id: Optional[UUID] = None
    deduplication_hash: Optional[str] = None

    # Phase 4.6 Multi-Modal Evidence Extensions
    artifacts: List[EvidenceArtifact] = field(default_factory=list)


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
