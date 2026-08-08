"""Unit and Integration Tests for Enterprise Security Audit & Penetration Testing Framework (Phase 12.1)."""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.domain.entities.role import Role, role_has_permission
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.security_audit.analyzers.api_analyzer import (
    APISecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.auth_analyzer import (
    AuthenticationSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.config_analyzer import (
    ConfigurationSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.container_analyzer import (
    ContainerSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.dependency_analyzer import (
    DependencySecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.rbac_analyzer import (
    AuthorizationRBACAnalyzer,
)
from app.infrastructure.security_audit.analyzers.sast_analyzer import (
    SASTSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.secret_analyzer import (
    SecretExposureAnalyzer,
)
from app.infrastructure.security_audit.audit_service import SecurityAuditService
from app.infrastructure.security_audit.dto import (
    AuditCategory,
    AuditFindingStatus,
    AuditSeverity,
    RemediateFindingRequestDTO,
    RunSecurityAuditRequestDTO,
    SecurityAuditExecutionDTO,
    SecurityAuditStatusDTO,
)


@pytest.fixture
def org_id() -> UUID:
    return uuid4()


@pytest.fixture
def actor_id() -> UUID:
    return uuid4()


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def admin_user(org_id: UUID, actor_id: UUID) -> UserModel:
    return UserModel(
        id=actor_id,
        email="security.lead@vulnova.enterprise",
        full_name="Security Lead",
        organization_id=org_id,
        role=Role.ADMIN,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestSecurityAnalyzers:
    """Verify all 8 domain security analyzers execute and produce valid findings."""

    def test_sast_analyzer_execution(self) -> None:
        analyzer = SASTSecurityAnalyzer()
        findings = analyzer.run_analysis()
        assert len(findings) >= 4
        assert analyzer.category_name == AuditCategory.SAST.value
        assert any(f.cwe_id == "CWE-89" for f in findings)
        assert all(f.remediation_status == "REMEDIATED" for f in findings)

    def test_dependency_analyzer_execution(self) -> None:
        analyzer = DependencySecurityAnalyzer()
        findings = analyzer.run_analysis()
        assert len(findings) >= 3
        assert analyzer.category_name == AuditCategory.SCA.value
        assert any(f.cwe_id == "CWE-1104" for f in findings)

    def test_configuration_analyzer_execution(self) -> None:
        analyzer = ConfigurationSecurityAnalyzer()
        findings = analyzer.run_analysis()
        assert len(findings) >= 4
        assert analyzer.category_name == AuditCategory.CONFIGURATION.value
        assert any(f.cwe_id == "CWE-1021" for f in findings)
        assert any(f.cwe_id == "CWE-209" for f in findings)

    def test_api_security_analyzer_execution(self) -> None:
        analyzer = APISecurityAnalyzer()
        findings = analyzer.run_analysis()
        assert len(findings) >= 4
        assert analyzer.category_name == AuditCategory.API_SECURITY.value
        assert any(f.cwe_id == "CWE-639" for f in findings)

    def test_auth_security_analyzer_execution(self) -> None:
        analyzer = AuthenticationSecurityAnalyzer()
        findings = analyzer.run_analysis()
        assert len(findings) >= 4
        assert analyzer.category_name == AuditCategory.AUTHENTICATION.value
        assert any(f.cwe_id == "CWE-916" for f in findings)

    def test_rbac_security_analyzer_execution(self) -> None:
        analyzer = AuthorizationRBACAnalyzer()
        findings = analyzer.run_analysis()
        assert len(findings) >= 3
        assert analyzer.category_name == AuditCategory.AUTHORIZATION_RBAC.value
        assert any(f.cwe_id == "CWE-269" for f in findings)

    def test_secret_exposure_analyzer_execution(self) -> None:
        analyzer = SecretExposureAnalyzer()
        findings = analyzer.run_analysis()
        assert len(findings) >= 3
        assert analyzer.category_name == AuditCategory.SECRET_DETECTION.value
        assert any(f.cwe_id == "CWE-798" for f in findings)

    def test_container_security_analyzer_execution(self) -> None:
        analyzer = ContainerSecurityAnalyzer()
        findings = analyzer.run_analysis()
        assert len(findings) >= 3
        assert analyzer.category_name == AuditCategory.CONTAINER_SECURITY.value
        assert any(f.cwe_id == "CWE-250" for f in findings)


class TestSecurityAuditService:
    """Verify orchestration, scoring, integrity hashing, and remediation workflows."""

    @pytest.mark.anyio
    async def test_full_security_audit_execution(
        self, mock_session: AsyncMock, org_id: UUID, actor_id: UUID
    ) -> None:
        service = SecurityAuditService(mock_session)
        result: SecurityAuditExecutionDTO = await service.execute_security_audit(
            organization_id=org_id,
            actor_user_id=actor_id,
            request=RunSecurityAuditRequestDTO(include_dynamic_checks=True),
        )

        assert result.organization_id == org_id
        assert result.total_findings >= 20
        assert len(result.categories_analyzed) == 8
        assert result.status in ("PASSED", "DEGRADED", "CRITICAL")
        assert result.overall_security_score >= 80.0
        assert len(result.audit_integrity_sha256) == 64

    @pytest.mark.anyio
    async def test_category_filtered_audit_execution(
        self, mock_session: AsyncMock, org_id: UUID
    ) -> None:
        service = SecurityAuditService(mock_session)
        request = RunSecurityAuditRequestDTO(
            categories=[AuditCategory.SAST.value, AuditCategory.API_SECURITY.value]
        )
        result = await service.execute_security_audit(
            organization_id=org_id, request=request
        )

        assert len(result.categories_analyzed) == 2
        assert AuditCategory.SAST.value in result.categories_analyzed
        assert AuditCategory.API_SECURITY.value in result.categories_analyzed

    @pytest.mark.anyio
    async def test_audit_status_retrieval(
        self, mock_session: AsyncMock, org_id: UUID
    ) -> None:
        service = SecurityAuditService(mock_session)
        status: SecurityAuditStatusDTO = await service.get_audit_status(org_id)

        assert status.total_vulnerabilities_tracked >= 20
        assert status.remediation_rate_percentage > 0.0
        assert status.compliance_grade in ("A+", "A", "B", "C")

    @pytest.mark.anyio
    async def test_list_findings_with_pagination_and_filters(
        self, mock_session: AsyncMock, org_id: UUID
    ) -> None:
        service = SecurityAuditService(mock_session)
        findings, total = await service.list_findings(
            organization_id=org_id,
            category=AuditCategory.SAST.value,
            limit=2,
            offset=0,
        )

        assert len(findings) <= 2
        assert total >= 4
        assert all(f.category == AuditCategory.SAST.value for f in findings)

    @pytest.mark.anyio
    async def test_remediate_finding_workflow(
        self, mock_session: AsyncMock, org_id: UUID, actor_id: UUID
    ) -> None:
        service = SecurityAuditService(mock_session)
        exec_res = await service.execute_security_audit(organization_id=org_id)
        target = exec_res.findings[0]

        remediated = await service.remediate_finding(
            organization_id=org_id,
            finding_id=target.finding_id,
            request=RemediateFindingRequestDTO(
                status=AuditFindingStatus.ACCEPTED_RISK,
                remediation_notes="Mitigated via edge WAF rate-limiting rule.",
                remediated_by="Lead Security Architect",
            ),
            actor_user_id=actor_id,
        )

        assert remediated.remediation_status == AuditFindingStatus.ACCEPTED_RISK.value
        assert (
            remediated.remediation_notes == "Mitigated via edge WAF rate-limiting rule."
        )
        assert remediated.remediated_by == "Lead Security Architect"
        assert remediated.remediated_at is not None

    @pytest.mark.anyio
    async def test_remediate_finding_not_found(
        self, mock_session: AsyncMock, org_id: UUID
    ) -> None:
        service = SecurityAuditService(mock_session)
        await service.execute_security_audit(organization_id=org_id)

        with pytest.raises(
            ValueError, match="Security audit finding INVALID-999 not found"
        ):
            await service.remediate_finding(
                organization_id=org_id,
                finding_id="INVALID-999",
                request=RemediateFindingRequestDTO(
                    status=AuditFindingStatus.REMEDIATED,
                    remediation_notes="Fixed.",
                ),
            )


class TestSecurityAuditRBAC:
    """Verify RBAC permission mappings for security audit endpoints."""

    def test_rbac_security_audit_permissions(self) -> None:
        assert role_has_permission(Role.ADMIN, "security_audit:manage") is True
        assert role_has_permission(Role.OWNER, "security_audit:manage") is True
        assert (
            role_has_permission(Role.SECURITY_ANALYST, "security_audit:manage") is False
        )
        assert role_has_permission(Role.VIEWER, "security_audit:manage") is False

        assert (
            role_has_permission(Role.SECURITY_ANALYST, "security_audit:execute") is True
        )
        assert role_has_permission(Role.VIEWER, "security_audit:execute") is False

        assert role_has_permission(Role.VIEWER, "security_audit:read") is True
