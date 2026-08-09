"""Finding Confidence Intelligence Engine Service (Phase 12.6).

Calculates multi-dimensional finding confidence scores based on evidence quality,
scanner plugin reliability, automated reproduction success, and AI analysis.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.infrastructure.ai_confidence.dto import (
    ConfidenceLevel,
    FindingConfidenceResultDTO,
    VerificationStatus,
)
from app.infrastructure.database.models.ai_confidence import (
    AIFindingConfidenceAnalysisModel,
    FindingVerificationAttemptModel,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel

logger = get_logger("vulnova.finding_confidence_service")


class FindingConfidenceService:
    """Service calculating enterprise finding confidence scores and evidence authenticity metrics."""

    HIGH_RELIABILITY_PLUGINS = {
        "sql_injection_plugin",
        "xss_plugin",
        "auth_security_plugin",
        "api_security_plugin",
        "tls_security_plugin",
        "jwt_security_plugin",
        "cors_security_plugin",
        "network_service_plugin",
        "cloud_security_plugin",
        "security_headers_plugin",
    }

    SQL_ERROR_PATTERNS = [
        "syntax error in sql",
        "ora-",
        "mysql_",
        "postgresql",
        "sqlite3.operationalerror",
        "unclosed quotation mark",
    ]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def calculate_confidence(
        self, finding_id: UUID, organization_id: UUID
    ) -> FindingConfidenceResultDTO:
        """Calculate dynamic multi-factor confidence score for a security finding."""
        stmt = select(SecurityFindingModel).where(
            SecurityFindingModel.id == finding_id,
            SecurityFindingModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        finding = res.scalar_one_or_none()
        if not finding:
            raise ResourceNotFoundException("Security finding not found.")

        # 1. Evidence Quality Score (0.0 to 100.0)
        evidence_quality = self._calculate_evidence_quality(finding)

        # 2. Scanner Plugin Reliability Score (0.0 to 100.0)
        scanner_reliability = (
            90.0 if finding.plugin_id in self.HIGH_RELIABILITY_PLUGINS else 75.0
        )

        # 3. Reproduction Score (0.0 to 100.0)
        reproduction_score, ver_status = await self._evaluate_reproduction(
            finding_id, organization_id
        )

        # 4. AI Analysis Score (0.0 to 100.0)
        ai_score = await self._evaluate_ai_score(finding_id, organization_id)

        # 5. Composite Confidence Score Calculation
        confidence_score = round(
            (0.35 * evidence_quality)
            + (0.25 * scanner_reliability)
            + (0.25 * reproduction_score)
            + (0.15 * ai_score),
            2,
        )

        # Map to ConfidenceLevel
        if confidence_score >= 90.0 or ver_status == VerificationStatus.CONFIRMED:
            confidence_level = ConfidenceLevel.CONFIRMED
        elif confidence_score >= 75.0:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence_score >= 50.0:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW

        explanation = (
            f"Finding evaluated with confidence score {confidence_score}% ({confidence_level.value}). "
            f"Evidence Quality: {evidence_quality}%, Scanner Reliability: {scanner_reliability}%, "
            f"Reproduction Score: {reproduction_score}%, AI Analysis Score: {ai_score}%."
        )

        logger.info(
            "finding_confidence.calculated",
            org_id=str(organization_id),
            finding_id=str(finding_id),
            confidence_score=confidence_score,
            confidence_level=confidence_level.value,
        )

        return FindingConfidenceResultDTO(
            finding_id=finding_id,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            evidence_quality_score=evidence_quality,
            reproduction_score=reproduction_score,
            ai_analysis_score=ai_score,
            verification_status=ver_status,
            explanation=explanation,
        )

    def _calculate_evidence_quality(self, finding: SecurityFindingModel) -> float:
        """Score evidence completeness from HTTP payloads, database errors, and stack traces."""
        score = 30.0  # Base score for finding title/description

        ev_dict = (
            finding.evidence_json if isinstance(finding.evidence_json, dict) else {}
        )
        ev_str = " ".join(str(v) for v in ev_dict.values()).lower()
        desc = (finding.description or "").lower()
        rem = (finding.remediation or "").lower()
        raw_ev = str(getattr(finding, "raw_evidence", "") or "").lower()
        poc = str(getattr(finding, "proof_of_concept", "") or "").lower()
        evidence_text = f"{ev_str} {desc} {rem} {raw_ev} {poc}"

        if (
            "http/" in evidence_text
            or "get " in evidence_text
            or "post " in evidence_text
        ):
            score += 35.0

        if (
            any(pat in evidence_text for pat in self.SQL_ERROR_PATTERNS)
            or "exception" in evidence_text
        ):
            score += 35.0
        elif len(evidence_text) > 100:
            score += 20.0

        return min(100.0, score)

    async def _evaluate_reproduction(
        self, finding_id: UUID, organization_id: UUID
    ) -> tuple[float, VerificationStatus]:
        """Fetch latest verification attempt to evaluate reproduction score."""
        stmt = (
            select(FindingVerificationAttemptModel)
            .where(
                FindingVerificationAttemptModel.finding_id == finding_id,
                FindingVerificationAttemptModel.organization_id == organization_id,
            )
            .order_by(FindingVerificationAttemptModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        attempt = res.scalar_one_or_none()

        if not attempt:
            return 50.0, VerificationStatus.UNVERIFIED

        if attempt.is_reproduced:
            return 95.0, VerificationStatus.CONFIRMED
        elif attempt.verification_status == "FALSE_POSITIVE":
            return 10.0, VerificationStatus.FALSE_POSITIVE
        elif attempt.verification_status == "VERIFYING":
            return 60.0, VerificationStatus.VERIFYING
        else:
            return 40.0, VerificationStatus.NEEDS_REVIEW

    async def _evaluate_ai_score(
        self, finding_id: UUID, organization_id: UUID
    ) -> float:
        """Fetch AI confidence analysis prediction if available."""
        stmt = (
            select(AIFindingConfidenceAnalysisModel)
            .where(
                AIFindingConfidenceAnalysisModel.finding_id == finding_id,
                AIFindingConfidenceAnalysisModel.organization_id == organization_id,
            )
            .order_by(AIFindingConfidenceAnalysisModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        analysis = res.scalar_one_or_none()

        if analysis and analysis.confidence_score is not None:
            # Map 0.0 - 1.0 to 0.0 - 100.0 if necessary
            score = analysis.confidence_score
            return score * 100.0 if score <= 1.0 else score
        return 75.0
