"""Unit and Integration Tests for Phase 4.5 Risk Intelligence and Finding Deduplication Engine."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.assessment.deduplication import FindingDeduplicator
from app.application.assessment.dto import CreateAssessmentRequest
from app.application.assessment.risk_engine import (
    RiskIntelligenceEngine,
    calculate_asset_factor,
    calculate_cvss_factor,
    calculate_epss_factor,
    calculate_final_risk_score,
    calculate_severity_factor,
)
from app.application.assessment.services import AssessmentService
from app.domain.entities.assessment import (
    AssetCriticality,
    ConfidenceLevel,
    CVSSMetrics,
    EPSSMetrics,
    Finding,
    SeverityLevel,
    VulnerabilityCategory,
)
from app.infrastructure.assessment.plugins.headers_plugin import (
    SecurityHeadersPlugin,
)
from app.infrastructure.database.models.user import UserModel


def test_risk_engine_scoring_factors() -> None:
    """Test individual scoring factor calculation functions."""
    assert calculate_severity_factor(SeverityLevel.CRITICAL) == 9.8
    assert calculate_severity_factor(SeverityLevel.LOW) == 2.5

    cvss = CVSSMetrics(base_score=9.1)
    assert calculate_cvss_factor(cvss, 5.0) == 9.1
    assert calculate_cvss_factor(None, 7.5) == 7.5

    epss = EPSSMetrics(epss_score=0.88)
    assert calculate_epss_factor(epss) == 0.88
    assert calculate_epss_factor(None) == 0.20

    assert calculate_asset_factor(AssetCriticality.CRITICAL) == 1.5
    assert calculate_asset_factor(AssetCriticality.LOW) == 0.8


def test_risk_engine_critical_finding() -> None:
    """Test RiskIntelligenceEngine enriches Critical finding with CVSS, EPSS, SLA, and >85 risk score."""
    engine = RiskIntelligenceEngine()
    finding = Finding(
        title="SQL Injection in Login Endpoint",
        severity=SeverityLevel.CRITICAL,
        category=VulnerabilityCategory.INJECTION,
        cwe_id="CWE-89",
        cvss=CVSSMetrics(
            version="3.1",
            base_score=9.8,
            vector_string="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        ),
        epss=EPSSMetrics(epss_score=0.92, percentile=0.98),
        confidence=ConfidenceLevel.HIGH,
    )

    enriched = engine.enrich_finding(finding, AssetCriticality.HIGH)
    assert enriched.risk is not None
    assert enriched.risk.composite_risk_score >= 85.0
    assert enriched.risk.business_impact == "CRITICAL"
    assert enriched.risk.fix_sla_hours == 24


def test_risk_engine_medium_finding() -> None:
    """Test RiskIntelligenceEngine enriches Medium finding with 14-day SLA (336h)."""
    engine = RiskIntelligenceEngine()
    finding = Finding(
        title="Missing X-Frame-Options Header",
        severity=SeverityLevel.MEDIUM,
        category=VulnerabilityCategory.SECURITY_HEADER,
        cwe_id="CWE-1021",
        confidence=ConfidenceLevel.HIGH,
    )

    enriched = engine.enrich_finding(finding, AssetCriticality.MEDIUM)
    assert enriched.risk is not None
    assert enriched.risk.business_impact == "MEDIUM"
    assert enriched.risk.fix_sla_hours == 336


def test_risk_engine_missing_cvss_epss_fallbacks() -> None:
    """Test RiskIntelligenceEngine handles missing CVSS/EPSS with safe defaults."""
    engine = RiskIntelligenceEngine()
    finding = Finding(
        title="Custom Scanner Finding",
        severity=SeverityLevel.HIGH,
        category=VulnerabilityCategory.OTHER,
        cvss=None,
        epss=None,
    )

    enriched = engine.enrich_finding(finding, AssetCriticality.MEDIUM)
    assert enriched.cvss is not None
    assert enriched.cvss.base_score == 7.5
    assert enriched.epss is not None
    assert enriched.epss.epss_score == 0.40
    assert enriched.risk is not None
    assert enriched.risk.fix_sla_hours == 72


def test_risk_engine_asset_criticality_multiplier() -> None:
    """Test higher asset criticality yields a higher composite risk score."""
    score_critical = calculate_final_risk_score(
        severity=SeverityLevel.HIGH,
        cvss=CVSSMetrics(base_score=8.0),
        epss=EPSSMetrics(epss_score=0.50),
        criticality=AssetCriticality.CRITICAL,
        confidence=ConfidenceLevel.HIGH,
    )
    score_low = calculate_final_risk_score(
        severity=SeverityLevel.HIGH,
        cvss=CVSSMetrics(base_score=8.0),
        epss=EPSSMetrics(epss_score=0.50),
        criticality=AssetCriticality.LOW,
        confidence=ConfidenceLevel.HIGH,
    )
    assert score_critical > score_low


def test_deduplication_same_vulnerability_same_endpoint() -> None:
    """Test FindingDeduplicator links identical duplicate findings to canonical finding."""
    dedup = FindingDeduplicator()
    org_id = uuid4()

    f1 = Finding(
        organization_id=org_id,
        plugin_id="sql_injection_plugin",
        category=VulnerabilityCategory.INJECTION,
        cwe_id="CWE-89",
        title="SQL Injection",
        evidence={"probe_url": "https://example.com/api/users?id=1"},
    )
    f2 = Finding(
        organization_id=org_id,
        plugin_id="sql_injection_plugin",
        category=VulnerabilityCategory.INJECTION,
        cwe_id="CWE-89",
        title="SQL Injection",
        evidence={"probe_url": "https://example.com/api/users?id=1"},
    )

    result = dedup.deduplicate_findings([f1, f2])
    assert len(result) == 2
    assert result[0].is_duplicate is False
    assert result[0].canonical_finding_id is None

    assert result[1].is_duplicate is True
    assert result[1].canonical_finding_id == result[0].id


def test_deduplication_different_endpoints() -> None:
    """Test FindingDeduplicator treats findings on different endpoints as unique canonical findings."""
    dedup = FindingDeduplicator()
    org_id = uuid4()

    f1 = Finding(
        organization_id=org_id,
        plugin_id="xss_plugin",
        cwe_id="CWE-79",
        title="Reflected XSS in search",
        evidence={"probe_url": "https://example.com/search?q=test"},
    )
    f2 = Finding(
        organization_id=org_id,
        plugin_id="xss_plugin",
        cwe_id="CWE-79",
        title="Reflected XSS in profile",
        evidence={"probe_url": "https://example.com/profile?name=test"},
    )

    result = dedup.deduplicate_findings([f1, f2])
    assert result[0].is_duplicate is False
    assert result[1].is_duplicate is False


def test_assessment_service_risk_and_deduplication_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration test verifying AssessmentService applies risk enrichment and deduplication before DB persistence."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AssessmentService(mock_session)

            service.plugin_registry.clear()
            service.plugin_registry.register(SecurityHeadersPlugin())

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            mock_job = MagicMock()
            mock_job.id = uuid4()
            mock_job.target_url = "https://example.com"
            mock_job.execution_state = "QUEUED"
            mock_job.created_at = "2026-08-02T18:30:00Z"

            service.repo.create_job = AsyncMock(return_value=mock_job)
            service.repo.get_job_by_id = AsyncMock(return_value=mock_job)
            service.repo.update_execution_state = AsyncMock(return_value=mock_job)
            service.repo.update_job_status = AsyncMock()
            service.repo.create_finding = AsyncMock()

            # Mock HTTP response missing Content-Security-Policy
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "text/html"}
            mock_resp.text = "<html><body>Hello</body></html>"

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

            service.assessment_policy_engine.validate_scan_authorization = AsyncMock(
                return_value=MagicMock(is_allowed=True, rejection_reason=None)
            )

            req = CreateAssessmentRequest(
                target_url="https://example.com",
                is_authorized_assessment=True,
            )
            res = await service.create_and_run_assessment(req, mock_user)

            assert res.status == "COMPLETED"
            assert res.total_findings >= 1

            finding_dto = res.findings[0]
            assert finding_dto.risk_score is not None
            assert finding_dto.business_impact is not None
            assert finding_dto.fix_sla_hours is not None
            assert finding_dto.is_duplicate is False

        loop.run_until_complete(_run())
    finally:
        loop.close()
