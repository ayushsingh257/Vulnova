"""Unit and Integration Tests for Phase 12.5 Target Ownership Verification & Scan Authorization Engine."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.entities.role import Role, role_has_permission
from app.infrastructure.database.models.scan_approval_request import (
    ScanApprovalRequestModel,
)
from app.infrastructure.database.models.scan_target import ScanTargetModel
from app.infrastructure.database.models.target_verification_challenge import (
    TargetVerificationChallengeModel,
)
from app.infrastructure.target_authorization.approval_service import (
    ScanApprovalService,
)
from app.infrastructure.target_authorization.authorization_service import (
    ScanAuthorizationService,
)
from app.infrastructure.target_authorization.dto import (
    ApprovalStatus,
    VerificationStatus,
    VerificationType,
)
from app.infrastructure.target_authorization.verification_service import (
    TargetVerificationService,
)


@pytest.fixture
def anyio_backend() -> str:
    """Restrict anyio test execution to asyncio backend."""
    return "asyncio"


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock SQLAlchemy AsyncSession for repository testing."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.anyio
async def test_dns_txt_verification_success(mock_session: AsyncMock) -> None:
    """Verify DNS TXT record challenge validation succeeds when token is present."""
    org_id = uuid4()
    target_id = uuid4()
    token = f"vn_verify_{uuid4().hex}"

    target_model = ScanTargetModel(
        id=target_id,
        organization_id=org_id,
        name="Example Domain",
        target_url="https://example.com",
        status="ACTIVE",
        is_ownership_verified=False,
    )
    challenge_model = TargetVerificationChallengeModel(
        id=uuid4(),
        target_id=target_id,
        organization_id=org_id,
        challenge_token=token,
        verification_type="DNS_TXT",
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=3),
    )

    async def _mock_exec(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "scan_targets" in stmt_str:
            res.scalar_one_or_none.return_value = target_model
        elif "target_verification_challenges" in stmt_str:
            res.scalar_one_or_none.return_value = challenge_model
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    service = TargetVerificationService(mock_session)
    service.audit_service.record_event = AsyncMock()  # type: ignore[method-assign]

    with patch.object(
        service, "_verify_dns_txt_record", new_callable=AsyncMock
    ) as mock_dns:
        mock_dns.return_value = (
            True,
            "DNS TXT verified",
            {"records": [token], "expected": token},
        )

        res = await service.verify_target_ownership(
            target_id=target_id, organization_id=org_id
        )
        assert res.verified is True
        assert res.status == VerificationStatus.VERIFIED
        assert "DNS TXT verified" in res.message


@pytest.mark.anyio
async def test_dns_txt_verification_failure(mock_session: AsyncMock) -> None:
    """Verify DNS TXT record challenge validation fails when token is missing."""
    org_id = uuid4()
    target_id = uuid4()
    token = f"vn_verify_{uuid4().hex}"

    target_model = ScanTargetModel(
        id=target_id,
        organization_id=org_id,
        name="Example Domain",
        target_url="https://unverified-example.com",
        status="ACTIVE",
        is_ownership_verified=False,
    )
    challenge_model = TargetVerificationChallengeModel(
        id=uuid4(),
        target_id=target_id,
        organization_id=org_id,
        challenge_token=token,
        verification_type="DNS_TXT",
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=3),
    )

    async def _mock_exec(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "scan_targets" in stmt_str:
            res.scalar_one_or_none.return_value = target_model
        else:
            res.scalar_one_or_none.return_value = challenge_model
        return res

    mock_session.execute.side_effect = _mock_exec

    service = TargetVerificationService(mock_session)
    service.audit_service.record_event = AsyncMock()  # type: ignore[method-assign]

    with patch.object(
        service, "_verify_dns_txt_record", new_callable=AsyncMock
    ) as mock_dns:
        mock_dns.return_value = (
            False,
            "Token not found in TXT records",
            {"records": ["wrong_record"]},
        )

        res = await service.verify_target_ownership(
            target_id=target_id, organization_id=org_id
        )
        assert res.verified is False
        assert res.status == VerificationStatus.FAILED


@pytest.mark.anyio
async def test_http_verification_success(mock_session: AsyncMock) -> None:
    """Verify HTTP well-known verification succeeds when endpoint returns token."""
    org_id = uuid4()
    target_id = uuid4()
    token = f"vn_verify_{uuid4().hex}"

    target_model = ScanTargetModel(
        id=target_id,
        organization_id=org_id,
        name="HTTP Target",
        target_url="https://http-target.org",
        status="ACTIVE",
        is_ownership_verified=False,
    )
    challenge_model = TargetVerificationChallengeModel(
        id=uuid4(),
        target_id=target_id,
        organization_id=org_id,
        challenge_token=token,
        verification_type="HTTP_WELL_KNOWN",
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=3),
    )

    async def _mock_exec(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "scan_targets" in stmt_str:
            res.scalar_one_or_none.return_value = target_model
        else:
            res.scalar_one_or_none.return_value = challenge_model
        return res

    mock_session.execute.side_effect = _mock_exec

    service = TargetVerificationService(mock_session)
    service.audit_service.record_event = AsyncMock()  # type: ignore[method-assign]

    with patch.object(
        service, "_verify_http_well_known", new_callable=AsyncMock
    ) as mock_http:
        mock_http.return_value = (
            True,
            "HTTP well-known token verified",
            {
                "status": 200,
                "url": "https://http-target.org/.well-known/vulnova-verification.txt",
            },
        )

        res = await service.verify_target_ownership(
            target_id=target_id, organization_id=org_id
        )
        assert res.verified is True
        assert res.status == VerificationStatus.VERIFIED


@pytest.mark.anyio
async def test_expired_challenge_rejection(mock_session: AsyncMock) -> None:
    """Verify expired verification challenge tokens are cleanly rejected."""
    org_id = uuid4()
    target_id = uuid4()

    target_model = ScanTargetModel(
        id=target_id,
        organization_id=org_id,
        name="Expired Target",
        target_url="https://expired.org",
        status="ACTIVE",
        is_ownership_verified=False,
    )
    expired_challenge = TargetVerificationChallengeModel(
        id=uuid4(),
        target_id=target_id,
        organization_id=org_id,
        challenge_token="vn_verify_expired",
        verification_type="DNS_TXT",
        status="PENDING",
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
        expires_at=datetime.now(timezone.utc) - timedelta(days=2),
    )

    async def _mock_exec(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "scan_targets" in stmt_str:
            res.scalar_one_or_none.return_value = target_model
        else:
            res.scalar_one_or_none.return_value = expired_challenge
        return res

    mock_session.execute.side_effect = _mock_exec

    service = TargetVerificationService(mock_session)
    res = await service.verify_target_ownership(
        target_id=target_id, organization_id=org_id
    )
    assert res.verified is False
    assert res.status == VerificationStatus.EXPIRED
    assert "expired" in res.message.lower()


@pytest.mark.anyio
async def test_unauthorized_unverified_scan_blocked(mock_session: AsyncMock) -> None:
    """Verify ScanAuthorizationService blocks scans against unverified targets."""
    org_id = uuid4()
    target_id = uuid4()

    unverified_target = ScanTargetModel(
        id=target_id,
        organization_id=org_id,
        name="Unverified Asset",
        target_url="https://unverified.app",
        status="ACTIVE",
        is_ownership_verified=False,
    )

    mock_session.execute.return_value = MagicMock(
        scalar_one_or_none=lambda: unverified_target
    )

    auth_service = ScanAuthorizationService(mock_session)
    auth_service.audit_service.record_event = AsyncMock()  # type: ignore[method-assign]

    auth_res = await auth_service.authorize_scan(
        target_id=target_id, organization_id=org_id
    )
    assert auth_res.authorized is False
    assert auth_res.is_verified is False
    assert "ownership verification required" in auth_res.reason.lower()


@pytest.mark.anyio
async def test_private_ip_and_cloud_metadata_blocked() -> None:
    """Verify ScanAuthorizationService blocks RFC1918 private IPs, localhost, and cloud metadata APIs."""
    mock_session = AsyncMock()
    service = ScanAuthorizationService(mock_session)

    prohibited_targets = [
        ("http://10.0.0.1/admin", "10.0.0.1"),
        ("http://192.168.1.1/dashboard", "192.168.1.1"),
        ("http://172.16.0.1/internal", "172.16.0.1"),
        ("http://127.0.0.1:8000", "localhost"),
        ("http://169.254.169.254/latest/meta-data", "cloud metadata"),
    ]

    for url, label in prohibited_targets:
        is_safe, reason = service.validate_target_address_safety(url)
        assert is_safe is False, f"Target {url} ({label}) should be blocked"
        assert (
            "prohibited" in reason.lower()
            or "private network" in reason.lower()
            or "loopback" in reason.lower()
        )


@pytest.mark.anyio
async def test_admin_scan_approval_workflow(mock_session: AsyncMock) -> None:
    """Verify full admin scan approval workflow (request, approve, reject)."""
    org_id = uuid4()
    target_id = uuid4()
    user_id = uuid4()
    admin_id = uuid4()
    req_id = uuid4()

    target_model = ScanTargetModel(
        id=target_id,
        organization_id=org_id,
        name="Production Target",
        target_url="https://prod.enterprise.com",
        environment="PRODUCTION",
        status="ACTIVE",
        is_ownership_verified=True,
    )

    approval_request = ScanApprovalRequestModel(
        id=req_id,
        organization_id=org_id,
        target_id=target_id,
        requested_by=user_id,
        status="PENDING_APPROVAL",
        reason="Scanning production database node",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    async def _mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        stmt_str = str(stmt).lower()
        if "scan_targets" in stmt_str:
            res.scalar_one_or_none.return_value = target_model
        elif "scan_approval_requests" in stmt_str:
            res.scalar_one_or_none.return_value = approval_request
        return res

    mock_session.execute.side_effect = _mock_exec

    service = ScanApprovalService(mock_session)
    service.audit_service.record_event = AsyncMock()  # type: ignore[method-assign]

    # 1. Create approval request
    created = await service.create_approval_request(
        organization_id=org_id,
        target_id=target_id,
        requested_by=user_id,
        reason="Scanning production database node",
    )
    assert created.status == ApprovalStatus.PENDING_APPROVAL

    # 2. Admin approves request
    approved = await service.approve_request(
        request_id=req_id,
        organization_id=org_id,
        approver_user_id=admin_id,
        reason="Authorized maintenance window",
    )
    assert approved.status == ApprovalStatus.APPROVED

    # Re-set status to pending for rejection test
    approval_request.status = "PENDING_APPROVAL"

    # 3. Admin rejects request
    rejected = await service.reject_request(
        request_id=req_id,
        organization_id=org_id,
        approver_user_id=admin_id,
        rejection_reason="Unapproved scan window",
    )
    assert rejected.status == ApprovalStatus.REJECTED


@pytest.mark.anyio
async def test_full_target_authorization_integration_flow(
    mock_session: AsyncMock,
) -> None:
    """Verify full end-to-end integration flow: Register target -> Verify ownership -> Authorization check -> Scan allowed."""
    org_id = uuid4()
    target_id = uuid4()

    # 1. Registered unverified target
    target_model = ScanTargetModel(
        id=target_id,
        organization_id=org_id,
        name="Production Web App",
        target_url="https://example.com",
        environment="STAGING",
        status="ACTIVE",
        is_ownership_verified=False,
    )

    challenge_model = TargetVerificationChallengeModel(
        id=uuid4(),
        target_id=target_id,
        organization_id=org_id,
        challenge_token="vn_verify_test",
        verification_type="DNS_TXT",
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    async def _mock_exec(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "scan_targets" in stmt_str:
            res.scalar_one_or_none.return_value = target_model
        elif "target_verification_challenges" in stmt_str:
            res.scalar_one_or_none.return_value = challenge_model
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    auth_service = ScanAuthorizationService(mock_session)
    auth_service.audit_service.record_event = AsyncMock()  # type: ignore[method-assign]

    verify_service = TargetVerificationService(mock_session)
    verify_service.audit_service.record_event = AsyncMock()  # type: ignore[method-assign]

    # Step A: Initial pre-scan check fails because target is unverified
    res_initial = await auth_service.authorize_scan(
        target_id=target_id, organization_id=org_id
    )
    assert res_initial.authorized is False
    assert res_initial.is_verified is False

    # Step B: Execute ownership verification
    with patch.object(
        verify_service, "_verify_dns_txt_record", new_callable=AsyncMock
    ) as mock_dns:
        mock_dns.return_value = (True, "DNS TXT matched", {})
        ver_result = await verify_service.verify_target_ownership(
            target_id=target_id, organization_id=org_id
        )
        assert ver_result.verified is True

    # Update model state to verified for post-verification check
    target_model.is_ownership_verified = True

    # Step C: Pre-scan authorization passes post-verification
    res_final = await auth_service.authorize_scan(
        target_id=target_id, organization_id=org_id
    )
    assert res_final.authorized is True
    assert res_final.is_verified is True
