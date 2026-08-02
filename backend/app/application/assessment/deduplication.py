"""Finding Deduplication Engine merging redundant vulnerabilities across plugins and targets."""

import hashlib
from typing import Dict, List
from uuid import UUID

from app.core.logging import get_logger
from app.domain.entities.assessment import Finding

logger = get_logger("vulnova.deduplication")


class FindingDeduplicator:
    """Engine identifying duplicate findings and linking canonical primary findings."""

    def compute_signature_hash(self, finding: Finding) -> str:
        """Compute deterministic deduplication signature hash for a finding."""
        # Extract target endpoint or vulnerable parameter if available in evidence
        evidence = finding.evidence or {}
        target_endpoint = (
            evidence.get("probe_url")
            or evidence.get("target_url")
            or evidence.get("exposed_url")
            or evidence.get("host")
            or finding.title
        )
        param = evidence.get("vulnerable_parameter") or ""

        signature_raw = (
            f"{finding.organization_id}:"
            f"{finding.plugin_id}:"
            f"{finding.cwe_id or finding.category.value}:"
            f"{target_endpoint}:"
            f"{param}"
        )
        return hashlib.sha256(signature_raw.encode("utf-8")).hexdigest()

    def deduplicate_findings(self, findings: List[Finding]) -> List[Finding]:
        """Process findings, computing deduplication hashes and linking duplicate instances to canonical findings."""
        hash_to_canonical: Dict[str, UUID] = {}

        for finding in findings:
            sig_hash = self.compute_signature_hash(finding)
            finding.deduplication_hash = sig_hash

            if sig_hash in hash_to_canonical:
                # Mark as duplicate and link canonical finding ID
                finding.is_duplicate = True
                finding.canonical_finding_id = hash_to_canonical[sig_hash]
                logger.info(
                    "deduplication.duplicate_found",
                    finding_id=str(finding.id),
                    canonical_id=str(hash_to_canonical[sig_hash]),
                    hash=sig_hash[:8],
                )
            else:
                # Primary canonical finding
                finding.is_duplicate = False
                finding.canonical_finding_id = None
                hash_to_canonical[sig_hash] = finding.id

        return findings
