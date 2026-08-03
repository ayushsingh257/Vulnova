"""Comprehensive test suite for Phase 6.3 Scan Execution Lifecycle State Machine & Retry Engine."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.application.assessment.dto import (
    DistributedLockStatusDTO,
    ScanLifecycleStateDTO,
    ScanStateTransitionRequest,
)
from app.application.assessment.scan_lifecycle_manager import (
    VALID_TRANSITIONS,
    ScanLifecycleManagerService,
)
from app.core.exceptions import (
    ConflictException,
    ResourceNotFoundException,
    ValidationException,
)
from app.domain.entities.scan_lifecycle import (
    RetryPolicy,
    ScanExecutionState,
    ScanLockMetadata,
    ScanStateTransitionEvent,
)
from app.infrastructure.database.models.assessment import AssessmentJobModel
from app.infrastructure.workers.scan_lock_manager import DistributedScanLockManager

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Domain Entity & Value Object Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_scan_execution_state_enum_values() -> None:
    """Test ScanExecutionState enum values."""
    assert ScanExecutionState.QUEUED.value == "QUEUED"
    assert ScanExecutionState.CRAWLING.value == "CRAWLING"
    assert ScanExecutionState.ASSESSING.value == "ASSESSING"
    assert ScanExecutionState.AI_ANALYSIS.value == "AI_ANALYSIS"
    assert ScanExecutionState.COMPLETED.value == "COMPLETED"
    assert ScanExecutionState.FAILED.value == "FAILED"
    assert ScanExecutionState.CANCELLED.value == "CANCELLED"
    assert ScanExecutionState.RETRYING.value == "RETRYING"


def test_scan_state_transition_event_enum_values() -> None:
    """Test ScanStateTransitionEvent enum values."""
    assert ScanStateTransitionEvent.DISPATCH.value == "DISPATCH"
    assert ScanStateTransitionEvent.START_CRAWL.value == "START_CRAWL"
    assert ScanStateTransitionEvent.START_ASSESSMENT.value == "START_ASSESSMENT"
    assert ScanStateTransitionEvent.START_AI_ANALYSIS.value == "START_AI_ANALYSIS"
    assert ScanStateTransitionEvent.COMPLETE.value == "COMPLETE"
    assert ScanStateTransitionEvent.FAIL.value == "FAIL"
    assert ScanStateTransitionEvent.CANCEL.value == "CANCEL"
    assert ScanStateTransitionEvent.RETRY.value == "RETRY"


def test_retry_policy_exponential_backoff_calculation() -> None:
    """Test RetryPolicy computes correct exponential backoff delays."""
    policy = RetryPolicy(
        max_retries=3,
        base_delay_seconds=5.0,
        backoff_factor=2.0,
        max_delay_seconds=300.0,
    )

    # Attempt 0: 5.0 * (2^0) = 5.0s
    assert policy.compute_backoff_delay(0) == 5.0
    # Attempt 1: 5.0 * (2^1) = 10.0s
    assert policy.compute_backoff_delay(1) == 10.0
    # Attempt 2: 5.0 * (2^2) = 20.0s
    assert policy.compute_backoff_delay(2) == 20.0
    # Attempt 10: capped at max_delay_seconds (300.0s)
    assert policy.compute_backoff_delay(10) == 300.0


def test_scan_lock_metadata_defaults() -> None:
    """Test ScanLockMetadata value object defaults."""
    meta = ScanLockMetadata()
    assert meta.ttl_seconds == 3600
    assert meta.lock_key == ""
    assert isinstance(meta.organization_id, UUID)
    assert isinstance(meta.acquired_at, datetime)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. Distributed Scan Lock Manager Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.anyio
async def test_distributed_lock_manager_acquire_and_release() -> None:
    """Test acquiring and releasing target scan lock."""
    lock_mgr = DistributedScanLockManager()
    await lock_mgr.clear_all_locks()

    org_id = uuid4()
    target_url = "https://example.com/api"

    # Initially not locked
    assert await lock_mgr.is_locked(org_id, target_url) is False

    # Acquire lock -> True
    acquired = await lock_mgr.acquire_lock(org_id, target_url, ttl_seconds=60)
    assert acquired is True
    assert await lock_mgr.is_locked(org_id, target_url) is True

    # Duplicate acquire -> False (collision)
    acquired_dup = await lock_mgr.acquire_lock(org_id, target_url, ttl_seconds=60)
    assert acquired_dup is False

    # Release lock -> True
    released = await lock_mgr.release_lock(org_id, target_url)
    assert released is True
    assert await lock_mgr.is_locked(org_id, target_url) is False


@pytest.mark.anyio
async def test_distributed_lock_tenant_isolation() -> None:
    """Test distributed lock keys are strictly isolated by organization ID."""
    lock_mgr = DistributedScanLockManager()
    await lock_mgr.clear_all_locks()

    org1 = uuid4()
    org2 = uuid4()
    target_url = "https://shared-target.com"

    # Org1 acquires lock
    assert await lock_mgr.acquire_lock(org1, target_url) is True

    # Org2 acquiring lock for same target URL should succeed (different tenant key)
    assert await lock_mgr.acquire_lock(org2, target_url) is True

    await lock_mgr.clear_all_locks()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. State Machine Transition Matrix Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_state_machine_valid_transitions() -> None:
    """Test ScanLifecycleManagerService validates legitimate state transitions."""
    mock_session = MagicMock()
    mgr = ScanLifecycleManagerService(mock_session)

    # Valid transitions
    assert (
        mgr.is_valid_transition(ScanExecutionState.QUEUED, ScanExecutionState.CRAWLING)
        is True
    )
    assert (
        mgr.is_valid_transition(
            ScanExecutionState.CRAWLING, ScanExecutionState.ASSESSING
        )
        is True
    )
    assert (
        mgr.is_valid_transition(
            ScanExecutionState.ASSESSING, ScanExecutionState.AI_ANALYSIS
        )
        is True
    )
    assert (
        mgr.is_valid_transition(
            ScanExecutionState.AI_ANALYSIS, ScanExecutionState.COMPLETED
        )
        is True
    )
    assert (
        mgr.is_valid_transition(
            ScanExecutionState.CRAWLING, ScanExecutionState.RETRYING
        )
        is True
    )
    assert (
        mgr.is_valid_transition(
            ScanExecutionState.RETRYING, ScanExecutionState.CRAWLING
        )
        is True
    )
    assert (
        mgr.is_valid_transition(
            ScanExecutionState.ASSESSING, ScanExecutionState.CANCELLED
        )
        is True
    )
    assert (
        mgr.is_valid_transition(
            ScanExecutionState.AI_ANALYSIS, ScanExecutionState.FAILED
        )
        is True
    )


def test_state_machine_invalid_transitions() -> None:
    """Test ScanLifecycleManagerService rejects illegal state transitions."""
    mock_session = MagicMock()
    mgr = ScanLifecycleManagerService(mock_session)

    # Invalid transitions
    assert (
        mgr.is_valid_transition(
            ScanExecutionState.COMPLETED, ScanExecutionState.CRAWLING
        )
        is False
    )
    assert (
        mgr.is_valid_transition(ScanExecutionState.FAILED, ScanExecutionState.ASSESSING)
        is False
    )
    assert (
        mgr.is_valid_transition(
            ScanExecutionState.CANCELLED, ScanExecutionState.AI_ANALYSIS
        )
        is False
    )
    assert (
        mgr.is_valid_transition(ScanExecutionState.QUEUED, ScanExecutionState.COMPLETED)
        is False
    )


@pytest.mark.anyio
async def test_transition_state_invalid_throws_validation_error() -> None:
    """Test transition_state raises ValidationException on invalid transition."""
    mock_session = MagicMock()
    mgr = ScanLifecycleManagerService(mock_session)

    mock_job = MagicMock(spec=AssessmentJobModel)
    mock_job.execution_state = "COMPLETED"
    mgr.repo.get_job_by_id = AsyncMock(return_value=mock_job)

    with pytest.raises(ValidationException) as exc_info:
        await mgr.transition_state(
            organization_id=uuid4(),
            job_id=uuid4(),
            target_state=ScanExecutionState.CRAWLING,
        )

    assert "invalid state transition" in str(exc_info.value).lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. Retry & Failure Handling Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.anyio
async def test_handle_scan_failure_schedules_retry() -> None:
    """Test handle_scan_failure schedules retry when retry_count < max_retries."""
    mock_session = MagicMock()
    mgr = ScanLifecycleManagerService(mock_session)
    mgr.audit_service.record_event = AsyncMock()

    mock_job = MagicMock(spec=AssessmentJobModel)
    mock_job.retry_count = 1
    mock_job.execution_state = "ASSESSING"
    mgr.repo.get_job_by_id = AsyncMock(return_value=mock_job)
    mgr.repo.increment_retry_count = AsyncMock()

    policy = RetryPolicy(max_retries=3)
    exc = Exception("Transient timeout")

    next_state = await mgr.handle_scan_failure(
        organization_id=uuid4(),
        job_id=uuid4(),
        exception=exc,
        retry_policy=policy,
    )

    assert next_state == ScanExecutionState.RETRYING
    mgr.repo.increment_retry_count.assert_called_once()
    mgr.audit_service.record_event.assert_called_once()


@pytest.mark.anyio
async def test_handle_scan_failure_exhausted_retries_fails_job() -> None:
    """Test handle_scan_failure transitions to FAILED when retries are exhausted."""
    mock_session = MagicMock()
    mgr = ScanLifecycleManagerService(mock_session)
    mgr.audit_service.record_event = AsyncMock()
    mgr.release_target_lock = AsyncMock()

    mock_job = MagicMock(spec=AssessmentJobModel)
    mock_job.retry_count = 3
    mock_job.execution_state = "ASSESSING"
    mock_job.target_url = "https://example.com"
    mgr.repo.get_job_by_id = AsyncMock(return_value=mock_job)
    mgr.repo.update_execution_state = AsyncMock(return_value=mock_job)

    policy = RetryPolicy(max_retries=3)
    exc = Exception("Persistent DB error")

    next_state = await mgr.handle_scan_failure(
        organization_id=uuid4(),
        job_id=uuid4(),
        exception=exc,
        retry_policy=policy,
    )

    assert next_state == ScanExecutionState.FAILED
    mgr.repo.update_execution_state.assert_called_once()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. DTO & Model Coverage Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_scan_state_transition_request_dto() -> None:
    """Test ScanStateTransitionRequest DTO construction."""
    req = ScanStateTransitionRequest(
        target_state="CRAWLING",
        current_step="Crawling URLs",
        reason="Manual trigger",
    )
    assert req.target_state == "CRAWLING"
    assert req.current_step == "Crawling URLs"
    assert req.reason == "Manual trigger"


def test_scan_lifecycle_state_dto() -> None:
    """Test ScanLifecycleStateDTO construction."""
    dto = ScanLifecycleStateDTO(
        job_id=str(uuid4()),
        organization_id=str(uuid4()),
        target_url="https://example.com",
        execution_state="ASSESSING",
        status="ASSESSING",
        current_step="Vulnerability Scanning",
        retry_count=1,
        max_retries=3,
        is_terminal=False,
    )
    assert dto.execution_state == "ASSESSING"
    assert dto.is_terminal is False


def test_distributed_lock_status_dto() -> None:
    """Test DistributedLockStatusDTO construction."""
    dto = DistributedLockStatusDTO(
        target_url="https://example.com",
        is_locked=True,
        lock_key="lock:scan:org1:1234",
        ttl_seconds=3600,
    )
    assert dto.is_locked is True
    assert dto.ttl_seconds == 3600
