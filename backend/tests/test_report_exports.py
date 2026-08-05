"""Unit and Integration Test Suite for Developer Technical Remediation Exports."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.report_exports import get_developer_export_service
from app.application.assessment.dto import (
    AttackPathNodeDTO,
    CVSSDetailDTO,
    EPSSDetailDTO,
    EvidenceItemDTO,
    FindingAttackPathsResponse,
    FindingEvidenceResponse,
    FindingRemediationResponse,
    ScanOriginDTO,
    VulnerabilityIntelligenceResponse,
    VulnerabilityRiskContextDTO,
)
from app.application.reporting.developer_export_service import (
    DeveloperExportService,
    sanitize_sensitive_data,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.user import UserModel
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_analyst_user() -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "analyst@enterprise.com"
    user.full_name = "Security Analyst"
    user.role = "SECURITY_ANALYST"
    user.is_active = True
    return user


def mock_finding_model() -> MagicMock:
    finding = MagicMock(spec=SecurityFindingModel)
    finding.id = uuid4()
    finding.organization_id = uuid4()
    finding.title = "SQL Injection in Search Form"
    finding.severity = "CRITICAL"
    finding.category = "Injection"
    finding.risk_score = 9.8
    finding.cve_id = "CVE-2024-9999"
    finding.cwe_id = "CWE-89"
    finding.description = "Unsanitized user input passed directly to database."
    finding.status = "CONFIRMED"
    finding.is_duplicate = False
    finding.epss_json = {"epss_score": 0.95}
    finding.created_at = None
    return finding


def test_sanitize_sensitive_data() -> None:
    """Test sensitive auth token and session cookie masking."""
    raw = "GET /api/v1/user HTTP/1.1\nHost: target.internal\nAuthorization: Bearer secret_jwt_token_12345\nCookie: session_id=secret_cookie"
    sanitized = sanitize_sensitive_data(raw)
    assert "secret_jwt_token_12345" not in sanitized
    assert "[REDACTED_AUTH_TOKEN]" in sanitized
    assert "[REDACTED_SESSION_COOKIE]" in sanitized


@pytest.mark.anyio
async def test_developer_export_service_bulk_json(mock_analyst_user: UserModel) -> None:
    """Test DeveloperExportService streaming JSON bulk export."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()

    finding1 = mock_finding_model()
    finding1.organization_id = mock_analyst_user.organization_id

    svc = DeveloperExportService(mock_session, mock_audit)

    with patch.object(svc, "_stream_findings") as mock_stream:

        async def _gen():
            yield finding1

        mock_stream.return_value = _gen()

        chunks = []
        async for chunk in svc.export_json_stream(mock_analyst_user):
            chunks.append(chunk)

        full_json = "".join(chunks)
        assert f'"{finding1.id}"' in full_json
        assert "SQL Injection in Search Form" in full_json
        assert mock_audit.record_event.called


@pytest.mark.anyio
async def test_developer_export_service_bulk_csv(mock_analyst_user: UserModel) -> None:
    """Test DeveloperExportService streaming CSV bulk export."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()

    finding1 = mock_finding_model()
    finding1.organization_id = mock_analyst_user.organization_id

    svc = DeveloperExportService(mock_session, mock_audit)

    with patch.object(svc, "_stream_findings") as mock_stream:

        async def _gen():
            yield finding1

        mock_stream.return_value = _gen()

        chunks = []
        async for chunk in svc.export_csv_stream(mock_analyst_user):
            chunks.append(chunk)

        full_csv = "".join(chunks)
        assert "Finding ID,Title,Severity,Category" in full_csv
        assert "SQL Injection in Search Form" in full_csv
        assert "CVE-2024-9999" in full_csv


@pytest.mark.anyio
async def test_developer_export_service_bulk_markdown(
    mock_analyst_user: UserModel,
) -> None:
    """Test DeveloperExportService streaming Markdown bulk export."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()

    finding1 = mock_finding_model()
    finding1.organization_id = mock_analyst_user.organization_id

    svc = DeveloperExportService(mock_session, mock_audit)

    with patch.object(svc, "_stream_findings") as mock_stream:

        async def _gen():
            yield finding1

        mock_stream.return_value = _gen()

        chunks = []
        async for chunk in svc.export_markdown_stream(mock_analyst_user):
            chunks.append(chunk)

        full_md = "".join(chunks)
        assert "# Vulnova Developer Technical Security Report" in full_md
        assert "### 1. [CRITICAL] SQL Injection in Search Form" in full_md


