"""Tests for Era 11 Phase 11.5 — Disaster Recovery, Failover & Rollback Services."""

import pytest

from app.infrastructure.disaster_recovery.dto import (
    DisasterRecoveryStatusDTO,
    FailoverEventDTO,
    RecoveryExecutionDTO,
    RollbackStatusDTO,
)
from app.infrastructure.disaster_recovery.failover_service import FailoverService
from app.infrastructure.disaster_recovery.recovery_service import RecoveryService
from app.infrastructure.disaster_recovery.rollback_service import RollbackService


@pytest.fixture()
def recovery_svc() -> RecoveryService:
    """Create a fresh RecoveryService instance for testing."""
    return RecoveryService()


@pytest.fixture()
def failover_svc() -> FailoverService:
    """Create a fresh FailoverService instance for testing."""
    return FailoverService()


@pytest.fixture()
def rollback_svc() -> RollbackService:
    """Create a fresh RollbackService instance for testing."""
    return RollbackService()


class TestRecoveryService:
    """Test suite for RecoveryService — DR status, execution, and history."""

    @pytest.mark.anyio
    async def test_get_dr_status_ready(self, recovery_svc: RecoveryService) -> None:
        """Verify initial DR status returns READY with correct RTO/RPO targets."""
        status = await recovery_svc.get_dr_status()
        assert isinstance(status, DisasterRecoveryStatusDTO)
        assert status.status == "READY"
        assert status.rto_target_minutes == 60
        assert status.rpo_target_minutes == 5
        assert status.primary_database_status == "HEALTHY"
        assert status.secondary_database_status == "STANDBY_READY"
        assert status.redis_cluster_status == "HEALTHY"
        assert status.active_recovery_id is None

    @pytest.mark.anyio
    async def test_execute_recovery_simulation(
        self, recovery_svc: RecoveryService
    ) -> None:
        """Verify SIMULATION recovery executes all 5 stages and meets RTO/RPO targets."""
        result = await recovery_svc.execute_recovery(recovery_type="SIMULATION")
        assert isinstance(result, RecoveryExecutionDTO)
        assert result.success is True
        assert result.recovery_type == "SIMULATION"
        assert len(result.stages_completed) == 5
        assert "DETECTION" in result.stages_completed
        assert "CONTAINMENT" in result.stages_completed
        assert "RECOVERY_EXECUTION" in result.stages_completed
        assert "VALIDATION" in result.stages_completed
        assert "SERVICE_RESTORATION" in result.stages_completed
        assert result.rto_target_met is True
        assert result.rpo_target_met is True

    @pytest.mark.anyio
    async def test_execute_recovery_pitr_restore(
        self, recovery_svc: RecoveryService
    ) -> None:
        """Verify PITR_RESTORE recovery type executes and completes."""
        result = await recovery_svc.execute_recovery(recovery_type="PITR_RESTORE")
        assert result.success is True
        assert result.recovery_type == "PITR_RESTORE"
        assert result.rto_target_met is True

    @pytest.mark.anyio
    async def test_recovery_history(self, recovery_svc: RecoveryService) -> None:
        """Verify recovery history accumulates records."""
        await recovery_svc.execute_recovery(recovery_type="SIMULATION")
        await recovery_svc.execute_recovery(recovery_type="FAILOVER")
        history = await recovery_svc.list_recovery_history()
        assert len(history) == 2
        types = [r.recovery_type for r in history]
        assert "SIMULATION" in types
        assert "FAILOVER" in types

    @pytest.mark.anyio
    async def test_dr_test_timestamp_updated_on_simulation(
        self, recovery_svc: RecoveryService
    ) -> None:
        """Verify last_dr_test_timestamp is set after a SIMULATION run."""
        assert recovery_svc._last_dr_test_timestamp is None
        await recovery_svc.execute_recovery(recovery_type="SIMULATION")
        assert recovery_svc._last_dr_test_timestamp is not None


class TestFailoverService:
    """Test suite for FailoverService — primary-to-secondary promotion."""

    @pytest.mark.anyio
    async def test_trigger_failover_success(
        self, failover_svc: FailoverService
    ) -> None:
        """Verify failover executes and returns COMPLETED status."""
        event = await failover_svc.trigger_failover()
        assert isinstance(event, FailoverEventDTO)
        assert event.status == "COMPLETED"
        assert event.triggered_by == "MANUAL_OPERATOR"
        assert "completed" in event.details.lower()

    @pytest.mark.anyio
    async def test_failover_history(self, failover_svc: FailoverService) -> None:
        """Verify failover history accumulates records."""
        await failover_svc.trigger_failover()
        await failover_svc.trigger_failover(triggered_by="AUTOMATED_DETECTOR")
        history = await failover_svc.list_failover_events()
        assert len(history) == 2


class TestRollbackService:
    """Test suite for RollbackService — deployment rollback operations."""

    @pytest.mark.anyio
    async def test_execute_rollback_success(
        self, rollback_svc: RollbackService
    ) -> None:
        """Verify rollback executes and returns SUCCESS with health check passed."""
        result = await rollback_svc.execute_rollback(target_version="11.4.0")
        assert isinstance(result, RollbackStatusDTO)
        assert result.status == "SUCCESS"
        assert result.target_version == "11.4.0"
        assert result.health_check_passed is True

    @pytest.mark.anyio
    async def test_rollback_history(self, rollback_svc: RollbackService) -> None:
        """Verify rollback history accumulates records."""
        await rollback_svc.execute_rollback(target_version="11.4.0")
        await rollback_svc.execute_rollback(target_version="11.3.0")
        history = await rollback_svc.list_rollback_history()
        assert len(history) == 2
        versions = [r.target_version for r in history]
        assert "11.4.0" in versions
        assert "11.3.0" in versions
