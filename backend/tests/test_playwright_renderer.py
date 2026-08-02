"""Unit and Integration Tests for Playwright SPA Dynamic DOM Renderer and Fallback."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.discovery.dto import CrawlRequest
from app.application.discovery.services import DiscoveryService
from app.domain.entities.discovery import CrawlScope
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.discovery.playwright_renderer import (
    PlaywrightUnavailableException,
    SPADynamicCrawler,
)


def test_crawl_request_render_js_default() -> None:
    """Test render_js parameter defaults to False in CrawlRequest."""
    req = CrawlRequest(target_url="https://example.com")
    assert req.render_js is False

    req_js = CrawlRequest(target_url="https://example.com", render_js=True)
    assert req_js.render_js is True


def test_playwright_unavailable_exception_raising() -> None:
    """Test PlaywrightUnavailableException instantiates properly."""
    exc = PlaywrightUnavailableException("Browser binaries missing")
    assert "Browser binaries missing" in str(exc)


def test_discovery_service_playwright_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test DiscoveryService gracefully falls back to static crawler if Playwright is unavailable."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = DiscoveryService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            # Mock Playwright to raise PlaywrightUnavailableException
            mock_spa_crawler = AsyncMock()
            mock_spa_crawler.crawl.side_effect = PlaywrightUnavailableException(
                "Chromium executable not found"
            )
            monkeypatch.setattr(
                "app.application.discovery.services.SPADynamicCrawler",
                lambda scope: mock_spa_crawler,
            )

            # Mock Static Crawler to succeed
            mock_static_crawler = AsyncMock()
            mock_static_result = MagicMock()
            mock_static_result.target_url = "https://example.com"
            mock_static_result.total_pages_crawled = 1
            mock_static_result.discovered_urls = []
            mock_static_result.discovered_forms = []
            mock_static_result.discovered_scripts = []
            mock_static_result.network_requests = []
            mock_static_result.is_spa = False
            mock_static_result.duration_seconds = 0.2
            mock_static_crawler.crawl.return_value = mock_static_result

            monkeypatch.setattr(
                "app.application.discovery.services.AsyncWebCrawler",
                lambda scope: mock_static_crawler,
            )

            req = CrawlRequest(target_url="https://example.com", render_js=True)
            res = await service.crawl_target(req, mock_user)

            assert res.target_url == "https://example.com"
            assert res.is_spa is False
            mock_spa_crawler.crawl.assert_called_once()
            mock_static_crawler.crawl.assert_called_once()

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_spa_dynamic_crawler_lazy_playwright_handling() -> None:
    """Test SPADynamicCrawler handles missing Playwright environment cleanly."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            scope = CrawlScope(
                base_url="https://example.com",
                allowed_domain="example.com",
            )
            crawler = SPADynamicCrawler(scope)

            # If Playwright is not installed / executable missing in test environment, it raises PlaywrightUnavailableException
            try:
                result = await crawler.crawl()
                # If Playwright IS installed and working:
                assert result.target_url == "https://example.com"
            except PlaywrightUnavailableException as e:
                # If Playwright is NOT installed or binaries missing:
                assert "Playwright" in str(e) or "Chromium" in str(e)

        loop.run_until_complete(_run())
    finally:
        loop.close()
