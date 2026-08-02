"""Headless Browser SPA Dynamic DOM Renderer (Playwright Integration).

Implements client-side JavaScript execution, dynamic DOM parsing, and background fetch/XHR
network request interception for Single-Page Applications (SPAs).

Playwright imports and browser launches are performed lazily and handled fail-safe to avoid
making Playwright a mandatory runtime startup dependency.
"""

import asyncio
import time
from typing import Any, Dict, List, Set
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger
from app.domain.entities.discovery import (
    CrawlResult,
    CrawlScope,
    DiscoveredForm,
    DiscoveredNetworkRequest,
    DiscoveredScript,
    DiscoveredURL,
)
from app.infrastructure.discovery.ssrf_validator import (
    is_safe_target_url,
    is_url_in_scope,
)

logger = get_logger("vulnova.playwright_renderer")

PAGE_TIMEOUT_MS = 30000
MAX_NETWORK_REQUESTS_PER_PAGE = 100


class PlaywrightUnavailableException(Exception):
    """Raised when Playwright is not installed or Chromium browser binaries are missing."""

    pass


class SPADynamicCrawler:
    """Headless Chromium dynamic DOM renderer for Single-Page Applications (SPAs)."""

    def __init__(self, scope: CrawlScope) -> None:
        self.scope = scope
        self.visited_urls: Set[str] = set()
        self.discovered_urls: Dict[str, DiscoveredURL] = {}
        self.discovered_forms: List[DiscoveredForm] = []
        self.discovered_scripts: List[DiscoveredScript] = []
        self.network_requests: List[DiscoveredNetworkRequest] = []

    async def crawl(self) -> CrawlResult:
        """Execute dynamic SPA rendering with lazy Playwright instantiation."""
        # 1. Lazy Playwright Import
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            logger.warning(
                "playwright.package_not_installed",
                error=str(e),
                target_url=self.scope.base_url,
            )
            raise PlaywrightUnavailableException(
                "Playwright python package is not installed"
            ) from e

        start_time = time.time()
        start_url = self.scope.base_url

        # Pre-validate safety of base target
        is_safe, reason = is_safe_target_url(start_url)
        if not is_safe:
            logger.warning(
                "playwright.unsafe_target_cancelled",
                target_url=start_url,
                reason=reason,
            )
            return CrawlResult(
                target_url=start_url,
                total_pages_crawled=0,
                duration_seconds=round(time.time() - start_time, 2),
            )

        try:
            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
                        ],
                    )
                except Exception as launch_err:
                    logger.warning(
                        "playwright.browser_launch_failed",
                        error=str(launch_err),
                        target_url=start_url,
                    )
                    raise PlaywrightUnavailableException(
                        f"Chromium browser launch failed: {launch_err}"
                    ) from launch_err

                context = await browser.new_context(
                    user_agent="Vulnova-AppSec-SPA-Scanner/1.0",
                    viewport={"width": 1280, "height": 800},
                    ignore_https_errors=True,
                )

                page = await context.new_page()
                page.set_default_timeout(PAGE_TIMEOUT_MS)

                # Intercept network requests (fetch / XHR)
                captured_requests: List[DiscoveredNetworkRequest] = []

                def _handle_request(request: Any) -> None:
                    if len(captured_requests) >= MAX_NETWORK_REQUESTS_PER_PAGE:
                        return
                    req_url = request.url
                    req_resource = request.resource_type
                    if req_resource in ("fetch", "xhr"):
                        # SSRF pre-check on background network calls
                        is_safe_req, _ = is_safe_target_url(req_url)
                        if is_safe_req:
                            captured_requests.append(
                                DiscoveredNetworkRequest(
                                    url=req_url,
                                    method=request.method.upper(),
                                    resource_type=req_resource,
                                )
                            )

                page.on("request", _handle_request)

                try:
                    logger.info("playwright.navigating", target_url=start_url)
                    response = await page.goto(
                        start_url, wait_until="networkidle", timeout=PAGE_TIMEOUT_MS
                    )
                    status_code = response.status if response else None

                    # Wait extra time for SPA hydration/routing
                    await asyncio.sleep(1.0)

                    # Extract fully rendered HTML DOM
                    rendered_html = await page.content()
                    title = await page.title()

                    self.discovered_urls[start_url] = DiscoveredURL(
                        url=start_url,
                        method="GET",
                        depth=0,
                        status_code=status_code,
                        content_type="text/html",
                        title=title,
                    )

                    # Parse rendered DOM nodes
                    soup = BeautifulSoup(rendered_html, "html.parser")

                    # Extract Links (<a href>)
                    for a_tag in soup.find_all("a", href=True):
                        if isinstance(a_tag, Tag) and a_tag.get("href"):
                            raw_href = str(a_tag["href"])
                            full_url = urljoin(start_url, raw_href)
                            if is_url_in_scope(
                                full_url,
                                self.scope.allowed_domain,
                                self.scope.allow_subdomains,
                            ):
                                self.discovered_urls[full_url] = DiscoveredURL(
                                    url=full_url,
                                    method="GET",
                                    depth=1,
                                )

                    # Extract Forms (<form action>)
                    for form_tag in soup.find_all("form"):
                        if isinstance(form_tag, Tag):
                            action = str(form_tag.get("action") or start_url)
                            full_action = urljoin(start_url, action)
                            method_val = str(form_tag.get("method") or "GET").upper()

                            inputs: List[Dict[str, str]] = []
                            for inp in form_tag.find_all(
                                ["input", "textarea", "select", "button"]
                            ):
                                if isinstance(inp, Tag):
                                    name_val = inp.get("name") or inp.get("id")
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

                    # Extract Scripts (<script src>)
                    for script_tag in soup.find_all("script", src=True):
                        if isinstance(script_tag, Tag) and script_tag.get("src"):
                            src_val = str(script_tag["src"])
                            full_src = urljoin(start_url, src_val)
                            is_ext = not is_url_in_scope(
                                full_src,
                                self.scope.allowed_domain,
                                self.scope.allow_subdomains,
                            )
                            self.discovered_scripts.append(
                                DiscoveredScript(src_url=full_src, is_external=is_ext)
                            )

                    self.network_requests = captured_requests

                except Exception as nav_err:
                    logger.warning(
                        "playwright.navigation_failed",
                        error=str(nav_err),
                        target_url=start_url,
                    )
                finally:
                    await context.close()
                    await browser.close()

        except PlaywrightUnavailableException:
            raise
        except Exception as e:
            logger.warning(
                "playwright.execution_failed",
                error=str(e),
                target_url=start_url,
            )
            raise PlaywrightUnavailableException(
                f"Playwright execution error: {e}"
            ) from e

        duration = round(time.time() - start_time, 2)
        logger.info(
            "playwright.completed",
            target_url=start_url,
            discovered_links=len(self.discovered_urls),
            discovered_forms=len(self.discovered_forms),
            network_requests=len(self.network_requests),
            duration=duration,
        )

        return CrawlResult(
            target_url=start_url,
            total_pages_crawled=1,
            discovered_urls=list(self.discovered_urls.values()),
            discovered_forms=self.discovered_forms,
            discovered_scripts=self.discovered_scripts,
            network_requests=self.network_requests,
            is_spa=True,
            duration_seconds=duration,
        )
