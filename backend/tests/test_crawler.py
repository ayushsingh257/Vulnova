"""Unit and Integration Tests for Discovery Engine & Async Web Crawler."""

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import (
    get_current_active_user,
    get_current_user,
)
from app.api.v1.routers.discovery import router as discovery_router
from app.application.discovery.dto import CrawlRequest
from app.application.discovery.services import DiscoveryService
from app.core.exceptions import ValidationException, VulnovaException
from app.domain.entities.discovery import CrawlScope
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.discovery.crawler import AsyncWebCrawler
from app.infrastructure.discovery.ssrf_validator import (
    extract_base_domain,
    is_allowed_scheme,
    is_private_ip,
    is_safe_target_url,
    is_url_in_scope,
)
from app.main import vulnova_exception_handler

# ───────────────────────────────────────────────
# 1. SSRF & Safety Validator Tests
# ───────────────────────────────────────────────


def test_is_allowed_scheme() -> None:
    """Test scheme whitelist enforcement."""
    assert is_allowed_scheme("http://example.com") is True
    assert is_allowed_scheme("HTTPS://example.com/test") is True

    # Prohibited schemes
    assert is_allowed_scheme("file:///etc/passwd") is False
    assert is_allowed_scheme("ftp://example.com") is False
    assert is_allowed_scheme("gopher://127.0.0.1") is False
    assert is_allowed_scheme("javascript:alert(1)") is False
    assert is_allowed_scheme("data:text/html,<h1>test</h1>") is False


def test_is_private_ip() -> None:
    """Test private and metadata IP identification."""
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("169.254.169.254") is True
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("172.16.0.1") is True
    assert is_private_ip("192.168.1.1") is True
    assert is_private_ip("0.0.0.0") is True

    # Public IP
    assert is_private_ip("8.8.8.8") is False


def test_is_url_in_scope() -> None:
    """Test domain scope matching."""
    base = "example.com"

    assert is_url_in_scope("https://example.com/page1", base) is True
    assert is_url_in_scope("https://www.example.com/about", base) is True
    assert (
        is_url_in_scope("https://sub.example.com/api", base, allow_subdomains=False)
        is False
    )
    assert (
        is_url_in_scope("https://sub.example.com/api", base, allow_subdomains=True)
        is True
    )
    assert is_url_in_scope("https://evil.com/phish", base) is False
    assert is_url_in_scope("file:///etc/passwd", base) is False


def test_extract_base_domain() -> None:
    """Test base domain extraction from URLs."""
    assert extract_base_domain("https://api.shop.enterprise.com/v1") == "enterprise.com"
    assert extract_base_domain("http://example.org") == "example.org"


# ───────────────────────────────────────────────
# 2. Async Web Crawler Unit Tests
# ───────────────────────────────────────────────


def test_async_web_crawler_extraction() -> None:
    """Test AsyncWebCrawler DOM parsing and link/form/script extraction using MockTransport."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            scope = CrawlScope(
                base_url="http://example.com",
                allowed_domain="example.com",
                max_depth=2,
                max_pages=5,
                concurrency_limit=2,
            )

            html_body = """
            <html>
                <head>
                    <title>Test Security Target</title>
                    <script src="/static/app.js"></script>
                    <script src="https://cdn.external.com/lib.js"></script>
                </head>
                <body>
                    <a href="/login">Login Page</a>
                    <a href="https://example.com/about">About Us</a>
                    <a href="https://prohibited.com/test">External Link</a>
                    <form action="/api/v1/auth" method="POST">
                        <input type="text" name="username" />
                        <input type="password" name="password" />
                    </form>
                </body>
            </html>
            """

            def _handler(request: httpx.Request) -> httpx.Response:
                if str(request.url).rstrip("/") == "http://example.com":
                    return httpx.Response(
                        200,
                        html=html_body,
                        headers={"Content-Type": "text/html; charset=utf-8"},
                    )
                return httpx.Response(
                    200,
                    html="<html><head><title>Subpage</title></head><body>OK</body></html>",
                    headers={"Content-Type": "text/html"},
                )

            transport = httpx.MockTransport(_handler)

            crawler = AsyncWebCrawler(scope)

            async with httpx.AsyncClient(
                transport=transport, follow_redirects=True
            ) as client:
                targets = await crawler._fetch_and_parse(
                    client, "http://example.com", depth=0
                )

            assert crawler.pages_crawled == 1
            assert len(crawler.discovered_forms) == 1
            assert (
                crawler.discovered_forms[0].action_url
                == "http://example.com/api/v1/auth"
            )
            assert crawler.discovered_forms[0].method == "POST"
            assert len(crawler.discovered_forms[0].inputs) == 2

            assert len(crawler.discovered_scripts) == 2
            assert len(targets) == 2  # /login and /about

        loop.run_until_complete(_run())
    finally:
        loop.close()


# ───────────────────────────────────────────────
# 3. Discovery Service Unit Tests
# ───────────────────────────────────────────────


def test_discovery_service_ssrf_rejection() -> None:
    """Test DiscoveryService rejects crawling loopback or internal IPs."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = DiscoveryService(mock_session)

            caller = MagicMock(spec=UserModel)
            caller.id = uuid4()
            caller.organization_id = uuid4()

            req = CrawlRequest(target_url="http://127.0.0.1/admin")

            with pytest.raises(ValidationException) as exc_info:
                await service.crawl_target(req, caller)

            assert "Target URL is prohibited" in str(exc_info.value)

        loop.run_until_complete(_run())
    finally:
        loop.close()


# ───────────────────────────────────────────────
# 4. FastAPI Endpoint Integration Tests
# ───────────────────────────────────────────────

discovery_test_app = FastAPI()
discovery_test_app.add_exception_handler(VulnovaException, vulnova_exception_handler)
discovery_test_app.include_router(discovery_router)

test_org_id = uuid4()
mock_analyst = MagicMock(spec=UserModel)
mock_analyst.id = uuid4()
mock_analyst.organization_id = test_org_id
mock_analyst.role = "SECURITY_ANALYST"
mock_analyst.is_active = True


def _override_user() -> UserModel:
    return mock_analyst


discovery_test_app.dependency_overrides[get_current_user] = _override_user
discovery_test_app.dependency_overrides[get_current_active_user] = _override_user
discovery_test_app.dependency_overrides[get_current_user_or_api_key] = _override_user


def test_discovery_crawl_endpoint_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /discovery/crawl triggers web crawl job when authorized."""
    mock_service = AsyncMock()
    mock_service.crawl_target.return_value = {
        "target_url": "https://example.com",
        "total_pages_crawled": 3,
        "discovered_urls": [
            {
                "url": "https://example.com/about",
                "method": "GET",
                "depth": 1,
                "status_code": 200,
                "content_type": "text/html",
                "title": "About Us",
            }
        ],
        "discovered_forms": [],
        "discovered_scripts": [],
        "duration_seconds": 0.45,
    }
    monkeypatch.setattr(
        "app.api.v1.routers.discovery.DiscoveryService",
        lambda session: mock_service,
    )

    client = TestClient(discovery_test_app)
    payload = {
        "target_url": "https://example.com",
        "max_depth": 2,
        "max_pages": 50,
        "concurrency_limit": 5,
        "allow_subdomains": False,
    }
    response = client.post("/discovery/crawl", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["target_url"] == "https://example.com"
    assert data["total_pages_crawled"] == 3
