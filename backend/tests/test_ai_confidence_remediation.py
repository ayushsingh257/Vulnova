"""Unit and Integration Tests for Phase 12.6 AI Finding Confidence Scoring & Human-in-the-Loop Remediation Workflow."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.ai_confidence.confidence_service import (
    FindingConfidenceService,
)
from app.infrastructure.ai_confidence.dto import (
    ConfidenceLevel,
    RemediationStatus,
    ReviewDecision,
    VerificationStatus,
)
from app.infrastructure.ai_confidence.remediation_governance_service import (
    RemediationGovernanceService,
)
from app.infrastructure.ai_confidence.review_service import FindingReviewService
from app.infrastructure.database.models.ai_confidence import (
    FindingVerificationAttemptModel,
)
from app.infrastructure.database.models.ai_remediation import AIRemediationPlanModel
from app.infrastructure.database.models.assessment import SecurityFindingModel


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


def _make_finding(
    finding_id: Any = None,
    org_id: Any = None,
    plugin_id: str = "sql_injection_plugin",
    title: str = "SQL Injection in /api/login",
    severity: str = "CRITICAL",
    raw_evidence: str = "HTTP/1.1 200 OK\nORA-00933: SQL command not properly ended",
    proof_of_concept: str = "POST /api/login HTTP/1.1\n' OR 1=1--",
    status: str = "OPEN",
) -> SecurityFindingModel:
    fid = finding_id or uuid4()
    oid = org_id or uuid4()
    m = SecurityFindingModel()
    m.id = fid
    m.organization_id = oid
    m.plugin_id = plugin_id
    m.title = title
    m.severity = severity
    m.raw_evidence = raw_evidence
    m.proof_of_concept = proof_of_concept
    m.status = status
    m.scan_target_id = uuid4()
    return m


# ─── Confidence Calculation Tests ───


@pytest.mark.anyio
async def test_confidence_high_evidence_high_reliability(
    mock_session: AsyncMock,
) -> None:
    """High-evidence SQL injection finding from high-reliability plugin scores HIGH+."""
    org_id = uuid4()
    finding_id = uuid4()
    finding = _make_finding(finding_id=finding_id, org_id=org_id)

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "security_findings" in stmt_str:
            res.scalar_one_or_none.return_value = finding
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    svc = FindingConfidenceService(mock_session)
    result = await svc.calculate_confidence(finding_id, org_id)

    assert result.finding_id == finding_id
    assert result.confidence_score >= 70.0
    assert result.confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.CONFIRMED)
    assert result.evidence_quality_score > 50.0
    assert result.explanation != ""


@pytest.mark.anyio
async def test_confidence_low_evidence_low_reliability(mock_session: AsyncMock) -> None:
    """Low-evidence finding from unknown plugin scores LOW/MEDIUM."""
    org_id = uuid4()
    finding_id = uuid4()
    finding = _make_finding(
        finding_id=finding_id,
        org_id=org_id,
        plugin_id="unknown_custom_plugin",
        raw_evidence="minimal",
        proof_of_concept="",
    )

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "security_findings" in stmt_str:
            res.scalar_one_or_none.return_value = finding
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    svc = FindingConfidenceService(mock_session)
    result = await svc.calculate_confidence(finding_id, org_id)

    assert result.confidence_score < 85.0
    assert result.confidence_level in (ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM)


@pytest.mark.anyio
async def test_confidence_with_reproduced_verification(mock_session: AsyncMock) -> None:
    """Reproduced verification boosts confidence to CONFIRMED."""
    org_id = uuid4()
    finding_id = uuid4()
    finding = _make_finding(finding_id=finding_id, org_id=org_id)

    verification = FindingVerificationAttemptModel()
    verification.id = uuid4()
    verification.finding_id = finding_id
    verification.organization_id = org_id
    verification.verification_status = "CONFIRMED"
    verification.is_reproduced = True
    verification.created_at = datetime.now(timezone.utc)

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "security_findings" in stmt_str:
            res.scalar_one_or_none.return_value = finding
        elif "finding_verification_attempts" in stmt_str:
            res.scalar_one_or_none.return_value = verification
        elif "ai_finding_confidence_analyses" in stmt_str:
            res.scalar_one_or_none.return_value = None
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    svc = FindingConfidenceService(mock_session)
    result = await svc.calculate_confidence(finding_id, org_id)

    assert result.reproduction_score >= 90.0
    assert result.verification_status == VerificationStatus.CONFIRMED


# ─── Human Review Tests ───


@pytest.mark.anyio
async def test_analyst_confirm_finding(mock_session: AsyncMock) -> None:
    """Analyst CONFIRM decision updates finding status to CONFIRMED."""
    org_id = uuid4()
    finding_id = uuid4()
    reviewer_id = uuid4()
    finding = _make_finding(finding_id=finding_id, org_id=org_id)

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = finding
        return res

    mock_session.execute.side_effect = _mock_exec

    svc = FindingReviewService(mock_session)
    svc.audit_service.record_event = AsyncMock()

    result = await svc.submit_review(
        finding_id=finding_id,
        organization_id=org_id,
        reviewer_id=reviewer_id,
        decision=ReviewDecision.CONFIRM,
        comments="Verified via manual testing",
    )

    assert result.decision == ReviewDecision.CONFIRM
    assert result.finding_id == finding_id
    assert result.reviewer_id == reviewer_id
    assert finding.status == "CONFIRMED"


@pytest.mark.anyio
async def test_analyst_false_positive_finding(mock_session: AsyncMock) -> None:
    """Analyst FALSE_POSITIVE decision updates finding status."""
    org_id = uuid4()
    finding_id = uuid4()
    reviewer_id = uuid4()
    finding = _make_finding(finding_id=finding_id, org_id=org_id)

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = finding
        return res

    mock_session.execute.side_effect = _mock_exec

    svc = FindingReviewService(mock_session)
    svc.audit_service.record_event = AsyncMock()

    result = await svc.submit_review(
        finding_id=finding_id,
        organization_id=org_id,
        reviewer_id=reviewer_id,
        decision=ReviewDecision.FALSE_POSITIVE,
        comments="Scanner misconfiguration",
    )

    assert result.decision == ReviewDecision.FALSE_POSITIVE
    assert finding.status == "FALSE_POSITIVE"


@pytest.mark.anyio
async def test_analyst_accept_risk_finding(mock_session: AsyncMock) -> None:
    """Analyst ACCEPT_RISK decision updates finding status to RISK_ACCEPTED."""
    org_id = uuid4()
    finding_id = uuid4()
    reviewer_id = uuid4()
    finding = _make_finding(finding_id=finding_id, org_id=org_id)

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = finding
        return res

    mock_session.execute.side_effect = _mock_exec

    svc = FindingReviewService(mock_session)
    svc.audit_service.record_event = AsyncMock()

    result = await svc.submit_review(
        finding_id=finding_id,
        organization_id=org_id,
        reviewer_id=reviewer_id,
        decision=ReviewDecision.ACCEPT_RISK,
        comments="Accepted for legacy system",
    )

    assert result.decision == ReviewDecision.ACCEPT_RISK
    assert finding.status == "RISK_ACCEPTED"


# ─── Remediation Governance Tests ───


@pytest.mark.anyio
async def test_remediation_approval_workflow(mock_session: AsyncMock) -> None:
    """Remediation plan approved by analyst transitions to APPROVED_FOR_IMPLEMENTATION."""
    org_id = uuid4()
    plan_id = uuid4()
    finding_id = uuid4()
    approver_id = uuid4()

    plan = AIRemediationPlanModel()
    plan.id = plan_id
    plan.organization_id = org_id
    plan.finding_id = finding_id
    plan.root_finding_id = finding_id
    plan.status = "AI_RECOMMENDED"

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = plan
        return res

    mock_session.execute.side_effect = _mock_exec

    svc = RemediationGovernanceService(mock_session)
    svc.audit_service.record_event = AsyncMock()

    result = await svc.approve_remediation(
        remediation_plan_id=plan_id,
        organization_id=org_id,
        approver_user_id=approver_id,
        notes="Approved during maintenance window",
    )

    assert result.new_state == RemediationStatus.APPROVED_FOR_IMPLEMENTATION
    assert result.previous_state == "AI_RECOMMENDED"
    assert result.action_by == approver_id
    assert plan.status == "APPROVED_FOR_IMPLEMENTATION"


@pytest.mark.anyio
async def test_remediation_rejection_workflow(mock_session: AsyncMock) -> None:
    """Remediation plan rejected transitions to REJECTED."""
    org_id = uuid4()
    plan_id = uuid4()
    finding_id = uuid4()
    approver_id = uuid4()

    plan = AIRemediationPlanModel()
    plan.id = plan_id
    plan.organization_id = org_id
    plan.finding_id = finding_id
    plan.root_finding_id = finding_id
    plan.status = "AI_RECOMMENDED"

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = plan
        return res

    mock_session.execute.side_effect = _mock_exec

    svc = RemediationGovernanceService(mock_session)
    svc.audit_service.record_event = AsyncMock()

    result = await svc.reject_remediation(
        remediation_plan_id=plan_id,
        organization_id=org_id,
        approver_user_id=approver_id,
        notes="Patch not compatible with production runtime",
    )

    assert result.new_state == RemediationStatus.REJECTED
    assert plan.status == "REJECTED"


@pytest.mark.anyio
async def test_remediation_execution_blocked_without_approval() -> None:
    """Validate that remediation execution is blocked without human approval."""
    plan = AIRemediationPlanModel()
    plan.id = uuid4()
    plan.status = "AI_RECOMMENDED"

    mock_session = AsyncMock()
    svc = RemediationGovernanceService(mock_session)

    from app.core.exceptions import ValidationException

    with pytest.raises(ValidationException, match="Human analyst approval"):
        svc.validate_execution_allowed(plan)


# ─── Full Integration Flow Test ───


@pytest.mark.anyio
async def test_full_finding_lifecycle_flow(mock_session: AsyncMock) -> None:
    """Full lifecycle: confidence calc -> analyst review -> remediation approval."""
    org_id = uuid4()
    finding_id = uuid4()
    reviewer_id = uuid4()
    plan_id = uuid4()

    finding = _make_finding(finding_id=finding_id, org_id=org_id)
    plan = AIRemediationPlanModel()
    plan.id = plan_id
    plan.organization_id = org_id
    plan.finding_id = finding_id
    plan.root_finding_id = finding_id
    plan.status = "AI_RECOMMENDED"

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "security_findings" in stmt_str:
            res.scalar_one_or_none.return_value = finding
        elif "ai_remediation_plans" in stmt_str:
            res.scalar_one_or_none.return_value = plan
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    # Step 1: Confidence calculation
    conf_svc = FindingConfidenceService(mock_session)
    confidence = await conf_svc.calculate_confidence(finding_id, org_id)
    assert confidence.confidence_score > 0.0
    assert confidence.confidence_level in (
        ConfidenceLevel.LOW,
        ConfidenceLevel.MEDIUM,
        ConfidenceLevel.HIGH,
        ConfidenceLevel.CONFIRMED,
    )

    # Step 2: Human analyst review
    review_svc = FindingReviewService(mock_session)
    review_svc.audit_service.record_event = AsyncMock()
    review = await review_svc.submit_review(
        finding_id=finding_id,
        organization_id=org_id,
        reviewer_id=reviewer_id,
        decision=ReviewDecision.CONFIRM,
        comments="Verified in staging environment",
    )
    assert review.decision == ReviewDecision.CONFIRM

    # Step 3: Remediation approval
    rem_svc = RemediationGovernanceService(mock_session)
    rem_svc.audit_service.record_event = AsyncMock()
    approval = await rem_svc.approve_remediation(
        remediation_plan_id=plan_id,
        organization_id=org_id,
        approver_user_id=reviewer_id,
        notes="Approved after manual verification",
    )
    assert approval.new_state == RemediationStatus.APPROVED_FOR_IMPLEMENTATION
    assert plan.status == "APPROVED_FOR_IMPLEMENTATION"
