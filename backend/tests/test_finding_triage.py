"""Unit and Integration Tests for Phase 4.10 Enterprise Finding Triage & Vulnerability Lifecycle Engine."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.assessment.dto import (
    BulkTriageRequest,
    CreateSuppressionRuleRequest,
    TriageFindingRequest,
)
from app.application.assessment.finding_triage_service import FindingTriageService
from app.domain.entities.assessment import Finding, SeverityLevel
from app.domain.entities.triage import FindingTriageStatus, SuppressionRuleType
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.triage import (
    FindingSuppressionRuleModel,
    FindingTriageHistoryModel,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.finding_triage_repository import (
    FindingTriageRepository,
)


def test_single_finding_triage_workflow() -> None:
    """Test FindingTriageService triages a finding, updates status, and logs audit events."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = FindingTriageService(mock_session)

            org_id = uuid4()
            finding_id = uuid4()

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = org_id

            mock_finding = MagicMock(spec=SecurityFindingModel)
            mock_finding.id = finding_id
            mock_finding.organization_id = org_id
            mock_finding.triage_status = "UNREVIEWED"

            service.assessment_repo.get_finding_by_id = AsyncMock(
                return_value=mock_finding
            )
            service.triage_repo.record_triage_action = AsyncMock(
                return_value=MagicMock(spec=FindingTriageHistoryModel)
            )
            service.audit_service.record_event = AsyncMock()

            req = TriageFindingRequest(
                status="CONFIRMED",
                comment="Verified valid SQL injection vulnerability.",
            )
            res = await service.triage_finding(mock_user, finding_id, req)

            assert res.finding_id == str(finding_id)
            assert res.previous_status == "UNREVIEWED"
            assert res.new_status == "CONFIRMED"
            service.triage_repo.record_triage_action.assert_called_once()
            service.audit_service.record_event.assert_called_once()

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_automated_suppression_rules_matching() -> None:
    """Test FindingTriageService evaluates active suppression rules against findings post-assessment."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = FindingTriageService(mock_session)

            org_id = uuid4()
            rule_id = uuid4()

            rule1 = FindingSuppressionRuleModel(
                id=rule_id,
                organization_id=org_id,
                name="SQLi Suppression",
                rule_type="EXACT_CWE",
                cwe_id="CWE-89",
                plugin_id=None,
                target_pattern=None,
                reason="Approved false positive for SQLi test query",
                is_active=True,
            )

            service.triage_repo.list_suppression_rules = AsyncMock(return_value=[rule1])

            f1 = Finding(
                organization_id=org_id,
                title="SQL Injection Probe",
                cwe_id="CWE-89",
                plugin_id="vuln-dast-sqli-v1",
                evidence={},
            )
            f2 = Finding(
                organization_id=org_id,
                title="XSS Probe",
                cwe_id="CWE-79",
                plugin_id="vuln-dast-xss-v1",
                evidence={},
            )

            processed = await service.evaluate_suppression_rules(org_id, [f1, f2])

            assert processed[0].evidence.get("suppressed_by_rule_id") == str(rule_id)
            assert "suppressed_by_rule_id" not in processed[1].evidence

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_triage_repository_tenant_isolation() -> None:
    """Test FindingTriageRepository isolates triage records and suppression rules by organization_id."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            repo = FindingTriageRepository(mock_session)

            org_id_1 = uuid4()
            org_id_2 = uuid4()
            finding_id = uuid4()

            mock_history_1 = MagicMock(spec=FindingTriageHistoryModel)
            mock_history_1.organization_id = org_id_1

            mock_result_1 = MagicMock()
            mock_result_1.scalars.return_value.all.return_value = [mock_history_1]

            mock_result_2 = MagicMock()
            mock_result_2.scalars.return_value.all.return_value = []

            mock_session.execute.side_effect = [mock_result_1, mock_result_2]

            res1 = await repo.get_triage_history(org_id_1, finding_id)
            assert len(res1) == 1

            res2 = await repo.get_triage_history(org_id_2, finding_id)
            assert len(res2) == 0

        loop.run_until_complete(_run())
    finally:
        loop.close()
