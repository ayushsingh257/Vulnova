"""Application Service for Developer Technical Remediation Exports (JSON, CSV, Markdown)."""

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from typing import AsyncGenerator, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.finding.finding_intelligence_service import (
    FindingIntelligenceService,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.user import UserModel

logger = structlog.get_logger(__name__)


def sanitize_sensitive_data(val: Optional[str]) -> str:
    """Sanitize secret tokens, authorization keys, or passwords in evidence strings."""
    if not val:
        return ""
    # Basic token / authorization header masking
    lines = val.split("\n")
    sanitized = []
    for line in lines:
        lower = line.lower()
        if "authorization: bearer" in lower or "authorization: basic" in lower:
            parts = line.split(":", 1)
            sanitized.append(f"{parts[0]}: [REDACTED_AUTH_TOKEN]")
        elif "cookie:" in lower and ("session" in lower or "token" in lower):
            parts = line.split(":", 1)
            sanitized.append(f"{parts[0]}: [REDACTED_SESSION_COOKIE]")
        else:
            sanitized.append(line)
    return "\n".join(sanitized)


class DeveloperExportService:
    """Service providing memory-efficient streaming exports of vulnerability intelligence, evidence, attack paths, and AI fix guidance."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service
        self.intelligence_service = FindingIntelligenceService(session)

    async def _stream_findings(
        self, organization_id: UUID, batch_size: int = 50
    ) -> AsyncGenerator[SecurityFindingModel, None]:
        """Stream findings from database in memory-efficient chunks."""
        offset = 0
        while True:
            stmt = (
                select(SecurityFindingModel)
                .where(
                    SecurityFindingModel.organization_id == organization_id,
                    SecurityFindingModel.is_duplicate.is_(False),
                )
                .order_by(SecurityFindingModel.created_at.desc())
                .offset(offset)
                .limit(batch_size)
            )
            res = await self.session.execute(stmt)
            findings = list(res.scalars().all())
            if not findings:
                break
            for finding in findings:
                yield finding
            if len(findings) < batch_size:
                break
            offset += batch_size

    async def export_csv_stream(
        self, current_user: UserModel
    ) -> AsyncGenerator[str, None]:
        """Stream bulk findings formatted as CSV rows with zero memory bloat."""
        # Yield CSV Header
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Finding ID",
                "Title",
                "Severity",
                "Category",
                "CVSS Score",
                "EPSS Score",
                "CVE ID",
                "CWE ID",
                "Risk Score",
                "Triage Status",
                "Created At",
            ]
        )
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

        count = 0
        async for finding in self._stream_findings(current_user.organization_id):
            epss_val = 0.0
            if finding.epss_json and isinstance(finding.epss_json, dict):
                epss_val = float(finding.epss_json.get("epss_score", 0.0))

            finding_status = str(getattr(finding, "status", "CONFIRMED"))

            writer.writerow(
                [
                    str(finding.id),
                    finding.title,
                    str(finding.severity),
                    str(finding.category),
                    float(finding.risk_score or 0.0),
                    epss_val,
                    finding.cve_id or "N/A",
                    finding.cwe_id or "N/A",
                    float(finding.risk_score or 0.0),
                    finding_status,
                    (
                        finding.created_at.isoformat()
                        if finding.created_at
                        else datetime.now(timezone.utc).isoformat()
                    ),
                ]
            )
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)
            count += 1

        # Record audit event
        await self.audit_log_service.record_event(
            organization_id=current_user.organization_id,
            actor_user_id=current_user.id,
            action="report.exported",
            resource_type="report_export",
            resource_id="bulk_csv",
            details={
                "format": "csv",
                "export_type": "bulk_findings",
                "findings_count": count,
            },
        )

    async def export_json_stream(
        self, current_user: UserModel
    ) -> AsyncGenerator[str, None]:
        """Stream bulk findings formatted as a JSON array."""
        yield "[\n"
        first = True
        count = 0

        async for finding in self._stream_findings(current_user.organization_id):
            if not first:
                yield ",\n"
            first = False

            epss_val = 0.0
            if finding.epss_json and isinstance(finding.epss_json, dict):
                epss_val = float(finding.epss_json.get("epss_score", 0.0))

            finding_status = str(getattr(finding, "status", "CONFIRMED"))

            item = {
                "id": str(finding.id),
                "organization_id": str(finding.organization_id),
                "title": finding.title,
                "description": finding.description,
                "severity": str(finding.severity),
                "category": str(finding.category),
                "cve_id": finding.cve_id,
                "cwe_id": finding.cwe_id,
                "cvss_score": float(finding.risk_score or 0.0),
                "epss_score": epss_val,
                "status": finding_status,
                "created_at": (
                    finding.created_at.isoformat()
                    if finding.created_at
                    else datetime.now(timezone.utc).isoformat()
                ),
            }
            yield json.dumps(item, indent=2)
            count += 1

        yield "\n]"

        # Record audit event
        await self.audit_log_service.record_event(
            organization_id=current_user.organization_id,
            actor_user_id=current_user.id,
            action="report.exported",
            resource_type="report_export",
            resource_id="bulk_json",
            details={
                "format": "json",
                "export_type": "bulk_findings",
                "findings_count": count,
            },
        )

    async def export_markdown_stream(
        self, current_user: UserModel
    ) -> AsyncGenerator[str, None]:
        """Stream bulk findings formatted as a Markdown document."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        header = f"""# Vulnova Developer Technical Security Report

**Generated At**: {now_str}
**Organization ID**: `{current_user.organization_id}`
**Export Scope**: All Active Findings

---

## Findings Overview

"""
        yield header
        count = 0

        async for finding in self._stream_findings(current_user.organization_id):
            count += 1
            epss_val = 0.0
            if finding.epss_json and isinstance(finding.epss_json, dict):
                epss_val = float(finding.epss_json.get("epss_score", 0.0))

            finding_status = str(getattr(finding, "status", "CONFIRMED"))

            section = f"""### {count}. [{finding.severity}] {finding.title}

- **Finding ID**: `{finding.id}`
- **Category**: {finding.category}
- **CVSS Score**: {finding.risk_score or 0.0} | **EPSS**: {epss_val:.4f}
- **CVE**: {finding.cve_id or 'N/A'} | **CWE**: {finding.cwe_id or 'N/A'}
- **Triage Status**: `{finding_status}`

#### Description
{finding.description or 'No description available.'}

---

"""
            yield section

        await self.audit_log_service.record_event(
            organization_id=current_user.organization_id,
            actor_user_id=current_user.id,
            action="report.exported",
            resource_type="report_export",
            resource_id="bulk_markdown",
            details={
                "format": "markdown",
                "export_type": "bulk_findings",
                "findings_count": count,
            },
        )

    async def export_single_finding(
        self, current_user: UserModel, finding_id: UUID, export_format: str
    ) -> Tuple[str, str, str]:
        """Generate a single vulnerability export package (JSON, CSV, or Markdown)."""
        intel = await self.intelligence_service.get_finding_details(
            current_user.organization_id, finding_id
        )
        evidence = await self.intelligence_service.get_finding_evidence(
            current_user.organization_id, finding_id
        )
        attack_paths = await self.intelligence_service.get_finding_attack_paths(
            current_user.organization_id, finding_id
        )
        remediation = await self.intelligence_service.get_finding_remediation(
            current_user.organization_id, finding_id
        )

        fmt = export_format.lower().strip()

        # Audit log trigger
        await self.audit_log_service.record_event(
            organization_id=current_user.organization_id,
            actor_user_id=current_user.id,
            action="vulnerability.exported",
            resource_type="security_finding",
            resource_id=str(finding_id),
            details={
                "format": fmt,
                "finding_title": intel.title,
                "severity": intel.severity,
            },
        )

        if fmt == "json":
            payload = {
                "vulnerability": intel.model_dump(),
                "evidence_artifacts": [e.model_dump() for e in evidence.evidence_items],
                "attack_paths": [p.model_dump() for p in attack_paths.nodes],
                "remediation": remediation.model_dump(),
                "exported_at": datetime.now(timezone.utc).isoformat(),
            }
            content = json.dumps(payload, indent=2)
            filename = f"Vulnova_Finding_{str(finding_id)[:8]}.json"
            return content, "application/json", filename

        elif fmt == "csv":
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "Finding ID",
                    "Title",
                    "Severity",
                    "Category",
                    "CVSS Score",
                    "EPSS Score",
                    "CVE ID",
                    "CWE ID",
                    "Target Asset",
                    "Status",
                    "Remediation Steps Count",
                ]
            )
            writer.writerow(
                [
                    intel.id,
                    intel.title,
                    intel.severity,
                    intel.category,
                    intel.cvss.base_score,
                    intel.epss.epss_score,
                    intel.cve_id or "N/A",
                    intel.cwe_id or "N/A",
                    intel.scan_origin.target_name or "N/A",
                    intel.triage_status,
                    len(remediation.steps),
                ]
            )
            content = output.getvalue()
            filename = f"Vulnova_Finding_{str(finding_id)[:8]}.csv"
            return content, "text/csv", filename

        else:  # markdown
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            lines = [
                f"# Vulnerability Technical Report: {intel.title}",
                "",
                f"**Finding ID**: `{intel.id}`  ",
                f"**Severity**: `{intel.severity}` | **CVSS Base Score**: `{intel.cvss.base_score}`  ",
                f"**CVE**: `{intel.cve_id or 'N/A'}` | **CWE**: `{intel.cwe_id or 'N/A'}`  ",
                f"**Target Asset**: `{intel.scan_origin.target_name or 'N/A'}`  ",
                f"**Report Generated**: `{now_str}`  ",
                "",
                "---",
                "",
                "## 1. Finding Summary",
                intel.description or "No description provided.",
                "",
                "## 2. Risk Details",
                f"- **Category**: {intel.category}",
                f"- **CVSS Vector**: `{intel.cvss.vector_string or 'N/A'}`",
                f"- **EPSS Probability**: `{intel.epss.epss_score:.4f}` ({intel.epss.percentile * 100:.1f}th percentile)",
                f"- **Triage Status**: `{intel.triage_status}`",
                "",
                "## 3. Evidence & Proof Artifacts",
            ]

            if evidence.evidence_items:
                for idx, ev in enumerate(evidence.evidence_items, 1):
                    sanitized_payload = sanitize_sensitive_data(
                        ev.raw_payload
                        if hasattr(ev, "raw_payload")
                        else (ev.storage_path or "")
                    )
                    lines.extend(
                        [
                            f"### Proof Artifact #{idx}: {ev.type_label} (`{ev.artifact_type}`)",
                            f"**SHA-256 Checksum**: `{ev.checksum or 'N/A'}`",
                            "```http",
                            sanitized_payload or "No raw payload stored.",
                            "```",
                            "",
                        ]
                    )
            else:
                lines.append("No proof evidence artifacts attached.")

            lines.extend(
                [
                    "## 4. Attack Path Sequence",
                ]
            )

            if attack_paths.nodes:
                lines.append(f"### {attack_paths.title}")
                lines.append(attack_paths.attack_summary)
                for step in attack_paths.nodes:
                    lines.append(
                        f"{step.sequence_number}. **{step.vulnerability_title}** ({step.asset_name} - {step.relationship})"
                    )
                    lines.append(f"   - *Impact*: `{step.risk_impact}`")
                lines.append("")
            else:
                lines.append("No attack path graph generated.")

            lines.extend(
                [
                    "## 5. Recommended AI Fix & Remediation Plan",
                ]
            )

            if remediation.title:
                lines.append(f"### {remediation.title}")
                lines.append(f"**Summary**: {remediation.summary}")
                lines.append(f"**Explanation**: {remediation.explanation}")
                lines.append("")
                if remediation.patch_suggestions:
                    lines.append("#### Suggested Code Patches")
                    for patch in remediation.patch_suggestions:
                        lines.extend(
                            [
                                f"File: `{patch.file_path or 'N/A'}` ({patch.language})",
                                "```diff",
                                patch.patch_code or patch.explanation or "",
                                "```",
                                "",
                            ]
                        )
                if remediation.steps:
                    lines.append("#### Remediation Steps")
                    for st in remediation.steps:
                        lines.append(
                            f"{st.sequence_number}. **{st.title}**: {st.description}"
                        )
                    lines.append("")
                if remediation.verification_steps:
                    lines.append("#### Verification Steps")
                    for v_step in remediation.verification_steps:
                        lines.append(f"- {v_step}")
                    lines.append("")
            else:
                lines.append("No AI remediation plan generated.")

            content = "\n".join(lines)
            filename = f"Vulnova_Finding_{str(finding_id)[:8]}.md"
            return content, "text/markdown", filename
