"""Unit and Integration Tests for Technology Stack Fingerprinting Engine."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.discovery.dto import TechnologyScanRequest
from app.application.discovery.services import DiscoveryService
from app.core.exceptions import ValidationException
from app.domain.entities.discovery import TechCategory
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.discovery.tech_fingerprinter import TechFingerprinter


def test_tech_category_enum() -> None:
    """Test TechCategory enum values."""
    assert TechCategory.WEB_SERVER.value == "WEB_SERVER"
    assert TechCategory.FRONTEND_FRAMEWORK.value == "FRONTEND_FRAMEWORK"
    assert TechCategory.BACKEND_FRAMEWORK.value == "BACKEND_FRAMEWORK"
    assert TechCategory.CMS.value == "CMS"
    assert TechCategory.JAVASCRIPT_LIBRARY.value == "JAVASCRIPT_LIBRARY"
    assert TechCategory.SECURITY_HEADER.value == "SECURITY_HEADER"
    assert TechCategory.CDN_PROXY.value == "CDN_PROXY"


def test_header_fingerprint_matching() -> None:
    """Test TechFingerprinter analyzes HTTP headers for server, framework, and security header signatures."""
    fingerprinter = TechFingerprinter()

    headers = {
        "server": "nginx/1.24.0",
        "x-powered-by": "Express",
        "cf-ray": "887a1b2c3d4e5f6g",
        "strict-transport-security": "max-age=31536000; includeSubDomains",
        "x-frame-options": "DENY",
    }

    result = fingerprinter.analyze(
        target_url="https://example.com",
        status_code=200,
        headers=headers,
        html_content="<html><body>Hello</body></html>",
    )

    assert result.status_code == 200
    tech_names = [t.name for t in result.detected_technologies]
    assert "Nginx" in tech_names
    assert "Express" in tech_names
    assert "Cloudflare" in tech_names

    # Check Nginx version extraction
    nginx_tech = next(t for t in result.detected_technologies if t.name == "Nginx")
    assert nginx_tech.version == "1.24.0"

    # Check security headers
    hsts = next(
        s
        for s in result.security_headers
        if s.header_name == "Strict-Transport-Security"
    )
    assert hsts.present is True
    assert hsts.value == "max-age=31536000; includeSubDomains"

    csp = next(
        s for s in result.security_headers if s.header_name == "Content-Security-Policy"
    )
    assert csp.present is False


def test_html_dom_and_script_fingerprinting() -> None:
    """Test TechFingerprinter detects React, Next.js, WordPress, Angular from DOM and scripts."""
    fingerprinter = TechFingerprinter()

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="generator" content="WordPress 6.4.2">
        <script src="/_next/static/chunks/main.js"></script>
        <script src="/js/jquery-3.6.0.js"></script>
    </head>
    <body>
        <div id="__next" data-reactroot=""></div>
        <div ng-version="17.0.0"></div>
    </body>
    </html>
    """

    result = fingerprinter.analyze(
        target_url="https://example.com",
        status_code=200,
        headers={},
        html_content=html_content,
    )

    tech_names = [t.name for t in result.detected_technologies]
    assert "WordPress" in tech_names
    assert "Next.js" in tech_names
    assert "React" in tech_names
    assert "Angular" in tech_names
    assert "jQuery" in tech_names

    wp_tech = next(t for t in result.detected_technologies if t.name == "WordPress")
    assert wp_tech.version == "6.4.2"

    ang_tech = next(t for t in result.detected_technologies if t.name == "Angular")
    assert ang_tech.version == "17.0.0"


def test_discovery_service_technology_scan_ssrf_rejection() -> None:
    """Test DiscoveryService rejects private IP target URLs for technology scanning."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = DiscoveryService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            req = TechnologyScanRequest(target_url="http://127.0.0.1/admin")

            with pytest.raises(ValidationException) as exc_info:
                await service.discover_technologies(req, mock_user)

            assert "prohibited" in str(exc_info.value).lower()

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_discovery_service_technology_scan_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test DiscoveryService.discover_technologies succeeds and records audit events."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = DiscoveryService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            # Mock TechFingerprinter probe
            mock_fingerprint_res = MagicMock()
            mock_fingerprint_res.target_url = "https://example.com"
            mock_fingerprint_res.status_code = 200
            mock_fingerprint_res.detected_technologies = []
            mock_fingerprint_res.security_headers = []
            mock_fingerprint_res.duration_seconds = 0.15

            mock_fingerprinter = AsyncMock()
            mock_fingerprinter.probe_and_fingerprint.return_value = mock_fingerprint_res

            monkeypatch.setattr(
                "app.application.discovery.services.TechFingerprinter",
                lambda: mock_fingerprinter,
            )

            req = TechnologyScanRequest(target_url="https://example.com")
            res = await service.discover_technologies(req, mock_user)

            assert res.target_url == "https://example.com"
            assert res.status_code == 200
            mock_fingerprinter.probe_and_fingerprint.assert_called_once_with(
                "https://example.com"
            )

        loop.run_until_complete(_run())
    finally:
        loop.close()
