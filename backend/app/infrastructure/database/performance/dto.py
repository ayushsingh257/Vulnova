"""Data Transfer Objects (DTOs) for Database Performance Analysis and Query Benchmarking."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SlowQueryLogDTO(BaseModel):
    """Captured slow query log record."""

    statement: str = Field(..., description="SQL statement text")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    timestamp: datetime = Field(..., description="Timestamp when query executed")
    table_name: Optional[str] = Field(
        default=None, description="Primary affected database table"
    )


class QueryOptimizationRecommendationDTO(BaseModel):
    """Query optimization recommendation."""

    target_table: str = Field(..., description="Target database table")
    query_pattern: str = Field(..., description="Query pattern or filter pattern")
    recommendation: str = Field(
        ..., description="Index creation or query refactoring advice"
    )
    estimated_impact: str = Field(
        ..., description="Expected performance gain percentage or impact rating"
    )


class BenchmarkResultDTO(BaseModel):
    """Benchmark execution result for a query category."""

    query_category: str = Field(
        ..., description="Category name (e.g., Tenant User Lookup, Audit Log Filter)"
    )
    total_executions: int = Field(
        ..., description="Number of query runs in benchmark batch"
    )
    avg_duration_ms: float = Field(
        ..., description="Average query duration in milliseconds"
    )
    p95_duration_ms: float = Field(
        ..., description="95th percentile query duration in milliseconds"
    )
    p99_duration_ms: float = Field(
        ..., description="99th percentile query duration in milliseconds"
    )
    optimization_status: str = Field(
        ..., description="Optimization rating: OPTIMAL, SATISFACTORY, or NEEDS_TUNING"
    )
    recommendation: Optional[str] = Field(
        default=None, description="Actionable optimization advice"
    )


class DatabaseHealthSummaryDTO(BaseModel):
    """Overall Database Layer Performance and Pool Health Summary."""

    status: str = Field(
        ..., description="Overall health rating: HEALTHY, WARNING, or CRITICAL"
    )
    avg_query_latency_ms: float = Field(
        ..., description="Global average query latency in milliseconds"
    )
    p95_query_latency_ms: float = Field(
        ..., description="Global 95th percentile query latency in milliseconds"
    )
    slow_queries_count_24h: int = Field(
        ..., description="Number of queries exceeding 100ms threshold in last 24h"
    )
    connection_pool_size: int = Field(
        ..., description="Configured SQLAlchemy connection pool size"
    )
    active_connections: int = Field(
        ..., description="Currently active checked-out DB connections"
    )
    overflow_connections: int = Field(
        ..., description="Current overflow connections in use"
    )
    recommendations: List[QueryOptimizationRecommendationDTO] = Field(
        default_factory=list, description="List of performance tuning recommendations"
    )
