"""Tests for Era 11 Phase 11.6 — Security Incident Response & Audit Escalation Lifecycle."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.infrastructure.database.models.audit_log import AuditLogModel
from app.infrastructure.database.models.incident import (
    EscalationEventModel,
    IncidentModel,
    IncidentTimelineModel,
    PostIncidentReviewModel,
)
from app.infrastructure.incident_response.dto import (
    CreateIncidentRequestDTO,
    CreatePIRRequestDTO,
    IncidentSeverity,
    IncidentStatus,
    TriggerEscalationRequestDTO,
    UpdateIncidentStateRequestDTO,
)
from app.infrastructure.incident_response.escalation.email import (
    EmailEscalationProvider,
)
from app.infrastructure.incident_response.escalation.pagerduty import (
    PagerDutyEscalationProvider,
)
from app.infrastructure.incident_response.escalation.slack import (
    SlackEscalationProvider,
)
from app.infrastructure.incident_response.escalation_service import (
    IncidentEscalationService,
)
from app.infrastructure.incident_response.forensics_service import (
    ForensicInvestigationService,
)
from app.infrastructure.incident_response.incident_service import (
    IncidentResponseService,
)
from app.infrastructure.incident_response.post_incident_service import (
    PostIncidentReviewService,
)


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Create a mock SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture()
def org_id() -> UUID:
    return uuid4()


@pytest.fixture()
def user_id() -> UUID:
    return uuid4()


@pytest.fixture()
def sample_incident(org_id: UUID, user_id: UUID) -> IncidentModel:
    now = datetime.now(timezone.utc)
    return IncidentModel(
        id=uuid4(),
        organization_id=org_id,
        title="Unauthorized BOLA Data Access Attempt",
        description="Cross-tenant resource access detected on vulnerability endpoint.",
        severity="SEV-1",
        status="DETECTED",
        lead_investigator_id=user_id,
        affected_services=["api-gateway", "vulnerabilities-service"],
        indicators_of_compromise=["198.51.100.45", "token_hash_abc123"],
        details={"path": "/api/v1/vulnerabilities/123"},
        detected_at=now,
        created_at=now,
        updated_at=now,
        timelines=[],
        escalations=[],
        post_incident_review=None,
    )


class TestIncidentResponseService:
    """Test suite for IncidentResponseService."""

    @pytest.mark.anyio
    async def test_create_incident(
        self, mock_session: AsyncMock, org_id: UUID, user_id: UUID
    ) -> None:
        """Verify incident creation records initial timeline and audit event."""
        service = IncidentResponseService(mock_session)

        req = CreateIncidentRequestDTO(
            title="Active SQL Injection Attack in Staging",
            description="Automated exploit probe targeting search parameters.",
            severity=IncidentSeverity.SEV_2,
            affected_services=["frontend", "database"],
            indicators_of_compromise=["203.0.113.19"],
            details={"vector": "UNION SELECT"},
        )

        res = await service.create_incident(
            organization_id=org_id,
            request=req,
            actor_id=user_id,
            client_ip="10.0.0.1",
        )

        assert res.title == req.title
        assert res.severity == "SEV-2"
        assert res.status == "DETECTED"
        assert res.organization_id == org_id
        assert len(res.timelines) == 1
        assert res.timelines[0].phase == "DETECTION"
        assert mock_session.add.call_count >= 2  # Incident + Timeline

    @pytest.mark.anyio
    async def test_update_incident_state_and_containment(
        self,
        mock_session: AsyncMock,
        org_id: UUID,
        user_id: UUID,
        sample_incident: IncidentModel,
    ) -> None:
        """Verify lifecycle state progression updates containment and resolution timestamps."""
        service = IncidentResponseService(mock_session)
        service.repo.get_incident_by_id_and_org = AsyncMock(return_value=sample_incident)  # type: ignore[assignment]
        service.repo.list_timeline_events = AsyncMock(return_value=[])  # type: ignore[assignment]

        # 1. Transition to CONTAINED
        update_req = UpdateIncidentStateRequestDTO(
            status=IncidentStatus.CONTAINED,
            note="Compromised session invalidated and offending IP blacklisted.",
        )

        res = await service.update_incident_state(
            incident_id=sample_incident.id,
            organization_id=org_id,
            request=update_req,
            actor_id=user_id,
        )

        assert res.status == "CONTAINED"
        assert sample_incident.contained_at is not None

        # 2. Transition to CLOSED
        close_req = UpdateIncidentStateRequestDTO(
            status=IncidentStatus.CLOSED,
            note="Remediation verified; emergency patch live.",
        )
        res_closed = await service.update_incident_state(
            incident_id=sample_incident.id,
            organization_id=org_id,
            request=close_req,
            actor_id=user_id,
        )
        assert res_closed.status == "CLOSED"
        assert sample_incident.closed_at is not None
        assert sample_incident.resolved_at is not None

    @pytest.mark.anyio
    async def test_duration_metrics_calculation(
        self, org_id: UUID, user_id: UUID, sample_incident: IncidentModel
    ) -> None:
        """Verify MTTA, MTTC, and MTTR calculation."""
        service = IncidentResponseService(AsyncMock())
        now = datetime.now(timezone.utc)
        sample_incident.contained_at = now
        sample_incident.resolved_at = now

        timelines = [
            IncidentTimelineModel(
                id=uuid4(),
                incident_id=sample_incident.id,
                phase="TRIAGE",
                action="incident.triaged",
                description="Triage complete",
                timestamp=now,
            )
        ]

        metrics = service.calculate_response_durations(sample_incident, timelines)
        assert metrics.mtta_minutes is not None
        assert metrics.mttc_minutes is not None
        assert metrics.mttr_minutes is not None
        assert metrics.sla_met is True

    @pytest.mark.anyio
    async def test_status_summary_aggregation(
        self, mock_session: AsyncMock, org_id: UUID, sample_incident: IncidentModel
    ) -> None:
        """Verify status summary calculates severity breakdown."""
        service = IncidentResponseService(mock_session)
        service.repo.list_incidents_by_org = AsyncMock(return_value=([sample_incident], 1))  # type: ignore[assignment]

        summary = await service.get_status_summary(org_id)
        assert summary.total_active_incidents == 1
        assert summary.sev1_critical_count == 1
        assert summary.status == "CRITICAL"


class TestIncidentEscalationService:
    """Test suite for IncidentEscalationService & Notification Providers."""

    def test_escalation_rules_evaluation(self, mock_session: AsyncMock) -> None:
        """Verify severity to channel mapping."""
        service = IncidentEscalationService(mock_session)
        assert service.evaluate_escalation_rules("SEV-1") == [
            "pagerduty",
            "slack",
            "email",
        ]
        assert service.evaluate_escalation_rules("SEV-2") == [
            "pagerduty",
            "slack",
            "email",
        ]
        assert service.evaluate_escalation_rules("SEV-3") == ["slack", "email"]
        assert service.evaluate_escalation_rules("SEV-4") == ["slack"]

    @pytest.mark.anyio
    async def test_pagerduty_provider_dispatch(self) -> None:
        """Verify PagerDuty provider formats and returns trigger payload."""
        provider = PagerDutyEscalationProvider()
        res = await provider.send_notification(
            incident_id=str(uuid4()),
            title="Database Connection Pool Exhaustion",
            severity="SEV-1",
            description="High connection wait latency detected.",
            details={"pool_size": 20},
        )
        assert res["status"] == "DELIVERED"
        assert res["channel"] == "pagerduty"
        assert res["pagerduty_severity"] == "critical"

    @pytest.mark.anyio
    async def test_slack_provider_dispatch(self) -> None:
        """Verify Slack provider generates Block Kit alert card."""
        provider = SlackEscalationProvider()
        res = await provider.send_notification(
            incident_id=str(uuid4()),
            title="Anomalous JWT Token Revocation Spike",
            severity="SEV-2",
            description="50+ tokens revoked in 60 seconds.",
            details={"org_id": "test"},
        )
        assert res["status"] == "DELIVERED"
        assert res["channel"] == "slack"
        assert res["blocks_count"] >= 3

    @pytest.mark.anyio
    async def test_email_provider_dispatch(self) -> None:
        """Verify Email provider formats security notification."""
        provider = EmailEscalationProvider()
        res = await provider.send_notification(
            incident_id=str(uuid4()),
            title="Security Audit Log Pipeline Delay",
            severity="SEV-3",
            description="Worker queue lag 120s.",
            details={},
        )
        assert res["status"] == "DELIVERED"
        assert res["channel"] == "email"
        assert "Incident Alert" in res["subject"]

    @pytest.mark.anyio
    async def test_trigger_escalation_workflow(
        self,
        mock_session: AsyncMock,
        org_id: UUID,
        user_id: UUID,
        sample_incident: IncidentModel,
    ) -> None:
        """Verify escalation service orchestrates multi-channel notifications and logs events."""
        service = IncidentEscalationService(mock_session)
        service.repo.get_incident_by_id_and_org = AsyncMock(return_value=sample_incident)  # type: ignore[assignment]

        req = TriggerEscalationRequestDTO(
            channels=["pagerduty", "slack"],
            reason="Confirmed remote code execution vulnerability in worker sandbox.",
            details={"sandbox_id": "sbx-99"},
        )

        res = await service.trigger_escalation(
            incident_id=sample_incident.id,
            organization_id=org_id,
            request=req,
            actor_id=user_id,
        )

        assert res.status == "DELIVERED"
        assert "pagerduty" in res.channels
        assert "slack" in res.channels
        assert mock_session.add.call_count >= 2  # Escalation event + timeline


class TestForensicInvestigationService:
    """Test suite for ForensicInvestigationService."""

    @pytest.mark.anyio
    async def test_correlate_suspicious_activities(
        self, mock_session: AsyncMock, org_id: UUID, user_id: UUID
    ) -> None:
        """Verify suspicious audit events are clustered by threat category."""
        service = ForensicInvestigationService(mock_session)
        now = datetime.now(timezone.utc)

        mock_logs = [
            AuditLogModel(
                id=uuid4(),
                organization_id=org_id,
                actor_user_id=user_id,
                action="auth.login_failed",
                resource_type="auth",
                client_ip="198.51.100.1",
                details={},
                created_at=now,
            ),
            AuditLogModel(
                id=uuid4(),
                organization_id=org_id,
                actor_user_id=user_id,
                action="user.role_escalated",
                resource_type="user",
                client_ip="198.51.100.1",
                details={},
                created_at=now,
            ),
            AuditLogModel(
                id=uuid4(),
                organization_id=org_id,
                actor_user_id=user_id,
                action="vulnerability.exported",
                resource_type="report",
                client_ip="198.51.100.1",
                details={},
                created_at=now,
            ),
        ]
        service.query_security_audit_events = AsyncMock(return_value=mock_logs)  # type: ignore[assignment]

        clusters = await service.correlate_suspicious_activities(organization_id=org_id)
        assert len(clusters) >= 3
        keys = [c.correlation_key for c in clusters]
        assert "AUTH_ANOMALIES" in keys
        assert "PRIVILEGE_ESCALATION" in keys
        assert "DATA_EXFILTRATION_RISK" in keys

    @pytest.mark.anyio
    async def test_preserve_investigation_timeline_sha256(
        self,
        mock_session: AsyncMock,
        org_id: UUID,
        sample_incident: IncidentModel,
    ) -> None:
        """Verify forensic timeline package generates a reproducible SHA-256 integrity digest."""
        service = ForensicInvestigationService(mock_session)
        service.repo.get_incident_by_id_and_org = AsyncMock(return_value=sample_incident)  # type: ignore[assignment]
        service.correlate_suspicious_activities = AsyncMock(return_value=[])  # type: ignore[assignment]

        result = await service.preserve_investigation_timeline(
            incident_id=sample_incident.id,
            organization_id=org_id,
        )

        assert result.incident_id == sample_incident.id
        assert len(result.forensic_integrity_sha256) == 64
        assert "Forensic investigation package" in result.summary


class TestPostIncidentReviewService:
    """Test suite for PostIncidentReviewService."""

    @pytest.mark.anyio
    async def test_create_pir_and_generate_report(
        self,
        mock_session: AsyncMock,
        org_id: UUID,
        user_id: UUID,
        sample_incident: IncidentModel,
    ) -> None:
        """Verify PIR creation, timeline update, and markdown report generation."""
        service = PostIncidentReviewService(mock_session)
        service.repo.get_incident_by_id_and_org = AsyncMock(return_value=sample_incident)  # type: ignore[assignment]

        pir_req = CreatePIRRequestDTO(
            summary="Tenant authorization bypass mitigated via middleware filter.",
            root_cause="Missing path parameter validation in legacy router.",
            impact_assessment="Single tenant finding metadata exposed; no secret keys leaked.",
            timeline_summary="Detection (14:00) -> Containment (14:15) -> Patch (15:00)",
            lessons_learned=[
                "Enforce automated BOLA validation tests in CI/CD pipeline",
                "Enhance rate limit telemetry on private endpoints",
            ],
            action_items=[
                {
                    "title": "Add AST lint check for tenant parameter",
                    "owner": "Backend Lead",
                    "due_date": "2026-08-20",
                    "status": "OPEN",
                }
            ],
        )

        pir_dto = await service.create_or_update_pir(
            incident_id=sample_incident.id,
            organization_id=org_id,
            request=pir_req,
            author_id=user_id,
        )

        assert pir_dto.incident_id == sample_incident.id
        assert len(pir_dto.lessons_learned) == 2
        assert len(pir_dto.action_items) == 1

        # Generate Lessons Learned Report
        sample_incident.post_incident_review = PostIncidentReviewModel(
            id=uuid4(),
            incident_id=sample_incident.id,
            author_id=user_id,
            summary=pir_req.summary,
            root_cause=pir_req.root_cause,
            impact_assessment=pir_req.impact_assessment,
            timeline_summary=pir_req.timeline_summary,
            lessons_learned=pir_req.lessons_learned,
            action_items=pir_req.action_items,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        report = await service.generate_lessons_learned_report(
            incident_id=sample_incident.id,
            organization_id=org_id,
        )

        assert report["incident_id"] == str(sample_incident.id)
        assert "# Post-Incident Review Report" in report["markdown_report"]
        assert "## 2. Root Cause Analysis" in report["markdown_report"]
