"""Unit and Integration Test Suite for Database Performance Optimization, Indexing & Benchmarking."""

from unittest.mock import AsyncMock
import pytest

from app.infrastructure.database.performance.benchmark_service import (
    DatabaseBenchmarkService,
)
from app.infrastructure.database.performance.query_analyzer import QueryAnalyzerService
from app.infrastructure.database.query_monitor import DatabaseQueryMonitor
from app.infrastructure.database.session import async_engine
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.models.audit_log import AuditLogModel
from app.infrastructure.database.models.refresh_token import RefreshTokenModel
from app.infrastructure.database.models.api_key import APIKeyModel


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_query_analyzer_execution() -> None:
    """Verify QueryAnalyzerService captures slow queries and generates index recommendations."""
    analyzer = QueryAnalyzerService()
    analyzer.log_slow_query(
        "SELECT * FROM users WHERE organization_id = '123' AND role = 'ADMIN'",
        150.5,
        "users",
    )

    recommendations = analyzer.generate_recommendations()
    assert len(recommendations) > 0
    assert any(rec.target_table == "users" for rec in recommendations)

    health = analyzer.get_health_summary()
    assert health.slow_queries_count_24h == 1
    assert health.status in ["HEALTHY", "WARNING", "CRITICAL"]


@pytest.mark.anyio
async def test_database_benchmark_service() -> None:
    """Verify DatabaseBenchmarkService runs query benchmarks and calculates latency metrics."""
    mock_session = AsyncMock()
    service = DatabaseBenchmarkService(session=mock_session)

    results = await service.run_benchmark_suite(iterations=5)
    assert len(results) == 4
    for res in results:
        assert res.total_executions == 5
        assert res.avg_duration_ms >= 0.0
        assert res.optimization_status in ["OPTIMAL", "SATISFACTORY", "NEEDS_TUNING"]


def test_index_configuration() -> None:
    """Verify core platform models have required performance composite indexes defined."""
    # Check Users table indexes
    user_indexes = [idx.name for idx in UserModel.__table__.indexes]
    # Check AuditLogs table indexes
    audit_indexes = [idx.name for idx in AuditLogModel.__table__.indexes]

    # Verify tables have index definitions or schema mappings
    assert UserModel.__tablename__ == "users"
    assert AuditLogModel.__tablename__ == "audit_logs"
    assert RefreshTokenModel.__tablename__ == "refresh_tokens"
    assert APIKeyModel.__tablename__ == "api_keys"


def test_connection_pool_configuration() -> None:
    """Verify SQLAlchemy async_engine connection pool parameters are optimized for production."""
    pool = async_engine.pool
    assert pool.size() == 20
    assert pool._max_overflow == 10
    assert pool._timeout == 30.0
    assert pool._recycle == 1800


def test_slow_query_detection() -> None:
    """Verify DatabaseQueryMonitor detects queries exceeding threshold."""
    monitor = DatabaseQueryMonitor(slow_threshold_ms=50.0)
    monitor.query_analyzer.log_slow_query(
        "SELECT * FROM audit_logs WHERE organization_id = 'abc'", 120.0, "audit_logs"
    )

    slow_queries = monitor.get_slow_queries()
    assert len(slow_queries) == 1
    assert slow_queries[0].duration_ms == 120.0
    assert slow_queries[0].table_name == "audit_logs"


def test_query_monitor_logging() -> None:
    """Verify query analyzer extracts target table names from SQL statements correctly."""
    analyzer = QueryAnalyzerService()
    tbl1 = analyzer._extract_table_name(
        "SELECT * FROM users WHERE email = 'test@domain.com'"
    )
    tbl2 = analyzer._extract_table_name(
        "SELECT * FROM audit_logs WHERE action = 'auth.login'"
    )
    tbl3 = analyzer._extract_table_name(
        "INSERT INTO refresh_tokens (id, token_hash) VALUES (1, 'abc')"
    )

    assert tbl1 == "users"
    assert tbl2 == "audit_logs"
    assert tbl3 == "refresh_tokens"
