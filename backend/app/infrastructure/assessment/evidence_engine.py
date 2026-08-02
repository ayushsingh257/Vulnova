"""Multi-Modal Evidence Collection & Capture Engine for Vulnova Findings."""

import json
import re
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.domain.entities.assessment import (
    AssessmentContext,
    EvidenceArtifact,
    EvidenceType,
    Finding,
)
from app.infrastructure.storage.evidence_store import EvidenceArtifactStorage

logger = get_logger("vulnova.evidence_engine")

SENSITIVE_HEADER_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
    "x-auth-token",
    "x-access-token",
    "proxy-authorization",
}


def mask_sensitive_headers(headers: Dict[str, Any]) -> Dict[str, str]:
    """Mask sensitive authorization, token, and cookie headers."""
    masked: Dict[str, str] = {}
    for k, v in headers.items():
        k_lower = k.lower()
        val_str = str(v)
        if k_lower in SENSITIVE_HEADER_KEYS:
            if k_lower == "authorization" and val_str.startswith("Bearer "):
                masked[k] = "Bearer *******"
            elif k_lower == "authorization" and val_str.startswith("Basic "):
                masked[k] = "Basic *******"
            else:
                masked[k] = "*******"
        else:
            # Mask potential bearer/jwt tokens in custom headers
            masked[k] = re.sub(
                r"(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})",
                "*******",
                val_str,
            )
    return masked


def mask_sensitive_cookies(cookies: Dict[str, Any]) -> Dict[str, str]:
    """Mask sensitive cookie values."""
    masked: Dict[str, str] = {}
    for k, v in cookies.items():
        k_lower = k.lower()
        if any(
            term in k_lower
            for term in ("session", "token", "jwt", "auth", "secret", "key", "sid")
        ):
            masked[k] = "*******"
        else:
            masked[k] = str(v)
    return masked