@pytest.mark.anyio
async def test_developer_export_service_single_finding(
    mock_analyst_user: UserModel,
) -> None:
    """Test single me vulnerability finding technical export in Markdown, JSON, and CSV."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()

    finding_id = uuid4()
    svc = DeveloperExportService(mock_session, mock_audit)

    mock_intel_resp = VulnerabilityIntelligenceResponse(
        id=str(finding_id),
        organization_id=str(mock_analyst_user.organization_id),
        title="SQL Injection in Search Form",
        description="Unsanitized user input passed directly to database query.",
        severity="CRITICAL",
        category="Injection",
        cve_id="CVE-2024-9999",
        cwe_id="CWE-89",
        cvss=CVSSDetailDTO(
            version="3.1",
            base_score=9.8,
            vector_string="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        ),
        epss=EPSSDetailDTO(epss_score=0.95, percentile=0.98),
        risk_context=VulnerabilityRiskContextDTO(
            cvss=CVSSDetailDTO(
                version="3.1",
                base_score=9.8,
                vector_string="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            ),
            epss=EPSSDetailDTO(epss_score=0.95, percentile=0.98),
            risk_level="CRITICAL",
        ),
        scan_origin=ScanOriginDTO(
            job_id=str(uuid4()),
            target_name="api.target.com",
            target_url="https://api.target.com",
        ),
        triage_status="CONFIRMED",
        created_at="2026-08-05T00:00:00Z",
    )

    mock_ev_resp = FindingEvidenceResponse(
        finding_id=str(finding_id),
        evidence_items=[
            EvidenceItemDTO(
                id=str(uuid4()),
                finding_id=str(finding_id),
                artifact_type="HTTP_EXCHANGE",
                type_label="HTTP Request / Response Exchange",
                storage_path="GET /search?q=1' OR 1=1 HTTP/1.1",
                checksum="abc123sha",
                created_at="2026-08-05T00:00:00Z",
            )
        ],
    )

    mock_paths_resp = FindingAttackPathsResponse(
        finding_id=str(finding_id),
        title="Vulnerability Attack Chain",
        attack_summary="Discovered attack progression",
        composite_risk_score=9.8,
        nodes=[
            AttackPathNodeDTO(
                id=str(uuid4()),
                asset_name="Target API Node",
                asset_type="ENDPOINT",
                vulnerability_title="SQL Injection in Search Form",
                relationship="EXPLOITS",
                risk_impact="CRITICAL",
                sequence_number=1,
            )
        ],
    )

    mock_rem_resp = FindingRemediationResponse(
        finding_id=str(finding_id),
        title="Parametrize SQL Query",
        summary="Use ORM parameter binding to neutralize SQL injection.",
        explanation="Raw execute replaced with bound parameter dictionary.",
        steps=[],
        patch_suggestions=[],
    )

    with (
        patch.object(
            svc.intelligence_service,
            "get_finding_details",
            return_value=mock_intel_resp,
        ),
        patch.object(
            svc.intelligence_service, "get_finding_evidence", return_value=mock_ev_resp
        ),
        patch.object(
            svc.intelligence_service,
            "get_finding_attack_paths",
            return_value=mock_paths_resp,
        ),
        patch.object(
            svc.intelligence_service,
            "get_finding_remediation",
            return_value=mock_rem_resp,
        ),
    ):

        # Test Markdown Export
        content_md, media_md, filename_md = await svc.export_single_finding(
            mock_analyst_user, finding_id, "markdown"
        )
        assert media_md == "text/markdown"
        assert (
            "# Vulnerability Technical Report: SQL Injection in Search Form"
            in content_md
        )

        # Test JSON Export
        content_json, media_json, filename_json = await svc.export_single_finding(
            mock_analyst_user, finding_id, "json"
        )
        assert media_json == "application/json"
        assert "SQL Injection in Search Form" in content_json

        # Test CSV Export
        content_csv, media_csv, filename_csv = await svc.export_single_finding(
            mock_analyst_user, finding_id, "csv"
        )
        assert media_csv == "text/csv"
        assert "SQL Injection in Search Form" in content_csv


@pytest.mark.anyio
async def test_developer_export_api_endpoints(mock_analyst_user: UserModel) -> None:
    """Test developer technical export REST API routes with dependency overrides."""
    mock_export_service = AsyncMock(spec=DeveloperExportService)

    async def _mock_gen():
        yield '["test_chunk"]'

    mock_export_service.export_json_stream.return_value = _mock_gen()
    mock_export_service.export_csv_stream.return_value = _mock_gen()
    mock_export_service.export_markdown_stream.return_value = _mock_gen()

    app.dependency_overrides[get_current_user_or_api_key] = lambda: mock_analyst_user
    app.dependency_overrides[get_current_user] = lambda: mock_analyst_user
    app.dependency_overrides[get_developer_export_service] = lambda: mock_export_service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        # GET /api/v1/reports/export/json
        res_json = await ac.get("/api/v1/reports/export/json")
        assert res_json.status_code == 200
        assert res_json.headers["content-type"].startswith("application/json")

        # GET /api/v1/reports/export/csv
        res_csv = await ac.get("/api/v1/reports/export/csv")
        assert res_csv.status_code == 200
        assert res_csv.headers["content-type"].startswith("text/csv")

        # GET /api/v1/reports/export/markdown
        res_md = await ac.get("/api/v1/reports/export/markdown")
        assert res_md.status_code == 200
        assert res_md.headers["content-type"].startswith("text/markdown")

    app.dependency_overrides.clear()
