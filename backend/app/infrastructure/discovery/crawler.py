"""Async HTTP Web Crawler Engine."""

import asyncio
import time
from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger
from app.domain.entities.discovery import (
    CrawlResult,
    CrawlScope,
    DiscoveredForm,
    DiscoveredScript,
    DiscoveredURL,
)
from app.infrastructure.discovery.ssrf_validator import (
    is_safe_target_url,
    is_url_in_scope,
)

logger = get_logger("vulnova.crawler")

# Safety Caps
MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 MB maximum response body size
MAX_REDIRECTS = 5
DEFAULT_TIMEOUT_SECONDS = 10.0


class AsyncWebCrawler:
    """High-performance non-blocking async web crawler with safety controls and DOM extraction."""

    def __init__(self, scope: CrawlScope) -> None:
        self.scope = scope
        self.visited_urls: Set[str] = set()
        self.discovered_urls: Dict[str, DiscoveredURL] = {}
        self.discovered_forms: List[DiscoveredForm] = []
        self.discovered_scripts: List[DiscoveredScript] = []
        self.pages_crawled = 0
        self.semaphore = asyncio.Semaphore(scope.concurrency_limit)

    def normalize_url(self, url: str) -> str:
        """Strip fragment identifiers and normalize whitespace."""
        parsed = urlparse(url.strip())
        # Reconstruct without fragment
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            clean += f"?{parsed.query}"
        return clean

    async def crawl(self) -> CrawlResult:
        """Execute async recursive crawl starting from base target URL."""
        start_time = time.time()
        start_url = self.normalize_url(self.scope.base_url)

        # Pre-validate safety of base URL
        is_safe, reason = is_safe_target_url(start_url)
        if not is_safe:
            logger.warning(
                "crawler.start_cancelled_unsafe_target",
                target_url=start_url,
                reason=reason,
            )
            return CrawlResult(
                target_url=self.scope.base_url,
                total_pages_crawled=0,
                duration_seconds=round(time.time() - start_time, 2),
            )

        client_limits = httpx.Limits(
            max_keepalive_connections=self.scope.concurrency_limit,
            max_connections=self.scope.concurrency_limit * 2,
        )
        timeout_config = httpx.Timeout(DEFAULT_TIMEOUT_SECONDS)

        async with httpx.AsyncClient(
            limits=client_limits,
            timeout=timeout_config,
            max_redirects=MAX_REDIRECTS,
            follow_redirects=True,
            headers={"User-Agent": "Vulnova-AppSec-Scanner/1.0"},
        ) as client:
            queue: List[Tuple[str, int]] = [(start_url, 0)]
            while queue and self.pages_crawled < self.scope.max_pages:
                current_batch = queue[: self.scope.concurrency_limit]
                queue = queue[self.scope.concurrency_limit :]

                tasks = [
                    self._fetch_and_parse(client, url, depth)
                    for url, depth in current_batch
                    if url not in self.visited_urls
                ]
                if not tasks:
                    continue

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for res in batch_results:
                    if isinstance(res, list):
                        for new_url, new_depth in res:
                            if (
                                new_url not in self.visited_urls
                                and new_depth <= self.scope.max_depth
                                and self.pages_crawled + len(queue)
                                < self.scope.max_pages
                            ):
                                queue.append((new_url, new_depth))

        duration = round(time.time() - start_time, 2)
        logger.info(
            "crawler.completed",
            target_url=self.scope.base_url,
            pages_crawled=self.pages_crawled,
            discovered_links=len(self.discovered_urls),
            discovered_forms=len(self.discovered_forms),
            duration=duration,
        )

        return CrawlResult(
            target_url=self.scope.base_url,
            total_pages_crawled=self.pages_crawled,
            discovered_urls=list(self.discovered_urls.values()),
            discovered_forms=self.discovered_forms,
            discovered_scripts=self.discovered_scripts,
            duration_seconds=duration,
        )

    async def _fetch_and_parse(
        self, client: httpx.AsyncClient, url: str, depth: int
    ) -> List[Tuple[str, int]]:
        """Fetch a single URL, cap response body, and extract outbound links/forms/scripts."""
        if url in self.visited_urls or self.pages_crawled >= self.scope.max_pages:
            return []

        self.visited_urls.add(url)

        # Check domain scope and SSRF safety before fetching
        if not is_url_in_scope(
            url, self.scope.allowed_domain, self.scope.allow_subdomains
        ):
            return []

        is_safe, reason = is_safe_target_url(url)
        if not is_safe:
            logger.warning("crawler.skipped_unsafe_url", url=url, reason=reason)
            return []

        next_targets: List[Tuple[str, int]] = []

        async with self.semaphore:
            try:
                response = await client.get(url)
                self.pages_crawled += 1

                content_type = response.headers.get("content-type", "")

                # Record Discovered URL
                title = None
                is_html = "text/html" in content_type.lower()

                # Stream/Cap body reading
                body_bytes = response.content[:MAX_BODY_BYTES]

                if is_html:
                    try:
                        soup = BeautifulSoup(body_bytes, "html.parser")
                        title_tag = soup.find("title")
                        if title_tag and isinstance(title_tag, Tag) and title_tag.string:
                            title = str(title_tag.string).strip()

                        # 1. Extract Links (<a href>)
                        for a_tag in soup.find_all("a", href=True):
                            if isinstance(a_tag, Tag) and a_tag.get("href"):
                                raw_href = str(a_tag["href"])
                                full_url = self.normalize_url(urljoin(url, raw_href))
                                if is_url_in_scope(
                                    full_url,
                                    self.scope.allowed_domain,
                                    self.scope.allow_subdomains,
                                ):
                                    next_targets.append((full_url, depth + 1))

                        # 2. Extract Forms (<form action>)
                        for form_tag in soup.find_all("form"):
                            if isinstance(form_tag, Tag):
                                action = str(form_tag.get("action") or url)
                                full_action = self.normalize_url(urljoin(url, action))
                                method_val = str(form_tag.get("method") or "GET").upper()

                                inputs: List[Dict[str, str]] = []
                                for inp in form_tag.find_all(["input", "textarea", "select"]):
                                    if isinstance(inp, Tag):
                                        name_val = inp.get("name")
                                        if name_val:
                                            inputs.append(
                                                {
                                                    "name": str(name_val),
                                                    "type": str(inp.get("type") or "text"),
                                                }
                                            )

                                self.discovered_forms.append(
                                    DiscoveredForm(
                                        action_url=full_action,
                                        method=method_val,
                                        inputs=inputs,
                                    )
                                )

                        # 3. Extract Scripts (<script src>)
                        for script_tag in soup.find_all("script", src=True):
                            if isinstance(script_tag, Tag) and script_tag.get("src"):
                                src_val = str(script_tag["src"])
                                full_src = self.normalize_url(urljoin(url, src_val))
                                is_ext = not is_url_in_scope(
                                    full_src,
                                    self.scope.allowed_domain,
                                    self.scope.allow_subdomains,
                                )
                                self.discovered_scripts.append(
                                    DiscoveredScript(src_url=full_src, is_external=is_ext)
                                )

                    except Exception as parse_err:
                        logger.warning(
                            "crawler.html_parse_failed",
                            url=url,
                            error=str(parse_err),
                        )

                self.discovered_urls[url] = DiscoveredURL(
                    url=url,
                    method="GET",
                    depth=depth,
                    status_code=response.status_code,
                    content_type=content_type,
                    title=title,
                )

            except httpx.HTTPError as http_err:
                logger.warning(
                    "crawler.fetch_failed",
                    url=url,
                    error=str(http_err),
                )

        return next_targets
