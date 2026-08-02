"""Discovery Data Transfer Objects (DTOs) for Application Services and API Routers."""

from typing import Dict, List, Optional

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


class CrawlResponse(BaseModel):
    """Result response model for a completed target web crawl job."""

    target_url: str
    total_pages_crawled: int
    discovered_urls: List[DiscoveredURLDTO]
    discovered_forms: List[DiscoveredFormDTO]
    discovered_scripts: List[DiscoveredScriptDTO]
    duration_seconds: float
