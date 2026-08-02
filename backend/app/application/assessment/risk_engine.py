"""Risk Intelligence Engine calculating CVSS, EPSS, composite risk scores, and remediation SLAs."""

from typing import List, Optional

from app.core.logging import get_logger
from app.domain.entities.assessment import (
    AssetCriticality,
    ConfidenceLevel,
    CVSSMetrics,
    EPSSMetrics,
    Finding,
    RiskMetrics,
    SeverityLevel,
)

logger = get_logger("vulnova.risk_engine")

# Severity baseline mapping (0.0 to 10.0 scale)
SEVERITY_BASELINES = {
    SeverityLevel.CRITICAL: 9.8,
    SeverityLevel.HIGH: 7.5,
    SeverityLevel.MEDIUM: 5.0,
    SeverityLevel.LOW: 2.5,
    SeverityLevel.INFO: 0.5,
}

# Asset criticality multipliers
ASSET_MULTIPLIERS = {
    AssetCriticality.CRITICAL: 1.5,
    AssetCriticality.HIGH: 1.2,
    AssetCriticality.MEDIUM: 1.0,
    AssetCriticality.LOW: 0.8,
}

# Confidence multipliers
CONFIDENCE_MULTIPLIERS = {
    ConfidenceLevel.HIGH: 1.0,
    ConfidenceLevel.MEDIUM: 0.85,
    ConfidenceLevel.LOW: 0.70,
}


def calculate_severity_factor(severity: SeverityLevel) -> float:
    """Calculate base severity factor (0.0 to 10.0 scale)."""
    return SEVERITY_BASELINES.get(severity, 5.0)


def calculate_cvss_factor(cvss: Optional[CVSSMetrics], severity_factor: float) -> float:
    """Return CVSS base score or fall back to severity baseline if missing."""
    if cvss and cvss.base_score > 0.0:
        return cvss.base_score
    return severity_factor


def calculate_epss_factor(epss: Optional[EPSSMetrics]) -> float:
    """Return EPSS exploit probability (0.0 to 1.0) or neutral fallback (0.20)."""
    if epss and epss.epss_score >= 0.0:
        return epss.epss_score
    return 0.20


def calculate_asset_factor(criticality: AssetCriticality) -> float:
    """Return asset criticality multiplier."""
    return ASSET_MULTIPLIERS.get(criticality, 1.0)


def calculate_confidence_factor(confidence: ConfidenceLevel) -> float:
    """Return detection confidence multiplier."""
    return CONFIDENCE_MULTIPLIERS.get(confidence, 1.0)


def calculate_final_risk_score(
    severity: SeverityLevel,
    cvss: Optional[CVSSMetrics],
    epss: Optional[EPSSMetrics],
    criticality: AssetCriticality,
    confidence: ConfidenceLevel,
) -> float:
    """Calculate normalized 0.0 to 100.0 composite risk score."""
    sev_factor = calculate_severity_factor(severity)
    cvss_factor = calculate_cvss_factor(cvss, sev_factor)
    epss_factor = calculate_epss_factor(epss)
    asset_factor = calculate_asset_factor(criticality)
    conf_factor = calculate_confidence_factor(confidence)

    # Composite formula: 60% CVSS/Severity + 40% EPSS Exploit Likelihood, scaled by Asset & Confidence
    base_weight = (cvss_factor * 0.6) + (epss_factor * 10.0 * 0.4)
    raw_score = base_weight * asset_factor * conf_factor * 10.0
    return min(100.0, max(0.0, round(raw_score, 1)))


class RiskIntelligenceEngine:
    """Engine normalizing vulnerability taxonomies, scoring risk metrics, and assigning SLAs."""

    def enrich_finding(
        self, finding: Finding, criticality: AssetCriticality = AssetCriticality.MEDIUM
    ) -> Finding:
        """Enrich a Finding with CVSS defaults, EPSS estimates, composite risk score, and SLA."""
        # 1. Provide Default CVSS Metrics if missing
        if not finding.cvss:
            sev_score = calculate_severity_factor(finding.severity)
            vector = (
                "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
                if finding.severity == SeverityLevel.CRITICAL
                else None
            )
            finding.cvss = CVSSMetrics(
                version="3.1",
                base_score=sev_score,
                vector_string=vector,
            )

        # 2. Provide Default EPSS Metrics if missing
        if not finding.epss:
            default_prob = (
                0.85
                if finding.severity == SeverityLevel.CRITICAL
                else (0.40 if finding.severity == SeverityLevel.HIGH else 0.15)
            )
            finding.epss = EPSSMetrics(
                epss_score=default_prob,
                percentile=default_prob,
            )

        # 3. Calculate Composite Risk Score
        risk_score = calculate_final_risk_score(
            severity=finding.severity,
            cvss=finding.cvss,
            epss=finding.epss,
            criticality=criticality,
            confidence=finding.confidence,
        )

        # 4. Assign Business Impact & Fix SLA
        if risk_score >= 85.0 or finding.severity == SeverityLevel.CRITICAL:
            impact = "CRITICAL"
            sla_hours = 24
            risk_lvl = "CRITICAL"
        elif risk_score >= 65.0 or finding.severity == SeverityLevel.HIGH:
            impact = "HIGH"
            sla_hours = 72
            risk_lvl = "HIGH"
        elif risk_score >= 35.0 or finding.severity == SeverityLevel.MEDIUM:
            impact = "MEDIUM"
            sla_hours = 336  # 14 days
            risk_lvl = "MEDIUM"
        else:
            impact = "LOW"
            sla_hours = 720  # 30 days
            risk_lvl = "LOW"

        finding.risk = RiskMetrics(
            composite_risk_score=risk_score,
            business_impact=impact,
            fix_sla_hours=sla_hours,
            risk_level=risk_lvl,
        )

        logger.debug(
            "risk_engine.finding_enriched",
            finding_id=str(finding.id),
            title=finding.title,
            risk_score=risk_score,
            sla_hours=sla_hours,
        )
        return finding

    def enrich_findings(
        self,
        findings: List[Finding],
        criticality: AssetCriticality = AssetCriticality.MEDIUM,
    ) -> List[Finding]:
        """Enrich a batch of findings with risk intelligence."""
        return [self.enrich_finding(f, criticality) for f in findings]
