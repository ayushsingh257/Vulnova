"""Domain Entity: Discovery Engine & Target Asset Surface Models.

Pure domain definitions for Vulnova Discovery Engine.
No framework, database, or HTTP dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class AssetType(str, Enum):
    """Extensible Asset Surface Classification for Discovery Engine."""

    URL = "URL"
    ENDPOINT = "ENDPOINT"
    FORM = "FORM"
    SCRIPT = "SCRIPT"
    SUBDOMAIN = "SUBDOMAIN"
    API_SCHEMA = "API_SCHEMA"


@dataclass
class DiscoveredAsset:
    """Base Domain Asset representation designed for multi-phase discovery extensions."""

    id: UUID = field(default_factory=uuid4)
    asset_type: AssetType = AssetType.URL
    url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveredURL:
    """Discovered web link domain entity."""

    url: str
    method: str = "GET"
    depth: int = 0
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    title: Optional[str] = None


@dataclass
class DiscoveredForm:
    """Discovered HTML form DOM entity."""

    action_url: str
    method: str = "GET"
    inputs: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class DiscoveredScript:
    """Discovered JavaScript resource entity."""

    src_url: str
    is_external: bool = False


@dataclass
class DiscoveredNetworkRequest:
    """Interception representation for asynchronous fetch/XHR network requests."""

    url: str
    method: str = "GET"
    resource_type: str = "fetch"


@dataclass
class CrawlScope:
    """Crawl boundary parameters and SSRF constraints."""

    base_url: str
    allowed_domain: str
    allow_subdomains: bool = False
    max_depth: int = 3
    max_pages: int = 100
    concurrency_limit: int = 10


@dataclass
class CrawlResult:
    """Aggregate result from an async web crawl job."""

    target_url: str
    total_pages_crawled: int
    discovered_urls: List[DiscoveredURL] = field(default_factory=list)
    discovered_forms: List[DiscoveredForm] = field(default_factory=list)
    discovered_scripts: List[DiscoveredScript] = field(default_factory=list)
    network_requests: List[DiscoveredNetworkRequest] = field(default_factory=list)
    is_spa: bool = False
    duration_seconds: float = 0.0


class DNSRecordType(str, Enum):
    """Supported DNS Record Types for Subdomain & DNS Intelligence."""

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    NS = "NS"
    TXT = "TXT"


@dataclass
class DNSRecord:
    """DNS record domain entity."""

    record_type: DNSRecordType
    name: str
    value: str
    ttl: Optional[int] = None


@dataclass
class DiscoveredIP:
    """Classified IP finding entity for Enterprise ASM intelligence."""

    value: str
    classification: str = "PUBLIC"
    is_internal: bool = False
    is_egress_safe: bool = True


@dataclass
class DiscoveredSubdomain:
    """Subdomain intelligence asset entity."""

    subdomain: str
    ip_addresses: List[DiscoveredIP] = field(default_factory=list)
    cname_aliases: List[str] = field(default_factory=list)
    dns_records: List[DNSRecord] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)


@dataclass
class SubdomainScanResult:
    """Aggregate result from a Subdomain & DNS Intelligence scan."""

    target_domain: str
    total_subdomains: int
    discovered_subdomains: List[DiscoveredSubdomain] = field(default_factory=list)
    duration_seconds: float = 0.0


class TechCategory(str, Enum):
    """Technology classification categories."""

    WEB_SERVER = "WEB_SERVER"
    FRONTEND_FRAMEWORK = "FRONTEND_FRAMEWORK"
    BACKEND_FRAMEWORK = "BACKEND_FRAMEWORK"
    CMS = "CMS"
    JAVASCRIPT_LIBRARY = "JAVASCRIPT_LIBRARY"
    SECURITY_HEADER = "SECURITY_HEADER"
    CDN_PROXY = "CDN_PROXY"
    DATABASE = "DATABASE"
    ANALYTICS = "ANALYTICS"


@dataclass
class DetectedTechnology:
    """Technology fingerprint finding entity."""

    name: str
    category: TechCategory
    version: Optional[str] = None
    confidence: int = 100
    matched_by: List[str] = field(default_factory=list)


@dataclass
class SecurityHeaderStatus:
    """Audit status for security headers."""

    header_name: str
    present: bool
    value: Optional[str] = None


@dataclass
class TechnologyScanResult:
    """Aggregate result from a technology stack fingerprinting scan."""

    target_url: str
    status_code: Optional[int] = None
    detected_technologies: List[DetectedTechnology] = field(default_factory=list)
    security_headers: List[SecurityHeaderStatus] = field(default_factory=list)
    duration_seconds: float = 0.0


class AssetNodeType(str, Enum):
    """Types of nodes in Vulnova Attack Surface Asset Graph."""

    ORGANIZATION = "ORGANIZATION"
    TARGET_DOMAIN = "TARGET_DOMAIN"
    SUBDOMAIN = "SUBDOMAIN"
    IP_ADDRESS = "IP_ADDRESS"
    URL_ENDPOINT = "URL_ENDPOINT"
    FORM = "FORM"
    SCRIPT = "SCRIPT"
    TECHNOLOGY = "TECHNOLOGY"


class RelationshipType(str, Enum):
    """Types of relationships connecting nodes in Attack Surface Asset Graph."""

    BELONGS_TO = "BELONGS_TO"
    RESOLVES_TO = "RESOLVES_TO"
    RUNS_TECH = "RUNS_TECH"
    HAS_ENDPOINT = "HAS_ENDPOINT"
    DISCOVERED_FROM = "DISCOVERED_FROM"


@dataclass
class AssetNode:
    """Pure domain model representing a node in the Attack Surface Graph."""

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    node_type: AssetNodeType = AssetNodeType.TARGET_DOMAIN
    name: str = ""
    value: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetRelationship:
    """Pure domain model representing a edge connecting two asset nodes."""

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    source_node_id: UUID = field(default_factory=uuid4)
    target_node_id: UUID = field(default_factory=uuid4)
    relationship_type: RelationshipType = RelationshipType.BELONGS_TO
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetGraph:
    """Aggregate domain model representing an Attack Surface Asset Graph."""

    target_domain: str
    nodes: List[AssetNode] = field(default_factory=list)
    relationships: List[AssetRelationship] = field(default_factory=list)
    duration_seconds: float = 0.0
