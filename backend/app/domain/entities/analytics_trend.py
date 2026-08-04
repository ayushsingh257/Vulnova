"""Domain Entities and Value Objects for Executive Risk Analytics & Trends."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RiskVelocity(str, Enum):
    """Directional velocity classification of organization security posture."""

    STABLE = "STABLE"
    IMPROVING = "IMPROVING"
    DETERIORATING = "DETERIORATING"


class TimeframePeriod(str, Enum):
    """Time-series query historical lookback periods."""

    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"


@dataclass(frozen=True)
class RiskTrendPoint:
    """Historical risk score data point for a specific snapshot date."""

    date_str: str
    composite_risk_score: float
    open_findings_count: int
    critical_findings_count: int


@dataclass(frozen=True)
class AttackSurfaceEnvironmentBreakdown:
    """Target asset metrics grouped by deployment environment."""

    environment: str  # PRODUCTION, STAGING, DEVELOPMENT
    target_count: int
    risk_score: float


@dataclass(frozen=True)
class ExecutiveThreatAlert:
    """Executive security threat advisory or SLA breach alert."""

    severity: str  # CRITICAL, WARNING, INFO
    category: str
    title: str
    description: str
    affected_target_url: Optional[str] = None
