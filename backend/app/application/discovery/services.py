import asyncio
import time
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.discovery.dto import (
    CrawlRequest,
    CrawlResponse,
    DetectedTechnologyDTO,
    DiscoveredFormDTO,
    DiscoveredNetworkRequestDTO,
    DiscoveredScriptDTO,
    DiscoveredSubdomainDTO,
    DiscoveredURLDTO,
    DNSRecordDTO,
    IPAddressInfoDTO,
    SecurityHeaderDTO,
    SubdomainScanRequest,
    SubdomainScanResponse,
    TechnologyScanRequest,
    TechnologyScanResponse,
)
from app.core.exceptions import ValidationException
from app.core.logging import get_logger
from app.domain.entities.discovery import CrawlResult, CrawlScope
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.discovery.crawler import AsyncWebCrawler
from app.infrastructure.discovery.ct_logs_client import CTLogsClient
from app.infrastructure.discovery.dns_resolver import AsyncDNSResolver
from app.infrastructure.discovery.playwright_renderer import (
    PlaywrightUnavailableException,
    SPADynamicCrawler,
)
from app.infrastructure.discovery.ssrf_validator import (
    extract_base_domain,
    is_safe_target_url,
)
from app.infrastructure.discovery.tech_fingerprinter import TechFingerprinter

logger = get_logger("vulnova.discovery")


