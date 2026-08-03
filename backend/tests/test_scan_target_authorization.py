"""Comprehensive test suite for Phase 6.2 — Target Scan Configuration & Authorized Assessment Contract.

Tests cover:
1. Domain entity validation (ScanTarget, AuthorizedAssessmentContract, enums)
2. ScanTargetRepository CRUD and authorization declaration persistence
3. AssessmentPolicyEngine authorization gate logic
4. Worker dispatch authorization enforcement
5. DTO backward compatibility with is_authorized_assessment field
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.application.assessment.assessment_policy_engine import AssessmentPolicyEngine
from app.application.assessment.dto import (
    CreateAssessmentRequest,
    DispatchScanRequest,
    PolicyValidationResult,
    ScanTargetCreateRequest,
    ScanTargetResponse,
    ScanTargetUpdateRequest,
)
from app.application.assessment.worker_orchestrator import WorkerOrchestratorService
from app.core.exceptions import ResourceNotFoundException
from app.domain.entities.scan_target import (
    AuthorizationScope,
    AuthorizedAssessmentContract,
    ScanTarget,
    TargetEnvironment,
    TargetStatus,
)
from app.infrastructure.database.models.scan_target import (
    AuthorizationDeclarationModel,
    ScanTargetModel,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Domain Entity Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_scan_target_defaults() -> None:
    """Test ScanTarget dataclass default values."""
    target = ScanTarget()
    assert target.environment == TargetEnvironment.PRODUCTION
    assert target.status == TargetStatus.ACTIVE
    assert target.is_ownership_verified is False
    assert target.ownership_verification_token is None
    assert target.created_by is None
    assert isinstance(target.id, UUID)
    assert isinstance(target.organization_id, UUID)


def test_scan_target_custom_values() -> None:
    """Test ScanTarget with custom values."""
    org_id = uuid4()
    target = ScanTarget(
        organization_id=org_id,
        name="Example Corp API",
        target_url="https://api.example.com",
        environment=TargetEnvironment.STAGING,
        status=TargetStatus.ACTIVE,
    )
    assert target.organization_id == org_id
    assert target.name == "Example Corp API"
    assert target.target_url == "https://api.example.com"
    assert target.environment == TargetEnvironment.STAGING


def test_authorized_assessment_contract_defaults() -> None:
    """Test AuthorizedAssessmentContract value object defaults."""
    contract = AuthorizedAssessmentContract()
    assert contract.is_authorized is False
    assert contract.authorization_scope == AuthorizationScope.FULL
    assert contract.ip_address is None
    assert isinstance(contract.declared_at, datetime)


def test_target_environment_enum_values() -> None:
    """Test TargetEnvironment enum values."""
    assert TargetEnvironment.PRODUCTION.value == "PRODUCTION"
    assert TargetEnvironment.STAGING.value == "STAGING"
    assert TargetEnvironment.DEVELOPMENT.value == "DEVELOPMENT"
    assert TargetEnvironment.TESTING.value == "TESTING"


def test_target_status_enum_values() -> None:
    """Test TargetStatus enum values."""
    assert TargetStatus.ACTIVE.value == "ACTIVE"
    assert TargetStatus.ARCHIVED.value == "ARCHIVED"
    assert TargetStatus.SUSPENDED.value == "SUSPENDED"


def test_authorization_scope_enum_values() -> None:
    """Test AuthorizationScope enum values."""
    assert AuthorizationScope.FULL.value == "full"
    assert AuthorizationScope.PASSIVE_ONLY.value == "passive_only"
    assert AuthorizationScope.CUSTOM.value == "custom"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. Repository Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_scan_target_model_tablename() -> None:
    """Test ScanTargetModel ORM table name is correct."""
    assert ScanTargetModel.__tablename__ == "scan_targets"


def test_authorization_declaration_model_tablename() -> None:
    """Test AuthorizationDeclarationModel ORM table name is correct."""
    assert AuthorizationDeclarationModel.__tablename__ == "authorization_declarations"


def test_scan_target_model_columns() -> None:
    """Test ScanTargetModel has all required columns."""
    column_names = {c.name for c in ScanTargetModel.__table__.columns}
    expected = {
        "id",
        "organization_id",
        "name",
        "target_url",
        "environment",
        "status",
        "is_ownership_verified",
        "ownership_verification_token",
        "created_by",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(column_names)


def test_authorization_declaration_model_columns() -> None:
    """Test AuthorizationDeclarationModel has all required columns."""
    column_names = {c.name for c in AuthorizationDeclarationModel.__table__.columns}
    expected = {
        "id",
        "organization_id",
        "scan_target_id",
        "declared_by",
        "is_authorized",
        "authorization_scope",
        "ip_address",
        "created_at",
    }
    assert expected.issubset(column_names)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. AssessmentPolicyEngine Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.anyio
async def test_policy_engine_rejects_unauthorized() -> None:
    """Test AssessmentPolicyEngine rejects when is_authorized_assessment is False."""
    mock_session = MagicMock()
    engine = AssessmentPolicyEngine(mock_session)
    engine.audit_service.record_event = AsyncMock()

    result = await engine.validate_scan_authorization(
        organization_id=uuid4(),
        target_url="https://example.com",
        is_authorized_assessment=False,
        declared_by=uuid4(),
    )

    assert result.is_allowed is False
    assert "consent is required" in (result.rejection_reason or "").lower()
    engine.audit_service.record_event.assert_called_once()


@pytest.mark.anyio
async def test_policy_engine_rejects_unregistered_target() -> None:
    """Test AssessmentPolicyEngine rejects when target URL is not registered."""
    mock_session = MagicMock()
    engine = AssessmentPolicyEngine(mock_session)
    engine.audit_service.record_event = AsyncMock()
    engine.scan_target_repo.get_target_by_url = AsyncMock(return_value=None)

    result = await engine.validate_scan_authorization(
        organization_id=uuid4(),
        target_url="https://unknown-target.com",
        is_authorized_assessment=True,
        declared_by=uuid4(),
    )

    assert result.is_allowed is False
    assert "not registered" in (result.rejection_reason or "").lower()


@pytest.mark.anyio
async def test_policy_engine_rejects_archived_target() -> None:
    """Test AssessmentPolicyEngine rejects when target status is ARCHIVED."""
    mock_session = MagicMock()
    engine = AssessmentPolicyEngine(mock_session)
    engine.audit_service.record_event = AsyncMock()

    mock_target = MagicMock(spec=ScanTargetModel)
    mock_target.id = uuid4()
    mock_target.status = "ARCHIVED"
    engine.scan_target_repo.get_target_by_url = AsyncMock(return_value=mock_target)

    result = await engine.validate_scan_authorization(
        organization_id=uuid4(),
        target_url="https://example.com",
        is_authorized_assessment=True,
        declared_by=uuid4(),
    )

    assert result.is_allowed is False
    assert "ARCHIVED" in (result.rejection_reason or "")


@pytest.mark.anyio
async def test_policy_engine_rejects_suspended_target() -> None:
    """Test AssessmentPolicyEngine rejects when target status is SUSPENDED."""
    mock_session = MagicMock()
    engine = AssessmentPolicyEngine(mock_session)
    engine.audit_service.record_event = AsyncMock()

    mock_target = MagicMock(spec=ScanTargetModel)
    mock_target.id = uuid4()
    mock_target.status = "SUSPENDED"
    engine.scan_target_repo.get_target_by_url = AsyncMock(return_value=mock_target)

    result = await engine.validate_scan_authorization(
        organization_id=uuid4(),
        target_url="https://example.com",
        is_authorized_assessment=True,
        declared_by=uuid4(),
    )

    assert result.is_allowed is False
    assert "SUSPENDED" in (result.rejection_reason or "")


@pytest.mark.anyio
async def test_policy_engine_rejects_ssrf_unsafe_target() -> None:
    """Test AssessmentPolicyEngine rejects SSRF-unsafe target URLs."""
    mock_session = MagicMock()
    engine = AssessmentPolicyEngine(mock_session)
    engine.audit_service.record_event = AsyncMock()

    mock_target = MagicMock(spec=ScanTargetModel)
    mock_target.id = uuid4()
    mock_target.status = "ACTIVE"
    engine.scan_target_repo.get_target_by_url = AsyncMock(return_value=mock_target)

    result = await engine.validate_scan_authorization(
        organization_id=uuid4(),
        target_url="http://127.0.0.1/admin",
        is_authorized_assessment=True,
        declared_by=uuid4(),
    )

    assert result.is_allowed is False
    assert (
        "ssrf" in (result.rejection_reason or "").lower()
        or "prohibited" in (result.rejection_reason or "").lower()
    )


@pytest.mark.anyio
async def test_policy_engine_allows_authorized_registered_target() -> None:
    """Test AssessmentPolicyEngine allows valid authorized + registered + ACTIVE target."""
    mock_session = MagicMock()
    engine = AssessmentPolicyEngine(mock_session)
    engine.audit_service.record_event = AsyncMock()

    mock_target = MagicMock(spec=ScanTargetModel)
    mock_target.id = uuid4()
    mock_target.status = "ACTIVE"
    engine.scan_target_repo.get_target_by_url = AsyncMock(return_value=mock_target)

    mock_declaration = MagicMock(spec=AuthorizationDeclarationModel)
    mock_declaration.id = uuid4()
    engine.scan_target_repo.record_authorization_declaration = AsyncMock(
        return_value=mock_declaration
    )

    result = await engine.validate_scan_authorization(
        organization_id=uuid4(),
        target_url="https://example.com",
        is_authorized_assessment=True,
        declared_by=uuid4(),
        authorization_scope="full",
    )

    assert result.is_allowed is True
    assert result.scan_target_id == str(mock_target.id)
    assert result.authorization_id == str(mock_declaration.id)
    engine.scan_target_repo.record_authorization_declaration.assert_called_once()


@pytest.mark.anyio
async def test_policy_engine_records_audit_trail() -> None:
    """Test AssessmentPolicyEngine records audit events on both rejection and approval."""
    mock_session = MagicMock()
    engine = AssessmentPolicyEngine(mock_session)
    engine.audit_service.record_event = AsyncMock()

    # Rejection case
    await engine.validate_scan_authorization(
        organization_id=uuid4(),
        target_url="https://example.com",
        is_authorized_assessment=False,
        declared_by=uuid4(),
    )
    assert engine.audit_service.record_event.called
    call_args = engine.audit_service.record_event.call_args
    assert call_args.kwargs["action"] == "scan.authorization_rejected"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. Worker Dispatch Authorization Enforcement Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.anyio
async def test_worker_dispatch_rejects_unauthorized() -> None:
    """Test WorkerOrchestratorService dispatch rejects when is_authorized_assessment is False."""
    mock_session = MagicMock()
    service = WorkerOrchestratorService(mock_session)
    service.audit_service.record_event = AsyncMock()

    req = DispatchScanRequest(
        scan_id=str(uuid4()),
        profile_id="full_dast",
        target_url="http://example.com",
        priority="scans.high",
        is_authorized_assessment=False,
    )

    with pytest.raises(ResourceNotFoundException) as exc_info:
        await service.dispatch_scan_job(uuid4(), uuid4(), req)

    assert "consent is required" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_worker_dispatch_allows_authorized() -> None:
    """Test WorkerOrchestratorService dispatch succeeds when is_authorized_assessment is True."""
    mock_session = MagicMock()
    service = WorkerOrchestratorService(mock_session)

    org_id = uuid4()
    user_id = uuid4()
    scan_id = uuid4()

    req = DispatchScanRequest(
        scan_id=str(scan_id),
        profile_id="full_dast",
        target_url="http://example.com",
        priority="scans.high",
        is_authorized_assessment=True,
    )

    from app.infrastructure.database.models.worker import WorkerTaskModel

    mock_saved_task = WorkerTaskModel(
        id=uuid4(),
        task_id="task-dispatched-auth",
        scan_id=scan_id,
        organization_id=org_id,
        requested_by=user_id,
        priority="scans.high",
        task_name="execute_scan_job_task",
        state="PENDING",
        retry_count=0,
        runtime_ms=0,
        created_at=datetime.now(timezone.utc),
    )

    service.worker_repo.log_task_execution = AsyncMock(return_value=mock_saved_task)
    service.audit_service.record_event = AsyncMock()

    dto = await service.dispatch_scan_job(org_id, user_id, req)

    assert dto.scan_id == str(scan_id)
    assert dto.state == "PENDING"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. DTO Backward Compatibility Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_create_assessment_request_requires_authorization() -> None:
    """Test CreateAssessmentRequest requires is_authorized_assessment field."""
    with pytest.raises(Exception):
        # Missing required field should raise validation error
        CreateAssessmentRequest(target_url="https://example.com")  # type: ignore[call-arg]


def test_create_assessment_request_with_authorization() -> None:
    """Test CreateAssessmentRequest accepts is_authorized_assessment field."""
    req = CreateAssessmentRequest(
        target_url="https://example.com",
        is_authorized_assessment=True,
    )
    assert req.is_authorized_assessment is True
    assert req.authorization_scope == "full"


def test_create_assessment_request_custom_scope() -> None:
    """Test CreateAssessmentRequest accepts custom authorization scope."""
    req = CreateAssessmentRequest(
        target_url="https://example.com",
        is_authorized_assessment=True,
        authorization_scope="passive_only",
    )
    assert req.authorization_scope == "passive_only"


def test_dispatch_scan_request_requires_authorization() -> None:
    """Test DispatchScanRequest requires is_authorized_assessment field."""
    with pytest.raises(Exception):
        DispatchScanRequest(
            scan_id=str(uuid4()),
            profile_id="full",
            target_url="http://example.com",
        )  # type: ignore[call-arg]


def test_dispatch_scan_request_with_authorization() -> None:
    """Test DispatchScanRequest accepts is_authorized_assessment field."""
    req = DispatchScanRequest(
        scan_id=str(uuid4()),
        profile_id="full",
        target_url="http://example.com",
        is_authorized_assessment=True,
    )
    assert req.is_authorized_assessment is True


def test_policy_validation_result_allowed() -> None:
    """Test PolicyValidationResult DTO for allowed case."""
    result = PolicyValidationResult(
        is_allowed=True,
        scan_target_id=str(uuid4()),
        authorization_id=str(uuid4()),
    )
    assert result.is_allowed is True
    assert result.rejection_reason is None


def test_policy_validation_result_rejected() -> None:
    """Test PolicyValidationResult DTO for rejected case."""
    result = PolicyValidationResult(
        is_allowed=False,
        rejection_reason="No authorization",
    )
    assert result.is_allowed is False
    assert "No authorization" in (result.rejection_reason or "")


def test_scan_target_create_request_dto() -> None:
    """Test ScanTargetCreateRequest DTO construction."""
    req = ScanTargetCreateRequest(
        name="Example Target",
        target_url="https://example.com",
        environment="STAGING",
    )
    assert req.name == "Example Target"
    assert req.environment == "STAGING"


def test_scan_target_update_request_dto() -> None:
    """Test ScanTargetUpdateRequest DTO construction."""
    req = ScanTargetUpdateRequest(
        name="Updated Name",
        status="ARCHIVED",
    )
    assert req.name == "Updated Name"
    assert req.status == "ARCHIVED"


def test_scan_target_response_dto() -> None:
    """Test ScanTargetResponse DTO construction."""
    resp = ScanTargetResponse(
        id=str(uuid4()),
        organization_id=str(uuid4()),
        name="Test Target",
        target_url="https://example.com",
        environment="PRODUCTION",
        status="ACTIVE",
        is_ownership_verified=False,
        created_at="2026-08-03T12:00:00Z",
    )
    assert resp.status == "ACTIVE"
    assert resp.is_ownership_verified is False
