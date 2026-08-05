"""Framework Mapper Engine evaluating findings against compliance controls."""

from typing import List, Tuple

from app.application.compliance.dto import (
    ComplianceControlDTO,
    ComplianceFindingMappingDTO,
    ComplianceFrameworkDTO,
    ComplianceScoreResponse,
)
from app.application.compliance.mappings import (
    asvs_v4,
    iso27001,
    owasp_top10,
    pci_dss,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel

FRAMEWORK_MODULES = {
    "owasp_top10": owasp_top10,
    "asvs_v4": asvs_v4,
    "pci_dss": pci_dss,
    "iso27001": iso27001,
}

# Statuses that represent active open findings impacting compliance
ACTIVE_FINDING_STATUSES = {
    "OPEN",
    "CONFIRMED",
    "NEW",
    "UNREAD",
    "TRIAGED",
    "IN_REMEDIATION",
    "UNHANDLED",
}


class FrameworkMapper:
    """Evaluates security findings against compliance framework control definitions."""

    @staticmethod
    def get_supported_frameworks() -> List[ComplianceFrameworkDTO]:
        """Return metadata for all supported compliance frameworks."""
        frameworks: List[ComplianceFrameworkDTO] = []
        for _f_id, mod in FRAMEWORK_MODULES.items():
            meta = mod.FRAMEWORK_METADATA
            controls_count = len(mod.CONTROLS)
            frameworks.append(
                ComplianceFrameworkDTO(
                    id=meta["id"],
                    name=meta["name"],
                    version=meta["version"],
                    description=meta["description"],
                    total_controls=controls_count,
                )
            )
        return frameworks

    @staticmethod
    def _is_active_finding(finding: SecurityFindingModel) -> bool:
        """Check if finding is active/open (resolved/false-positive findings do not impact compliance)."""
        status = str(getattr(finding, "status", "CONFIRMED")).upper().strip()
        if status in (
            "RESOLVED",
            "FALSE_POSITIVE",
            "VERIFIED_FIXED",
            "SUPPRESSED",
            "CLOSED",
        ):
            return False
        return True

    @staticmethod
    def evaluate_framework(
        framework_id: str, findings: List[SecurityFindingModel]
    ) -> Tuple[
        ComplianceFrameworkDTO, List[ComplianceControlDTO], ComplianceScoreResponse
    ]:
        """Evaluate a list of findings against the specified framework controls."""
        mod = FRAMEWORK_MODULES.get(framework_id)
        if not mod:
            raise ValueError(f"Unsupported compliance framework '{framework_id}'")

        meta = mod.FRAMEWORK_METADATA
        raw_controls = mod.CONTROLS

        # Filter only active open findings for compliance evaluation
        active_findings = [f for f in findings if FrameworkMapper._is_active_finding(f)]

        control_dtos: List[ComplianceControlDTO] = []
        passed_count = 0
        failed_count = 0

        for ctrl in raw_controls:
            control_id = ctrl["control_id"]
            ctrl_title = ctrl["title"]
            ctrl_desc = ctrl["description"]
            ctrl_guidance = ctrl["remediation_guidance"]
            cwes = set(ctrl.get("cwes", []))
            categories = {c.lower() for c in ctrl.get("categories", [])}

            matched_findings: List[ComplianceFindingMappingDTO] = []

            for f in active_findings:
                # Match by CWE ID or Category
                f_cwe = str(f.cwe_id).strip() if f.cwe_id else ""
                f_cat = str(f.category).strip().lower() if f.category else ""
                f_title = str(f.title).strip().lower()

                is_match = False
                if f_cwe and f_cwe in cwes:
                    is_match = True
                elif f_cat and (
                    f_cat in categories or any(cat in f_cat for cat in categories)
                ):
                    is_match = True
                elif any(cat in f_title for cat in categories):
                    is_match = True

                if is_match:
                    # Extract evidence checksum/path for traceability
                    ev_checksum = None
                    if f.evidence_json and isinstance(f.evidence_json, dict):
                        ev_checksum = f.evidence_json.get(
                            "checksum"
                        ) or f.evidence_json.get("proof_hash")
                    elif hasattr(f, "artifacts") and f.artifacts:
                        art = f.artifacts[0]
                        ev_checksum = getattr(art, "checksum", None)

                    asset_name = None
                    if hasattr(f, "assessment_job") and f.assessment_job:
                        asset_name = getattr(f.assessment_job, "target_url", None)

                    mapped_dto = ComplianceFindingMappingDTO(
                        finding_id=str(f.id),
                        title=f.title,
                        severity=f.severity,
                        category=f.category,
                        cwe_id=f.cwe_id,
                        cve_id=f.cve_id,
                        status=str(getattr(f, "status", "CONFIRMED")),
                        asset_name=asset_name,
                        evidence_checksum=ev_checksum,
                        remediation_summary=f.remediation or ctrl_guidance,
                    )
                    matched_findings.append(mapped_dto)

            status = "FAIL" if matched_findings else "PASS"
            if status == "PASS":
                passed_count += 1
            else:
                failed_count += 1

            control_dtos.append(
                ComplianceControlDTO(
                    control_id=control_id,
                    title=ctrl_title,
                    description=ctrl_desc,
                    status=status,
                    mapped_findings_count=len(matched_findings),
                    affected_findings=matched_findings,
                    remediation_guidance=ctrl_guidance,
                )
            )

        total_controls = len(raw_controls)
        compliance_pct = (
            round((passed_count / total_controls) * 100.0, 1)
            if total_controls > 0
            else 100.0
        )

        framework_dto = ComplianceFrameworkDTO(
            id=meta["id"],
            name=meta["name"],
            version=meta["version"],
            description=meta["description"],
            total_controls=total_controls,
        )

        score_dto = ComplianceScoreResponse(
            framework_id=meta["id"],
            framework_name=meta["name"],
            framework_version=meta["version"],
            total_controls=total_controls,
            passed_controls=passed_count,
            failed_controls=failed_count,
            compliance_percentage=compliance_pct,
        )

        return framework_dto, control_dtos, score_dto