class DiscoveryService:
    """Application service for managing asset surface discovery and web crawling."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditLogService(session)

    async def crawl_target(
        self, req: CrawlRequest, current_user: UserModel
    ) -> CrawlResponse:
        """Execute an async web crawl on an explicitly approved target URL.

        Enforces SSRF checks, domain scope limits, safety caps, and audit logging.
        Supports optional headless Chromium Playwright rendering with graceful static fallback.
        """
        target_str = str(req.target_url).rstrip("/")

        # 1. Pre-validate SSRF & Egress Firewall Safety
        is_safe, reason = is_safe_target_url(target_str)
        if not is_safe:
            logger.warning(
                "discovery.crawl_rejected_unsafe_target",
                target_url=target_str,
                reason=reason,
                user_id=str(current_user.id),
                org_id=str(current_user.organization_id),
            )
            await self.audit_service.record_event(
                organization_id=current_user.organization_id,
                action="discovery.crawl_rejected",
                resource_type="target",
                resource_id=target_str,
                actor_user_id=current_user.id,
                details={"target_url": target_str, "reason": reason},
            )
            raise ValidationException(f"Target URL is prohibited: {reason}")

        base_domain = extract_base_domain(target_str)

        # 2. Record Crawl Started Audit Event
        await self.audit_service.record_event(
            organization_id=current_user.organization_id,
            action="discovery.crawl_started",
            resource_type="target",
            resource_id=target_str,
            actor_user_id=current_user.id,
            details={
                "target_url": target_str,
                "max_depth": req.max_depth,
                "max_pages": req.max_pages,
                "render_js": req.render_js,
            },
        )

        # 3. Instantiate CrawlScope
        scope = CrawlScope(
            base_url=target_str,
            allowed_domain=base_domain,
            allow_subdomains=req.allow_subdomains,
            max_depth=req.max_depth,
            max_pages=req.max_pages,
            concurrency_limit=req.concurrency_limit,
        )

        crawl_result: CrawlResult
        render_mode = "static"

        # 4. Execute Playwright Dynamic Crawler or Fallback to Static Crawler
        if req.render_js:
            try:
                spa_crawler = SPADynamicCrawler(scope)
                crawl_result = await spa_crawler.crawl()
                render_mode = "playwright_spa"
            except PlaywrightUnavailableException as p_err:
                logger.warning(
                    "discovery.playwright_unavailable_falling_back_to_static",
                    target_url=target_str,
                    error=str(p_err),
                )
                static_crawler = AsyncWebCrawler(scope)
                crawl_result = await static_crawler.crawl()
                render_mode = "static_fallback"
        else:
            static_crawler = AsyncWebCrawler(scope)
            crawl_result = await static_crawler.crawl()

        # 5. Map Domain CrawlResult to Response DTOs
        urls_dto = [
            DiscoveredURLDTO(
                url=u.url,
                method=u.method,
                depth=u.depth,
                status_code=u.status_code,
                content_type=u.content_type,
                title=u.title,
            )
            for u in crawl_result.discovered_urls
        ]
        forms_dto = [
            DiscoveredFormDTO(action_url=f.action_url, method=f.method, inputs=f.inputs)
            for f in crawl_result.discovered_forms
        ]
        scripts_dto = [
            DiscoveredScriptDTO(src_url=s.src_url, is_external=s.is_external)
            for s in crawl_result.discovered_scripts
        ]
        network_dto = [
            DiscoveredNetworkRequestDTO(
                url=nr.url, method=nr.method, resource_type=nr.resource_type
            )
            for nr in crawl_result.network_requests
        ]

        # 6. Record Crawl Completed Audit Event
        await self.audit_service.record_event(
            organization_id=current_user.organization_id,
            action="discovery.crawl_completed",
            resource_type="target",
            resource_id=target_str,
            actor_user_id=current_user.id,
            details={
                "target_url": target_str,
                "pages_crawled": crawl_result.total_pages_crawled,
                "discovered_links": len(urls_dto),
                "discovered_forms": len(forms_dto),
                "network_requests": len(network_dto),
                "render_mode": render_mode,
                "is_spa": crawl_result.is_spa,
                "duration_seconds": crawl_result.duration_seconds,
            },
        )

        return CrawlResponse(
            target_url=crawl_result.target_url,
            total_pages_crawled=crawl_result.total_pages_crawled,
            discovered_urls=urls_dto,
            discovered_forms=forms_dto,
            discovered_scripts=scripts_dto,
            network_requests=network_dto,
            is_spa=crawl_result.is_spa,
            duration_seconds=crawl_result.duration_seconds,
        )

    async def discover_subdomains(
        self, req: SubdomainScanRequest, current_user: UserModel
    ) -> SubdomainScanResponse:
        """Execute a Subdomain & DNS Intelligence discovery scan on a target domain.

        Queries Certificate Transparency logs and resolves A, AAAA, CNAME, MX, NS, and TXT DNS records.
        Classifies IP findings into PUBLIC, PRIVATE, LOOPBACK for enterprise ASM intelligence.
        """
        start_time = time.time()
        base_domain = extract_base_domain(req.target_domain)

        # 1. Record Subdomain Scan Started Audit Event
        await self.audit_service.record_event(
            organization_id=current_user.organization_id,
            action="discovery.subdomain_scan_started",
            resource_type="domain",
            resource_id=base_domain,
            actor_user_id=current_user.id,
            details={
                "target_domain": base_domain,
                "include_ct_logs": req.include_ct_logs,
                "resolve_dns": req.resolve_dns,
            },
        )

        # 2. Passive Certificate Transparency Discovery
        candidate_subdomains: List[str] = [base_domain]
        if req.include_ct_logs:
            ct_client = CTLogsClient()
            ct_subdomains = await ct_client.search_subdomains(base_domain)
            candidate_subdomains = sorted(
                list(set(candidate_subdomains + ct_subdomains))
            )

        discovered_list: List[DiscoveredSubdomainDTO] = []

        # 3. Async DNS Record Enumeration
        if req.resolve_dns:
            resolver = AsyncDNSResolver()
            tasks = [resolver.resolve_subdomain(sub) for sub in candidate_subdomains]
            resolution_results = await asyncio.gather(*tasks, return_exceptions=True)

            for raw_res in resolution_results:
                if isinstance(raw_res, dict):
                    ips_dto = [
                        IPAddressInfoDTO(
                            value=ip.value,
                            classification=ip.classification,
                            is_internal=ip.is_internal,
                            is_egress_safe=ip.is_egress_safe,
                        )
                        for ip in raw_res.get("ip_addresses", [])
                    ]
                    dns_dto = [
                        DNSRecordDTO(
                            record_type=rec.record_type.value,
                            name=rec.name,
                            value=rec.value,
                            ttl=rec.ttl,
                        )
                        for rec in raw_res.get("dns_records", [])
                    ]

                    discovered_list.append(
                        DiscoveredSubdomainDTO(
                            subdomain=raw_res["subdomain"],
                            ip_addresses=ips_dto,
                            cname_aliases=raw_res.get("cname_aliases", []),
                            dns_records=dns_dto,
                            sources=["ct_logs" if req.include_ct_logs else "input"],
                        )
                    )
        else:
            for sub in candidate_subdomains:
                discovered_list.append(
                    DiscoveredSubdomainDTO(
                        subdomain=sub,
                        ip_addresses=[],
                        cname_aliases=[],
                        dns_records=[],
                        sources=["ct_logs" if req.include_ct_logs else "input"],
                    )
                )

        duration = round(time.time() - start_time, 2)

        # 4. Record Subdomain Scan Completed Audit Event
        await self.audit_service.record_event(
            organization_id=current_user.organization_id,
            action="discovery.subdomain_scan_completed",
            resource_type="domain",
            resource_id=base_domain,
            actor_user_id=current_user.id,
            details={
                "target_domain": base_domain,
                "total_subdomains": len(discovered_list),
                "duration_seconds": duration,
            },
        )

        return SubdomainScanResponse(
            target_domain=base_domain,
            total_subdomains=len(discovered_list),
            discovered_subdomains=discovered_list,
            duration_seconds=duration,
        )

    async def discover_technologies(
        self, req: TechnologyScanRequest, current_user: UserModel
    ) -> TechnologyScanResponse:
        """Execute a technology stack fingerprinting scan on a target URL.

        Enforces SSRF target validation, analyzes HTTP headers, HTML DOM structures, script URLs,
        and security header compliance. Records structured audit events.
        """
        target_str = str(req.target_url).rstrip("/")

        # 1. Pre-validate SSRF & Egress Firewall Safety
        is_safe, reason = is_safe_target_url(target_str)
        if not is_safe:
            logger.warning(
                "discovery.technology_scan_rejected_unsafe_target",
                target_url=target_str,
                reason=reason,
                user_id=str(current_user.id),
                org_id=str(current_user.organization_id),
            )
            await self.audit_service.record_event(
                organization_id=current_user.organization_id,
                action="technology.scan_rejected",
                resource_type="target",
                resource_id=target_str,
                actor_user_id=current_user.id,
                details={"target_url": target_str, "reason": reason},
            )
            raise ValidationException(f"Target URL is prohibited: {reason}")

        # 2. Record Technology Scan Started Audit Event
        await self.audit_service.record_event(
            organization_id=current_user.organization_id,
            action="technology.scan_started",
            resource_type="target",
            resource_id=target_str,
            actor_user_id=current_user.id,
            details={"target_url": target_str},
        )

        # 3. Execute Technology Stack Probe
        fingerprinter = TechFingerprinter()
        tech_result = await fingerprinter.probe_and_fingerprint(target_str)

        # 4. Map Domain TechnologyScanResult to Response DTOs
        tech_dtos = [
            DetectedTechnologyDTO(
                name=t.name,
                category=t.category.value,
                version=t.version,
                confidence=t.confidence,
                matched_by=t.matched_by,
            )
            for t in tech_result.detected_technologies
        ]

        sec_header_dtos = [
            SecurityHeaderDTO(
                header_name=sh.header_name,
                present=sh.present,
                value=sh.value,
            )
            for sh in tech_result.security_headers
        ]

        # 5. Record Technology Scan Completed Audit Event
        await self.audit_service.record_event(
            organization_id=current_user.organization_id,
            action="technology.scan_completed",
            resource_type="target",
            resource_id=target_str,
            actor_user_id=current_user.id,
            details={
                "target_url": target_str,
                "status_code": tech_result.status_code,
                "technologies_found": len(tech_dtos),
                "duration_seconds": tech_result.duration_seconds,
            },
        )

        return TechnologyScanResponse(
            target_url=tech_result.target_url,
            status_code=tech_result.status_code,
            detected_technologies=tech_dtos,
            security_headers=sec_header_dtos,
            duration_seconds=tech_result.duration_seconds,
        )
