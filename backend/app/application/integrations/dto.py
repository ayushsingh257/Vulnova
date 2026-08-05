"""Data Transfer Objects (DTOs) for Enterprise Jira & GitHub Issues Integrations."""

from typing import List, Optional

from pydantic import BaseModel, Field


class SaveJiraConfigRequest(BaseModel):
    """Payload to configure Jira Cloud integration."""

    host_url: str = Field(
        ..., description="Jira Cloud Host URL, e.g., acme.atlassian.net"
    )
    email: str = Field(..., description="Jira Service Account Email")
    api_token: str = Field(..., description="Jira API Token")
    project_key: str = Field(..., description="Jira Project Key, e.g., SEC")
    issue_type: str = Field(
        default="Bug", description="Jira Issue Type, e.g., Bug or Security Task"
    )


class SaveGitHubConfigRequest(BaseModel):
    """Payload to configure GitHub Issues integration."""

    repo_owner: str = Field(..., description="GitHub Repository Owner/Organization")
    repo_name: str = Field(..., description="GitHub Repository Name")
    personal_access_token: str = Field(
        ..., description="GitHub Personal Access Token or Fine-Grained PAT"
    )


class JiraConfigDTO(BaseModel):
    """Jira configuration status view (masked secrets)."""

    host_url: Optional[str] = None
    email: Optional[str] = None
    api_token_masked: Optional[str] = None
    project_key: Optional[str] = None
    issue_type: str = "Bug"
    is_configured: bool = False


class GitHubConfigDTO(BaseModel):
    """GitHub configuration status view (masked secrets)."""

    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None
    personal_access_token_masked: Optional[str] = None
    is_configured: bool = False


class IntegrationConfigResponse(BaseModel):
    """Combined integration configurations for tenant."""

    jira: JiraConfigDTO
    github: GitHubConfigDTO


class CreateIssueRequest(BaseModel):
    """Request payload to trigger issue creation."""

    custom_labels: List[str] = Field(default_factory=list)
    assignee: Optional[str] = None


class ExternalIssueDTO(BaseModel):
    """Model representing a created external ticket reference."""

    issue_id: str
    issue_key: str
    issue_url: str
    provider: str
    status: str
    created_at: str


class SyncStatusResponse(BaseModel):
    """Result of external issue status lifecycle synchronization."""

    finding_id: str
    provider: str
    external_issue_id: str
    external_status: str
    previous_vulnova_status: str
    updated_vulnova_status: str
    synced_at: str
