"""Unit and Integration Tests for Phase 7.2 Public Trust Center & Security Disclosures.

Tests:
1. TrustCenterService summary aggregation & OWASP ASVS mappings.
2. RFC 9116 security.txt text generation.
3. Public REST API endpoints (/api/v1/public/trust, /status, /security-disclosure, /.well-known/security.txt).
4. Public data boundary security (zero tenant/target/finding leakage).
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.assessment.trust_center_service import TrustCenterService
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_trust_center_service_summary() -> None:
    """Test TrustCenterService public summary generation and OWASP ASVS grid."""
    session = AsyncMock()
    redis_client = AsyncMock()
    redis_client.get.return_value = None

    service = TrustCenterService(session=session, redis_client=redis_client)
    summary = await service.get_public_trust_center_summary()

    assert summary.platform_name.startswith("Vulnova")
    assert summary.system_status in ["OPERATIONAL", "DEGRADED_PERFORMANCE"]
    assert "OWASP ASVS" in summary.asvs_alignment
    assert len(summary.security_practices_grid) >= 5
    assert any(
        p.category == "V17_WORKER_SANDBOX" for p in summary.security_practices_grid
    )
    assert any(p.category == "V6_CRYPTOGRAPHY" for p in summary.security_practices_grid)


@pytest.mark.anyio
async def test_security_txt_generation() -> None:
    """Test RFC 9116 security.txt plain text formatting."""
    service = TrustCenterService(session=AsyncMock())
    content = service.get_security_txt_content()

    assert "Contact: mailto:security@vulnova.com" in content
    assert "Expires:" in content
    assert "Preferred-Languages: en, es" in content
    assert "Canonical: https://vulnova.com/.well-known/security.txt" in content


@pytest.mark.anyio
async def test_public_api_trust_endpoint() -> None:
    """Test GET /api/v1/public/trust REST endpoint without authentication headers."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        res = await client.get("/api/v1/public/trust")
        assert res.status_code == 200
        data = res.json()
        assert "platform_name" in data
        assert (
            data["asvs_alignment"] == "Security Controls Mapped Against OWASP ASVS v4.0"
        )
        assert len(data["security_practices_grid"]) > 0


@pytest.mark.anyio
async def test_public_api_status_endpoint() -> None:
    """Test GET /api/v1/public/status REST endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        res = await client.get("/api/v1/public/status")
        assert res.status_code == 200
        data = res.json()
        assert data["system_status"] in ["OPERATIONAL", "DEGRADED_PERFORMANCE"]


@pytest.mark.anyio
async def test_well_known_security_txt_endpoint() -> None:
    """Test GET /.well-known/security.txt endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        res = await client.get("/.well-known/security.txt")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/plain")
        assert "Contact: mailto:security@vulnova.com" in res.text


@pytest.mark.anyio
async def test_public_data_boundary_security() -> None:
    """Security Test: Verify zero tenant IDs, target URLs, or findings leak via public endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        res = await client.get("/api/v1/public/trust")
        assert res.status_code == 200
        text = res.text.lower()

        # Sensitive field keywords that must NEVER leak
        forbidden_terms = [
            "organization_id",
            "scan_target_id",
            "target_url",
            "finding_id",
            "password",
            "secret",
            "private_key",
        ]
        for term in forbidden_terms:
            assert (
                term not in text
            ), f"Security Boundary Leak: Forbidden term '{term}' found in public endpoint response!"
