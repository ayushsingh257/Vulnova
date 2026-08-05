"""Async HTTP Client for GitHub REST API."""

from typing import Any, Dict, List, Optional

import httpx
import structlog

from app.core.exceptions import IntegrationException

logger = structlog.get_logger(__name__)


class GitHubClient:
    """Async client interacting with GitHub REST API v3."""

    def __init__(self, personal_access_token: str) -> None:
        self.base_url = "https://api.github.com"
        self.pat = personal_access_token.strip()
        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Vulnova-AppSec-Platform",
        }

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a GitHub issue in target repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        payload = {
            "title": title,
            "body": body,
            "labels": labels or ["security", "vulnova-finding"],
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(url, json=payload, headers=self.headers)
                if res.status_code not in (200, 201):
                    logger.error(
                        "github.create_issue_failed",
                        status_code=res.status_code,
                        body=res.text,
                    )
                    raise IntegrationException(
                        f"GitHub API returned HTTP {res.status_code}: {res.text[:200]}"
                    )
                data = res.json()
                issue_num = str(data.get("number", ""))
                return {
                    "issue_id": str(data.get("id", "")),
                    "issue_key": f"#{issue_num}",
                    "issue_number": issue_num,
                    "issue_url": data.get("html_url", ""),
                    "raw": data,
                }
            except httpx.HTTPError as e:
                logger.error("github.http_error", error=str(e))
                raise IntegrationException(
                    f"Failed to communicate with GitHub: {str(e)}"
                ) from e

    async def get_issue(
        self, owner: str, repo: str, issue_number: str
    ) -> Dict[str, Any]:
        """Get the current state and labels of a GitHub issue."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(url, headers=self.headers)
                if res.status_code != 200:
                    raise IntegrationException(
                        f"Failed to fetch GitHub issue #{issue_number}: HTTP {res.status_code}"
                    )
                data = res.json()
                labels = [
                    lbl.get("name", "")
                    for lbl in data.get("labels", [])
                    if isinstance(lbl, dict)
                ]
                return {
                    "issue_number": str(data.get("number", "")),
                    "state": data.get("state", "open"),
                    "labels": labels,
                    "title": data.get("title", ""),
                    "html_url": data.get("html_url", ""),
                }
            except httpx.HTTPError as e:
                logger.error("github.get_issue_failed", error=str(e))
                raise IntegrationException(
                    f"Failed to fetch GitHub issue status: {str(e)}"
                ) from e
