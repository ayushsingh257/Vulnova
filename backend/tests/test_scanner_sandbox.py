"""Enterprise Scanner Execution Sandbox & Isolation Architecture Test Suite (Era 12 Phase 12.4)."""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock
import pytest
from uuid import uuid4

from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.domain.entities.role import Role, role_has_permission
from app.infrastructure.database.models.scanner_sandbox import ScannerSandboxModel
from app.infrastructure.database.repositories.scanner_sandbox_repository import (
    ScannerSandboxRepository,
)
from app.infrastructure.scanner_sandbox.container_driver import (
    EphemeralContainerDriver,
)
from app.infrastructure.scanner_sandbox.dto import (
    SandboxCreationRequestDTO,
    SandboxExecutionResultDTO,
    SandboxSecurityConfigDTO,
    SandboxStatus,
)
from app.infrastructure.scanner_sandbox.sandbox_manager import (
    ScannerSandboxManager,
)
from app.infrastructure.scanner_sandbox.security_policy import (
    SandboxSecurityViolationException,
    ScannerSecurityPolicy,
)
from app.main import app
from app.security.jwt import create_access_token


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
async def test_sandbox_security_policy_validation() -> None:
    """Validate sandbox security policy enforces resource bounds and non-root execution."""
    # 1. Valid Security Config
    valid_config = SandboxSecurityConfigDTO(
        cpu_limit="1.0",
        memory_limit="512m",
        max_processes=100,
        execution_timeout_seconds=1800,
        non_root_uid=10001,
        non_root_gid=10001,
    )
    validated = ScannerSecurityPolicy.validate_security_config(valid_config)
    assert validated.cpu_limit == "1.0"
    assert validated.memory_limit == "512m"

    # 2. Reject Root Execution (UID 0)
    root_config = SandboxSecurityConfigDTO(non_root_uid=0)
    with pytest.raises(SandboxSecurityViolationException, match="Root execution"):
        ScannerSecurityPolicy.validate_security_config(root_config)

    # 3. Reject Excessive CPU Limit (> 2.0)
    excess_cpu = SandboxSecurityConfigDTO(cpu_limit="4.0")
    with pytest.raises(SandboxSecurityViolationException, match="CPU allocation"):
        ScannerSecurityPolicy.validate_security_config(excess_cpu)

    # 4. Reject Excessive Memory Limit (> 2048m)
    excess_mem = SandboxSecurityConfigDTO(memory_limit="4096m")
    with pytest.raises(SandboxSecurityViolationException, match="Memory allocation"):
        ScannerSecurityPolicy.validate_security_config(excess_mem)


@pytest.mark.anyio
async def test_target_network_policy_validation() -> None:
    """Validate RFC1918 private IP and cloud metadata network blocklist policy."""
    # Public domain target -> Allowed
    ok, msg = ScannerSecurityPolicy.validate_target_address("https://example.com/api")
    assert ok is True

    # Loopback localhost -> Rejected
    ok, msg = ScannerSecurityPolicy.validate_target_address("http://localhost:8000")
    assert ok is False
    assert "loopback" in msg.lower() or "localhost" in msg.lower()

    # RFC1918 Private IPs -> Rejected
    prohibited_ips = [
        "http://10.0.0.5/scan",
        "http://192.168.1.1/admin",
        "http://172.16.0.1",
    ]
    for target in prohibited_ips:
        ok, msg = ScannerSecurityPolicy.validate_target_address(target)
        assert ok is False
        assert "private network" in msg.lower() or "prohibited" in msg.lower()

    # Cloud Metadata Service (169.254.169.254) -> Rejected
    ok, msg = ScannerSecurityPolicy.validate_target_address(
        "http://169.254.169.254/latest/meta-data"
    )
    assert ok is False


@pytest.mark.anyio
async def test_sandbox_repository_crud(mock_session: AsyncMock) -> None:
    """Verify CRUD operations on ScannerSandboxRepository using mock AsyncSession."""
    org_id = uuid4()
    job_id = uuid4()
    sandbox_id = uuid4()

    repo = ScannerSandboxRepository(mock_session)
    sandbox_model = ScannerSandboxModel(
        id=sandbox_id,
        organization_id=org_id,
        scan_job_id=job_id,
        container_id=f"test-sb-{str(sandbox_id)[:8]}",
        status=SandboxStatus.CREATED.value,
        cpu_limit="1.0",
        memory_limit="512m",
        read_only_rootfs=True,
    )
    saved = await repo.create_sandbox(sandbox_model)
    assert saved.id == sandbox_id
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()

    # Mock DB Query scalar return for update_status
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sandbox_model
    mock_session.execute.return_value = mock_result

    updated = await repo.update_status(sandbox_id, "RUNNING")
    assert updated is not None
    assert updated.status == "RUNNING"

    updated = await repo.update_status(sandbox_id, "DESTROYED")
    assert updated is not None
    assert updated.status == "DESTROYED"


@pytest.mark.anyio
async def test_sandbox_manager_full_execution_flow(mock_session: AsyncMock) -> None:
    """Verify complete sandbox lifecycle orchestration, result collection, and auto-destruction."""
    org_id = uuid4()
    job_id = uuid4()

    manager = ScannerSandboxManager(mock_session)

    # Mock audit log service record_event to prevent DB calls
    manager.audit_service.record_event = AsyncMock()  # type: ignore[method-assign]

    # Mock DB Query scalar return for repository updates
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    request = SandboxCreationRequestDTO(
        organization_id=org_id,
        scan_job_id=job_id,
        target_url="https://example.com",
        enabled_plugins=["xss_plugin", "sqli_plugin"],
    )

    result = await manager.execute_sandboxed_scan(request)
    assert result.scan_job_id == job_id
    assert result.status == SandboxStatus.DESTROYED
    assert result.exit_code == 0
    assert len(result.raw_findings) >= 1
    assert manager.audit_service.record_event.call_count >= 3


@pytest.mark.anyio
async def test_sandbox_manager_policy_rejection_flow(mock_session: AsyncMock) -> None:
    """Verify sandbox manager cleanly rejects targets violating security policy and logs failure."""
    org_id = uuid4()
    job_id = uuid4()

    manager = ScannerSandboxManager(mock_session)
    manager.audit_service.record_event = AsyncMock()  # type: ignore[method-assign]

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    request = SandboxCreationRequestDTO(
        organization_id=org_id,
        scan_job_id=job_id,
        target_url="http://10.0.0.1/private-admin",
        enabled_plugins=["sqli_plugin"],
    )

    result = await manager.execute_sandboxed_scan(request)
    assert result.status == SandboxStatus.DESTROYED
    assert result.exit_code == 1
    assert "Policy Violation" in result.error_log


@pytest.mark.anyio
async def test_scanner_sandbox_permission_mapping() -> None:
    """Verify RBAC role permission mapping for scanner sandbox execution operations."""
    assert role_has_permission(Role.VIEWER, "sandbox:read") is True
    assert role_has_permission(Role.VIEWER, "sandbox:execute") is False
    assert role_has_permission(Role.SECURITY_ANALYST, "sandbox:execute") is True
    assert role_has_permission(Role.SECURITY_ANALYST, "sandbox:manage") is False
    assert role_has_permission(Role.ADMIN, "sandbox:manage") is True
