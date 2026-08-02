"""Discovery Application Use Case Services."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.discovery.dto import (
    CrawlRequest,
    CrawlResponse,
    DiscoveredFormDTO,
    DiscoveredNetworkRequestDTO,
    DiscoveredScriptDTO,
    DiscoveredURLDTO,
)
from app.core.exceptions import ValidationException
from app.core.logging import get_logger
from app.domain.entities.discovery import CrawlResult, CrawlScope
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.discovery.crawler import AsyncWebCrawler
from app.infrastructure.discovery.playwright_renderer import (
    PlaywrightUnavailableException,
    SPADynamicCrawler,
)
from app.infrastructure.discovery.ssrf_validator import (
    extract_base_domain,
    is_safe_target_url,
)

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
