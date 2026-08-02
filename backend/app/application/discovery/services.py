"""Discovery Application Use Case Services."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.discovery.dto import (
    CrawlRequest,
    CrawlResponse,
    DiscoveredFormDTO,
    DiscoveredScriptDTO,
    DiscoveredURLDTO,
)
from app.core.exceptions import ValidationException
from app.core.logging import get_logger
from app.domain.entities.discovery import CrawlScope
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.discovery.crawler import AsyncWebCrawler
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
            },
        )

        # 3. Instantiate CrawlScope & AsyncWebCrawler
        scope = CrawlScope(
            base_url=target_str,
            allowed_domain=base_domain,
            allow_subdomains=req.allow_subdomains,
            max_depth=req.max_depth,
            max_pages=req.max_pages,
            concurrency_limit=req.concurrency_limit,
        )

        crawler = AsyncWebCrawler(scope)
        crawl_result = await crawler.crawl()

        # 4. Map Domain CrawlResult to Response DTOs
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

        # 5. Record Crawl Completed Audit Event
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
                "duration_seconds": crawl_result.duration_seconds,
            },
        )

        return CrawlResponse(
            target_url=crawl_result.target_url,
            total_pages_crawled=crawl_result.total_pages_crawled,
            discovered_urls=urls_dto,
            discovered_forms=forms_dto,
            discovered_scripts=scripts_dto,
            duration_seconds=crawl_result.duration_seconds,
        )
