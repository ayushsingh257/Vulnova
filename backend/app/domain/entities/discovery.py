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
    duration_seconds: float = 0.0