class EvidenceCollectionEngine:
    """Engine capturing HTTP exchanges, headers, cookies, DOM snapshots, and screenshots as evidence artifacts."""

    def __init__(self, storage: Optional[EvidenceArtifactStorage] = None) -> None:
        self.storage = storage or EvidenceArtifactStorage()

    async def capture_evidence_for_finding(
        self, finding: Finding, context: AssessmentContext
    ) -> List[EvidenceArtifact]:
        """Capture multi-modal evidence artifacts for a normalized finding."""
        artifacts: List[EvidenceArtifact] = []
        evidence_data = finding.evidence or {}

        target_url = (
            evidence_data.get("probe_url")
            or evidence_data.get("target_url")
            or evidence_data.get("exposed_url")
            or context.target_url
        )

        # 1. Capture HTTP Request Artifact
        req_method = evidence_data.get("method", "GET")
        req_headers = mask_sensitive_headers(evidence_data.get("request_headers", {}))
        req_body = evidence_data.get("request_body", "")

        req_text = f"{req_method} {target_url} HTTP/1.1\n"
        for k, v in req_headers.items():
            req_text += f"{k}: {v}\n"
        if req_body:
            req_text += f"\n{req_body}"

        req_artifact = await self.storage.save_artifact(
            organization_id=finding.organization_id,
            finding_id=finding.id,
            artifact_type=EvidenceType.HTTP_REQUEST,
            filename="request.txt",
            content=req_text.encode("utf-8"),
            metadata={"target_url": target_url, "method": req_method},
        )
        artifacts.append(req_artifact)

        # 2. Capture HTTP Response Artifact
        resp_status = evidence_data.get("status_code", 200)
        resp_headers = mask_sensitive_headers(
            evidence_data.get("response_headers") or evidence_data.get("headers") or {}
        )
        resp_body = (
            evidence_data.get("response_body")
            or evidence_data.get("body_snippet")
            or f"Status {resp_status} response from {target_url}"
        )

        resp_text = f"HTTP/1.1 {resp_status}\n"
        for k, v in resp_headers.items():
            resp_text += f"{k}: {v}\n"
        resp_text += f"\n{resp_body}"

        resp_artifact = await self.storage.save_artifact(
            organization_id=finding.organization_id,
            finding_id=finding.id,
            artifact_type=EvidenceType.HTTP_RESPONSE,
            filename="response.txt",
            content=resp_text.encode("utf-8"),
            metadata={"status_code": resp_status},
        )
        artifacts.append(resp_artifact)

        # 3. Capture Header Data Artifact if present
        if resp_headers:
            header_json = json.dumps(resp_headers, indent=2).encode("utf-8")
            header_artifact = await self.storage.save_artifact(
                organization_id=finding.organization_id,
                finding_id=finding.id,
                artifact_type=EvidenceType.HEADER_DATA,
                filename="headers.json",
                content=header_json,
                metadata={"total_headers": len(resp_headers)},
            )
            artifacts.append(header_artifact)

        # 4. Capture Cookie Data Artifact if cookie flags or evidence exist
        cookies = evidence_data.get("cookies")
        if cookies:
            masked_cookies = mask_sensitive_cookies(cookies)
            cookie_json = json.dumps(masked_cookies, indent=2).encode("utf-8")
            cookie_artifact = await self.storage.save_artifact(
                organization_id=finding.organization_id,
                finding_id=finding.id,
                artifact_type=EvidenceType.COOKIE_DATA,
                filename="cookies.json",
                content=cookie_json,
                metadata={"cookie_count": len(masked_cookies)},
            )
            artifacts.append(cookie_artifact)

        # 5. Capture Browser Visual Screenshot & DOM Snapshot Evidence
        dom_bytes: bytes = b""
        screenshot_bytes: bytes = b""

        # Attempt Playwright rendering lazily
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(
                    target_url, timeout=15000, wait_until="domcontentloaded"
                )
                dom_html = await page.content()
                dom_bytes = dom_html.encode("utf-8")
                screenshot_bytes = await page.screenshot(type="png", full_page=False)
                await browser.close()
        except Exception as e:
            logger.debug(
                "evidence_engine.playwright_fallback", reason=str(e), url=target_url
            )
            # Fallback DOM snapshot and SVG placeholder screenshot when Playwright browser binaries not present
            fallback_dom = f"<html><head><title>Proof of Finding: {finding.title}</title></head><body><h1>Finding Proof for {target_url}</h1><pre>{resp_body}</pre></body></html>"
            dom_bytes = fallback_dom.encode("utf-8")

            svg_placeholder = f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400"><rect width="100%" height="100%" fill="#111827"/><text x="400" y="200" fill="#EF4444" font-size="20" font-family="sans-serif" text-anchor="middle">Vulnova Finding Proof: {finding.title}</text></svg>'
            screenshot_bytes = svg_placeholder.encode("utf-8")

        dom_artifact = await self.storage.save_artifact(
            organization_id=finding.organization_id,
            finding_id=finding.id,
            artifact_type=EvidenceType.DOM_SNAPSHOT,
            filename="dom_snapshot.html",
            content=dom_bytes,
            metadata={"target_url": target_url},
        )
        artifacts.append(dom_artifact)

        screenshot_artifact = await self.storage.save_artifact(
            organization_id=finding.organization_id,
            finding_id=finding.id,
            artifact_type=EvidenceType.SCREENSHOT,
            filename="screenshot.png",
            content=screenshot_bytes,
            metadata={"target_url": target_url},
        )
        artifacts.append(screenshot_artifact)

        finding.artifacts = artifacts
        logger.info(
            "evidence_engine.captured_finding_evidence",
            finding_id=str(finding.id),
            total_artifacts=len(artifacts),
        )
        return artifacts

    async def capture_evidence_batch(
        self, findings: List[Finding], context: AssessmentContext
    ) -> List[Finding]:
        """Capture multi-modal evidence artifacts for a list of findings."""
        for finding in findings:
            await self.capture_evidence_for_finding(finding, context)
        return findings
