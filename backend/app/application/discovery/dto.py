"""Discovery Data Transfer Objects (DTOs) for Application Services and API Routers."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class CrawlRequest(BaseModel):
    """Payload for triggering an async target web crawl job."""

    target_url: HttpUrl = Field(
        description="Explicit target URL to crawl (must be HTTP/HTTPS and publicly resolvable)"
    )
    max_depth: int = Field(
        default=3, ge=1, le=5, description="Maximum link crawl depth (1–5)"
    )
    max_pages: int = Field(
        default=100, ge=1, le=500, description="Maximum pages to crawl (1–500)"
    )
    concurrency_limit: int = Field(
        default=10, ge=1, le=20, description="Concurrent request limit (1–20)"
    )
    allow_subdomains: bool = Field(
        default=False,
        description="True to allow crawling subdomains of target base domain",
    )
    render_js: bool = Field(
        default=False,
        description="True to enable headless Chromium SPA dynamic DOM rendering",
    )


class DiscoveredURLDTO(BaseModel):
    """DTO representing a discovered target URL."""

    url: str
    method: str = "GET"
    depth: int
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    title: Optional[str] = None


class DiscoveredFormDTO(BaseModel):
    """DTO representing a discovered HTML form."""

    action_url: str
    method: str = "GET"
    inputs: List[Dict[str, str]]


class DiscoveredScriptDTO(BaseModel):
    """DTO representing a discovered JavaScript resource."""

    src_url: str
    is_external: bool


class DiscoveredNetworkRequestDTO(BaseModel):
    """DTO representing an intercepted background fetch/XHR network request."""

    url: str
    method: str = "GET"
    resource_type: str = "fetch"


class CrawlResponse(BaseModel):
    """Result response model for a completed target web crawl job."""

    target_url: str
    total_pages_crawled: int
    discovered_urls: List[DiscoveredURLDTO]
    discovered_forms: List[DiscoveredFormDTO]
    discovered_scripts: List[DiscoveredScriptDTO]
    network_requests: List[DiscoveredNetworkRequestDTO] = Field(default_factory=list)
    is_spa: bool = False
    duration_seconds: float


class IPAddressInfoDTO(BaseModel):
    """DTO representing classified IP metadata."""

    value: str
    classification: str = "PUBLIC"
    is_internal: bool = False
    is_egress_safe: bool = True


class DNSRecordDTO(BaseModel):
    """DTO representing a DNS record (A, AAAA, CNAME, MX, NS, TXT)."""

    record_type: str
    name: str
    value: str
    ttl: Optional[int] = None


class DiscoveredSubdomainDTO(BaseModel):
    """DTO representing a discovered subdomain intelligence finding."""

    subdomain: str
    ip_addresses: List[IPAddressInfoDTO] = Field(default_factory=list)
    cname_aliases: List[str] = Field(default_factory=list)
    dns_records: List[DNSRecordDTO] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


class SubdomainScanRequest(BaseModel):
    """Payload for triggering a Subdomain & DNS Intelligence discovery scan."""

    target_domain: str = Field(
        description="Target base domain (e.g. 'example.com') to discover subdomains and DNS records"
    )
    include_ct_logs: bool = Field(
        default=True,
        description="True to query passive Certificate Transparency (CT) log history",
    )
    resolve_dns: bool = Field(
        default=True,
        description="True to perform async DNS resolution (A, AAAA, CNAME, MX, NS, TXT)",
    )


class SubdomainScanResponse(BaseModel):
    """Response model for a completed Subdomain & DNS Intelligence scan."""

    target_domain: str
    total_subdomains: int
    discovered_subdomains: List[DiscoveredSubdomainDTO]
    duration_seconds: float


class TechnologyScanRequest(BaseModel):
    """Payload for triggering a Technology Stack Fingerprinting scan."""

    target_url: HttpUrl = Field(
        description="Explicit target URL to fingerprint technology stack (must be HTTP/HTTPS)"
    )


class DetectedTechnologyDTO(BaseModel):
    """DTO representing a detected technology fingerprint finding."""

    name: str
    category: str
    version: Optional[str] = None
    confidence: int = 100
    matched_by: List[str] = Field(default_factory=list)


class SecurityHeaderDTO(BaseModel):
    """DTO representing a security header audit status."""

    header_name: str
    present: bool
    value: Optional[str] = None


class TechnologyScanResponse(BaseModel):
    """Response model for a completed Technology Stack Fingerprinting scan."""

    target_url: str
    status_code: Optional[int] = None
    detected_technologies: List[DetectedTechnologyDTO] = Field(default_factory=list)
    security_headers: List[SecurityHeaderDTO] = Field(default_factory=list)
    duration_seconds: float


class BuildAssetGraphRequest(BaseModel):
    """Payload for building or correlation scanning an Attack Surface Asset Graph."""

    target_domain: str = Field(
        description="Target base domain (e.g. 'example.com') to map into Attack Surface Graph"
    )
    include_crawls: bool = Field(
        default=True,
        description="True to run static/dynamic web crawling for target domain",
    )
    include_dns: bool = Field(
        default=True,
        description="True to run subdomain discovery & DNS record resolution",
    )
    include_tech: bool = Field(
        default=True,
        description="True to run technology stack fingerprinting",
    )


class AssetNodeDTO(BaseModel):
    """DTO representing a node in the Attack Surface Graph."""

    id: str
    node_type: str
    name: str
    value: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetRelationshipDTO(BaseModel):
    """DTO representing an edge connecting two nodes in Attack Surface Graph."""

    id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetGraphResponse(BaseModel):
    """Response model for Attack Surface Asset Graph build queries."""

    target_domain: str
    total_nodes: int
    total_relationships: int
    nodes: List[AssetNodeDTO]
    relationships: List[AssetRelationshipDTO]
    duration_seconds: float
