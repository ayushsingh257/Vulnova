"""Async HTTP Client for Atlassian Jira Cloud REST API."""

import base64
from typing import Any, Dict, List, Optional

import httpx
import structlog

from app.core.exceptions import IntegrationException

logger = structlog.get_logger(__name__)


class JiraClient:
    """Async client interacting with Jira Cloud REST API v3."""

    def __init__(self, host_url: str, email: str, api_token: str) -> None:
        clean_host = host_url.replace("https://", "").replace("http://", "").strip("/")
        self.base_url = f"https://{clean_host}"
        self.email = email
        self.api_token = api_token
        auth_str = f"{email}:{api_token}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        self.headers = {
            "Authorization": f"Basic {b64_auth}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def create_issue(
        self,
        project_key: str,
        issue_type: str,
        summary: str,
        description_adf: Dict[str, Any],
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a Jira issue and return issue key, ID, and self link."""
        url = f"{self.base_url}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": project_key.upper()},
                "summary": summary,
                "description": description_adf,
                "issuetype": {"name": issue_type},
                "labels": labels or ["vulnova-sec"],
            }
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(url, json=payload, headers=self.headers)
                if res.status_code not in (200, 201):
                    logger.error(
                        "jira.create_issue_failed",
                        status_code=res.status_code,
                        body=res.text,
                    )
                    raise IntegrationException(
                        f"Jira API returned HTTP {res.status_code}: {res.text[:200]}"
                    )
                data = res.json()
                issue_key = data.get("key", "")
                return {
                    "issue_id": data.get("id", ""),
                    "issue_key": issue_key,
                    "issue_url": f"{self.base_url}/browse/{issue_key}",
                    "raw": data,
                }
            except httpx.HTTPError as e:
                logger.error("jira.http_error", error=str(e))
                raise IntegrationException(
                    f"Failed to communicate with Jira: {str(e)}"
                ) from e

    async def get_issue_status(self, issue_key: str) -> Dict[str, Any]:
        """Get the current status of a Jira issue."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}?fields=status,summary"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(url, headers=self.headers)
                if res.status_code != 200:
                    raise IntegrationException(
                        f"Failed to fetch Jira issue '{issue_key}': HTTP {res.status_code}"
                    )
                data = res.json()
                fields = data.get("fields", {})
                status_obj = fields.get("status", {})
                status_name = status_obj.get("name", "Unknown")
                return {
                    "issue_key": issue_key,
                    "status_name": status_name,
                    "status_category": status_obj.get("statusCategory", {}).get(
                        "name", ""
                    ),
                    "summary": fields.get("summary", ""),
                }
            except httpx.HTTPError as e:
                logger.error("jira.get_issue_failed", error=str(e))
                raise IntegrationException(
                    f"Failed to fetch Jira issue status: {str(e)}"
                ) from e
