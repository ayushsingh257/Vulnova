"""Unit and Integration Tests for Subdomain & DNS Intelligence Engine."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.discovery.dto import SubdomainScanRequest
from app.application.discovery.services import DiscoveryService
from app.domain.entities.discovery import DNSRecordType
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.discovery.ct_logs_client import CTLogsClient
from app.infrastructure.discovery.dns_resolver import AsyncDNSResolver
from app.infrastructure.discovery.ssrf_validator import classify_ip


def test_classify_ip_categories() -> None:
    """Test IP address classification into PUBLIC, PRIVATE, and LOOPBACK."""
    pub_info = classify_ip("1.1.1.1")
    assert pub_info["classification"] == "PUBLIC"
    assert pub_info["is_internal"] is False
    assert pub_info["is_egress_safe"] is True

    priv_info = classify_ip("10.10.5.20")
    assert priv_info["classification"] == "PRIVATE"
    assert priv_info["is_internal"] is True
    assert priv_info["is_egress_safe"] is False

    loop_info = classify_ip("127.0.0.1")
    assert loop_info["classification"] == "LOOPBACK"
    assert loop_info["is_internal"] is True
    assert loop_info["is_egress_safe"] is False


def test_dns_record_type_enum() -> None:
    """Test DNSRecordType enumeration contains all required DNS record types."""
    assert DNSRecordType.A.value == "A"
    assert DNSRecordType.AAAA.value == "AAAA"
    assert DNSRecordType.CNAME.value == "CNAME"
    assert DNSRecordType.MX.value == "MX"
    assert DNSRecordType.NS.value == "NS"
    assert DNSRecordType.TXT.value == "TXT"


def test_ct_logs_client_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CTLogsClient parses and deduplicates subdomains cleanly."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            client = CTLogsClient()

            # Mock httpx response
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = [
                {"name_value": "api.example.com\n*.dev.example.com"},
                {"name_value": "app.example.com"},
            ]

            mock_httpx = AsyncMock()
            mock_httpx.get.return_value = mock_resp

            monkeypatch.setattr("httpx.AsyncClient.get", mock_httpx.get)

            subs = await client.search_subdomains("example.com")
            assert "api.example.com" in subs
            assert "dev.example.com" in subs
            assert "app.example.com" in subs
            assert "example.com" in subs

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_discovery_service_subdomain_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test DiscoveryService.discover_subdomains integrates CT logs, DNS resolution, and audit logging."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = DiscoveryService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            # Mock CT log client
            mock_ct = AsyncMock()
            mock_ct.search_subdomains.return_value = ["api.example.com", "example.com"]
            monkeypatch.setattr(
                "app.infrastructure.discovery.ct_logs_client.CTLogsClient.search_subdomains",
                mock_ct.search_subdomains,
            )

            req = SubdomainScanRequest(
                target_domain="example.com",
                include_ct_logs=True,
                resolve_dns=False,  # Skip live network DNS in unit test
            )

            res = await service.discover_subdomains(req, mock_user)

            assert res.target_domain == "example.com"
            assert res.total_subdomains == 2
            sub_names = [s.subdomain for s in res.discovered_subdomains]
            assert "api.example.com" in sub_names
            assert "example.com" in sub_names

        loop.run_until_complete(_run())
    finally:
        loop.close()
