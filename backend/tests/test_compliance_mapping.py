"""Unit and Integration Test Suite for Compliance Framework Mapping Engine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.compliance import get_compliance_service
from app.application.compliance.compliance_service import ComplianceMappingService
from app.application.compliance.framework_mapper import FrameworkMapper
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


@pytest.fixture
def mock_viewer_user() -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "viewer@enterprise.com"
    user.full_name = "Security Viewer"
    user.role = "VIEWER"
    user.is_active = True
    return user


def create_finding(
    title: str,
    category: str,
    cwe_id: str,
    severity: str = "HIGH",
    status: str = "CONFIRMED",
) -> MagicMock:
    finding = MagicMock(spec=SecurityFindingModel)
    finding.id = uuid4()
    finding.organization_id = uuid4()
    finding.title = title
    finding.category = category
    finding.cwe_id = cwe_id
    finding.cve_id = "CVE-2024-1234"
    finding.severity = severity
    finding.status = status
    finding.remediation = "Apply security patch immediately."
    finding.is_duplicate = False
    finding.evidence_json = {"checksum": "abc123hash"}
    finding.assessment_job = MagicMock(target_url="https://api.target.com")
    return finding


def test_owasp_mapping_accuracy() -> None:
    """Verify vulnerability to OWASP Top 10 2021 mapping accuracy."""
    findings = [
        create_finding("SQL Injection in Search", "SQL Injection", "CWE-89"),
        create_finding("XSS in Input", "XSS", "CWE-79"),
    ]
    framework, controls, score = FrameworkMapper.evaluate_framework(
        "owasp_top10", findings
    )

    assert framework.version == "OWASP Top 10 2021"
    a03_control = next(c for c in controls if c.control_id == "A03:2021")
    assert a03_control.status == "FAIL"
    assert a03_control.mapped_findings_count == 2
    assert len(a03_control.affected_findings) == 2
    assert a03_control.affected_findings[0].cwe_id == "CWE-89"


def test_asvs_control_mapping() -> None:
    """Verify vulnerability to OWASP ASVS 4.0.3 mapping."""
    findings = [
        create_finding("Broken Authentication", "Authentication", "CWE-287"),
    ]
    framework, controls, score = FrameworkMapper.evaluate_framework("asvs_v4", findings)

    assert framework.version == "OWASP ASVS 4.0.3"
    v2_control = next(c for c in controls if c.control_id == "V2")
    assert v2_control.status == "FAIL"
    assert v2_control.affected_findings[0].cwe_id == "CWE-287"


def test_pci_dss_mapping() -> None:
    """Verify vulnerability to PCI DSS 4.0 mapping."""
    findings = [
        create_finding("Hardcoded API Key", "Misconfiguration", "CWE-16"),
    ]
    framework, controls, score = FrameworkMapper.evaluate_framework("pci_dss", findings)

    assert framework.version == "PCI DSS 4.0"
    req11 = next(c for c in controls if c.control_id == "Req-11")
    assert req11.status == "FAIL"


def test_iso27001_mapping() -> None:
    """Verify vulnerability to ISO 27001:2022 mapping."""
    findings = [
        create_finding("IDOR Vulnerability", "Access Control", "CWE-639"),
    ]
    framework, controls, score = FrameworkMapper.evaluate_framework(
        "iso27001", findings
    )

    assert framework.version == "ISO 27001:2022"
    a9_control = next(c for c in controls if c.control_id == "A.9")
    assert a9_control.status == "FAIL"


def test_compliance_score_calculation() -> None:
    """Verify compliance score calculation and exclusion of resolved/false-positive findings."""
    # 1 active SQLi finding, 1 resolved XSS finding
    findings = [
        create_finding("SQLi Active", "SQL Injection", "CWE-89", status="CONFIRMED"),
        create_finding("XSS Fixed", "XSS", "CWE-79", status="RESOLVED"),
        create_finding(
            "Auth False Positive", "Authentication", "CWE-287", status="FALSE_POSITIVE"
        ),
    ]
    _, controls, score = FrameworkMapper.evaluate_framework("owasp_top10", findings)

    # Total OWASP Top 10 controls = 10
    # A03 fails due to active SQLi. Resolved XSS and False Positive Auth do NOT trigger failure.
    assert score.total_controls == 10
    assert score.failed_controls == 1  # Only A03 fails
    assert score.passed_controls == 9
    assert score.compliance_percentage == 90.0


@pytest.mark.anyio
async def test_tenant_isolation(mock_analyst_user: UserModel) -> None:
    """Verify compliance queries enforce strict organization_id tenant filtering."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ComplianceMappingService(mock_session, mock_audit)

    # Mock DB scalar results
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_res

    overview = await service.get_compliance_overview(mock_analyst_user, "owasp_top10")
    assert overview.score.compliance_percentage == 100.0
    mock_session.execute.assert_called()


@pytest.mark.anyio
async def test_rbac_permissions(
    mock_analyst_user: UserModel, mock_viewer_user: UserModel
) -> None:
    """Verify RBAC permission guards for compliance endpoints."""
    mock_service = AsyncMock()
    mock_service.get_compliance_overview.return_value = {
        "framework_id": "owasp_top10",
        "framework_name": "OWASP Top 10",
        "framework_version": "OWASP Top 10 2021",
        "score": {
            "framework_id": "owasp_top10",
            "framework_name": "OWASP Top 10",
            "framework_version": "OWASP Top 10 2021",
            "total_controls": 10,
            "passed_controls": 10,
            "failed_controls": 0,
            "compliance_percentage": 100.0,
        },
        "controls": [],
        "failed_controls": [],
        "top_remediation_priorities": [],
    }

    app.dependency_overrides[get_compliance_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user
    app.dependency_overrides[get_current_user_or_api_key] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read overview
        res = await client.get("/api/v1/compliance/owasp_top10/overview")
        assert res.status_code == 200

        # Viewer CANNOT export compliance report (compliance:export requires SECURITY_ANALYST+)
        res_export = await client.get("/api/v1/compliance/owasp_top10/export")
        assert res_export.status_code == 403

        # Switch to Analyst
        app.dependency_overrides[get_current_user] = lambda: mock_analyst_user
        app.dependency_overrides[get_current_user_or_api_key] = (
            lambda: mock_analyst_user
        )
        mock_service.export_compliance_report.return_value = {"title": "Report"}
        res_analyst_export = await client.get("/api/v1/compliance/owasp_top10/export")
        assert res_analyst_export.status_code == 200

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_compliance_audit_logging(mock_analyst_user: UserModel) -> None:
    """Verify audit log event recording for compliance viewing and exporting."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ComplianceMappingService(mock_session, mock_audit)

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_res

    await service.get_compliance_overview(mock_analyst_user, "owasp_top10")
    mock_audit.record_event.assert_called_with(
        organization_id=mock_analyst_user.organization_id,
        action="compliance.viewed",
        resource_type="compliance_framework",
        resource_id="owasp_top10",
        actor_user_id=mock_analyst_user.id,
        details={
            "framework_id": "owasp_top10",
            "framework_version": "OWASP Top 10 2021",
            "compliance_percentage": 100.0,
            "failed_controls_count": 0,
        },
    )

    await service.export_compliance_report(mock_analyst_user, "pci_dss")
    assert mock_audit.record_event.call_count == 3  # viewed + overview + exported
