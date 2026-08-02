"""Technology Stack Fingerprinting Engine.

Analyzes HTTP headers, server banners, security headers, HTML meta tags, DOM structures,
and script resource URLs to detect technologies powering target web applications.
"""

import re
import time
from typing import Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger
from app.domain.entities.discovery import (
    DetectedTechnology,
    SecurityHeaderStatus,
    TechCategory,
    TechnologyScanResult,
)
from app.infrastructure.discovery.ssrf_validator import is_safe_target_url

logger = get_logger("vulnova.tech_fingerprinter")

MAX_RESPONSE_BODY_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_TIMEOUT_SECONDS = 10.0

SECURITY_HEADERS_LIST: List[str] = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
]


class TechFingerprinter:
    """Modular rule-based Technology Stack Fingerprinting Engine."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout

    async def probe_and_fingerprint(self, target_url: str) -> TechnologyScanResult:
        """Send HTTP probe request and execute comprehensive fingerprint analysis."""
        clean_url = target_url.strip().rstrip("/")
        start_time = time.time()

        # Pre-validate safety of target URL via SSRF Egress Firewall
        is_safe, reason = is_safe_target_url(clean_url)
        if not is_safe:
            logger.warning(
                "tech_fingerprinter.unsafe_target_cancelled",
                target_url=clean_url,
                reason=reason,
            )
            return TechnologyScanResult(
                target_url=clean_url,
                status_code=None,
                duration_seconds=round(time.time() - start_time, 2),
            )

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers={"User-Agent": "Vulnova-AppSec-TechScanner/1.0"},
            ) as client:
                response = await client.get(clean_url)
                status_code = response.status_code

                # Cap body size
                raw_body = response.content[:MAX_RESPONSE_BODY_BYTES]
                html_text = raw_body.decode("utf-8", errors="ignore")

                # Convert headers to case-insensitive mapping
                headers = {k.lower(): v for k, v in response.headers.items()}

                result = self.analyze(
                    target_url=clean_url,
                    status_code=status_code,
                    headers=headers,
                    html_content=html_text,
                )
                result.duration_seconds = round(time.time() - start_time, 2)
                return result

        except Exception as e:
            logger.warning(
                "tech_fingerprinter.probe_failed",
                target_url=clean_url,
                error=str(e),
            )
            return TechnologyScanResult(
                target_url=clean_url,
                status_code=None,
                duration_seconds=round(time.time() - start_time, 2),
            )

    def analyze(
        self,
        target_url: str,
        status_code: int,
        headers: Dict[str, str],
        html_content: str,
    ) -> TechnologyScanResult:
        """Analyze headers and HTML content to identify technology stack signatures."""
        detected_dict: Dict[Tuple[str, TechCategory], DetectedTechnology] = {}

        def _add_tech(
            name: str,
            category: TechCategory,
            matched_by: str,
            version: Optional[str] = None,
            confidence: int = 100,
        ) -> None:
            key = (name, category)
            if key not in detected_dict:
                detected_dict[key] = DetectedTechnology(
                    name=name,
                    category=category,
                    version=version,
                    confidence=confidence,
                    matched_by=[matched_by],
                )
            else:
                existing = detected_dict[key]
                if matched_by not in existing.matched_by:
                    existing.matched_by.append(matched_by)
                if not existing.version and version:
                    existing.version = version

        # 1. Header Analysis
        server_header = headers.get("server", "")
        if "nginx" in server_header.lower():
            ver = self._extract_version(r"nginx/([\d.]+)", server_header)
            _add_tech("Nginx", TechCategory.WEB_SERVER, "header:Server", version=ver)
        if "apache" in server_header.lower():
            ver = self._extract_version(r"apache/([\d.]+)", server_header)
            _add_tech("Apache", TechCategory.WEB_SERVER, "header:Server", version=ver)
        if "microsoft-iis" in server_header.lower():
            ver = self._extract_version(r"iis/([\d.]+)", server_header)
            _add_tech(
                "Microsoft IIS", TechCategory.WEB_SERVER, "header:Server", version=ver
            )

        x_powered_by = headers.get("x-powered-by", "")
        if "express" in x_powered_by.lower():
            _add_tech("Express", TechCategory.BACKEND_FRAMEWORK, "header:X-Powered-By")
        if "next.js" in x_powered_by.lower():
            ver = self._extract_version(r"next\.js/([\d.]+)", x_powered_by)
            _add_tech(
                "Next.js",
                TechCategory.FRONTEND_FRAMEWORK,
                "header:X-Powered-By",
                version=ver,
            )
        if "php" in x_powered_by.lower():
            ver = self._extract_version(r"php/([\d.]+)", x_powered_by)
            _add_tech(
                "PHP",
                TechCategory.BACKEND_FRAMEWORK,
                "header:X-Powered-By",
                version=ver,
            )
        if "asp.net" in x_powered_by.lower():
            _add_tech("ASP.NET", TechCategory.BACKEND_FRAMEWORK, "header:X-Powered-By")

        if "cf-ray" in headers or "cloudflare" in server_header.lower():
            _add_tech("Cloudflare", TechCategory.CDN_PROXY, "header:CF-Ray/Server")
        if "x-served-by" in headers and "cache-" in headers.get("x-served-by", ""):
            _add_tech("Fastly", TechCategory.CDN_PROXY, "header:X-Served-By")
        if "via" in headers and "varnish" in headers.get("via", "").lower():
            _add_tech("Varnish", TechCategory.CDN_PROXY, "header:Via")

        # 2. Security Headers Audit
        sec_headers: List[SecurityHeaderStatus] = []
        for sec_h in SECURITY_HEADERS_LIST:
            val = headers.get(sec_h.lower())
            sec_headers.append(
                SecurityHeaderStatus(
                    header_name=sec_h,
                    present=val is not None,
                    value=val,
                )
            )

        # 3. HTML DOM & Meta Tag Fingerprinting
        soup = BeautifulSoup(html_content, "html.parser")

        # Generator meta tags
        for meta in soup.find_all("meta"):
            if isinstance(meta, Tag):
                name_attr = str(meta.get("name") or "").lower()
                content_attr = str(meta.get("content") or "")
                if name_attr == "generator":
                    if "wordpress" in content_attr.lower():
                        ver = self._extract_version(
                            r"wordpress\s*([\d.]+)", content_attr
                        )
                        _add_tech(
                            "WordPress", TechCategory.CMS, "meta:generator", version=ver
                        )
                    elif "drupal" in content_attr.lower():
                        ver = self._extract_version(r"drupal\s*([\d.]+)", content_attr)
                        _add_tech(
                            "Drupal", TechCategory.CMS, "meta:generator", version=ver
                        )
                    elif "next.js" in content_attr.lower():
                        _add_tech(
                            "Next.js", TechCategory.FRONTEND_FRAMEWORK, "meta:generator"
                        )

        # DOM structure markers
        if soup.find(id="__next") or soup.find("script", id="__NEXT_DATA__"):
            _add_tech("Next.js", TechCategory.FRONTEND_FRAMEWORK, "dom:__next")
            _add_tech("React", TechCategory.FRONTEND_FRAMEWORK, "dom:__next_dependency")

        if soup.find(id="__nuxt") or soup.find("script", id="__NUXT__"):
            _add_tech("Nuxt.js", TechCategory.FRONTEND_FRAMEWORK, "dom:__nuxt")
            _add_tech(
                "Vue.js", TechCategory.FRONTEND_FRAMEWORK, "dom:__nuxt_dependency"
            )

        if soup.find(attrs={"ng-version": True}):
            tag = soup.find(attrs={"ng-version": True})
            ver_attr = str(tag.get("ng-version")) if isinstance(tag, Tag) else None
            _add_tech(
                "Angular",
                TechCategory.FRONTEND_FRAMEWORK,
                "dom:ng-version",
                version=ver_attr,
            )

        if soup.find(attrs={"data-reactroot": True}):
            _add_tech("React", TechCategory.FRONTEND_FRAMEWORK, "dom:data-reactroot")

        if "wp-content" in html_content or "wp-includes" in html_content:
            _add_tech("WordPress", TechCategory.CMS, "dom:wp-content")

        # 4. Script Src Path Analysis
        for script in soup.find_all("script", src=True):
            if isinstance(script, Tag) and script.get("src"):
                src_url = str(script["src"]).lower()
                if "react" in src_url:
                    ver = self._extract_version(
                        r"react@?([\d.]+)", src_url
                    ) or self._extract_version(r"react-([\d.]+)", src_url)
                    _add_tech(
                        "React",
                        TechCategory.FRONTEND_FRAMEWORK,
                        "script:src",
                        version=ver,
                    )
                if "vue" in src_url:
                    ver = self._extract_version(
                        r"vue@?([\d.]+)", src_url
                    ) or self._extract_version(r"vue-([\d.]+)", src_url)
                    _add_tech(
                        "Vue.js",
                        TechCategory.FRONTEND_FRAMEWORK,
                        "script:src",
                        version=ver,
                    )
                if "jquery" in src_url:
                    ver = self._extract_version(
                        r"jquery-([\d.]+)", src_url
                    ) or self._extract_version(r"jquery/([\d.]+)", src_url)
                    _add_tech(
                        "jQuery",
                        TechCategory.JAVASCRIPT_LIBRARY,
                        "script:src",
                        version=ver,
                    )
                if "bootstrap" in src_url:
                    ver = self._extract_version(
                        r"bootstrap/([\d.]+)", src_url
                    ) or self._extract_version(r"bootstrap-([\d.]+)", src_url)
                    _add_tech(
                        "Bootstrap",
                        TechCategory.JAVASCRIPT_LIBRARY,
                        "script:src",
                        version=ver,
                    )

        return TechnologyScanResult(
            target_url=target_url,
            status_code=status_code,
            detected_technologies=list(detected_dict.values()),
            security_headers=sec_headers,
        )

    def _extract_version(self, pattern: str, text: str) -> Optional[str]:
        """Extract version string using regex pattern match."""
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            return match.group(1).strip()
        return None
