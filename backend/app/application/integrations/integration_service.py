"""Application Service for Jira and GitHub Issues Integrations."""

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.finding.finding_intelligence_service import (
    FindingIntelligenceService,
)
from app.application.integrations.dto import (
    CreateIssueRequest,
    ExternalIssueDTO,
    GitHubConfigDTO,
    IntegrationConfigResponse,
    JiraConfigDTO,
    SaveGitHubConfigRequest,
    SaveJiraConfigRequest,
    SyncStatusResponse,
)
from app.application.integrations.github.github_client import GitHubClient
from app.application.integrations.github.github_mapper import (
    ControlledGitHubStatusMapper,
    GitHubFindingMapper,
)
from app.application.integrations.jira.jira_client import JiraClient
from app.application.integrations.jira.jira_mapper import (
    ControlledJiraStatusMapper,
    JiraFindingMapper,
)
from app.core.exceptions import (
    IntegrationException,
    ResourceNotFoundException,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.finding_triage_repository import (
    FindingTriageRepository,
)
from app.security.encryption import SecretEncryptionService

logger = structlog.get_logger(__name__)

# In-memory backup store for encrypted integration credentials per organization
_ENCRYPTED_INTEGRATIONS_STORE: Dict[str, Dict[str, Any]] = {}


class IntegrationService:
    """Service orchestrating external issue creation, lifecycle sync, and secret encryption."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service
        self.encryption_service = SecretEncryptionService()
        self.intelligence_service = FindingIntelligenceService(session)
        self.triage_repo = FindingTriageRepository(session)

    async def _get_org_config_store(self, organization_id: UUID) -> Dict[str, Any]:
        """Fetch encrypted tenant integration config from store."""
        org_id_str = str(organization_id)
        return _ENCRYPTED_INTEGRATIONS_STORE.get(org_id_str, {})

    async def _save_org_config_store(
        self, organization_id: UUID, config_data: Dict[str, Any]
    ) -> None:
        """Persist encrypted integration config to store."""
        org_id_str = str(organization_id)
        _ENCRYPTED_INTEGRATIONS_STORE[org_id_str] = config_data

    async def get_integration_status(
        self, user: UserModel
    ) -> IntegrationConfigResponse:
        """Get integration configuration status for user's organization (secrets masked)."""
        store = await self._get_org_config_store(user.organization_id)

        jira_raw = store.get("jira", {})
        github_raw = store.get("github", {})

        jira_token = jira_raw.get("encrypted_api_token", "")
        jira_masked = f"vn_token_{'*' * 8}{jira_token[-4:]}" if jira_token else None

        jira_dto = JiraConfigDTO(
            host_url=jira_raw.get("host_url"),
            email=jira_raw.get("email"),
            api_token_masked=jira_masked,
            project_key=jira_raw.get("project_key"),
            issue_type=jira_raw.get("issue_type", "Bug"),
            is_configured=bool(jira_token and jira_raw.get("host_url")),
        )

        gh_token = github_raw.get("encrypted_pat", "")
        gh_masked = f"ghp_{'*' * 8}{gh_token[-4:]}" if gh_token else None

        github_dto = GitHubConfigDTO(
            repo_owner=github_raw.get("repo_owner"),
            repo_name=github_raw.get("repo_name"),
            personal_access_token_masked=gh_masked,
            is_configured=bool(gh_token and github_raw.get("repo_owner")),
        )

        return IntegrationConfigResponse(jira=jira_dto, github=github_dto)

    async def save_jira_config(
        self, user: UserModel, req: SaveJiraConfigRequest
    ) -> JiraConfigDTO:
        """Encrypt Jira API token and save Jira configuration for tenant."""
        encrypted_token = self.encryption_service.encrypt_secret(req.api_token)

        jira_payload = {
            "host_url": req.host_url,
            "email": req.email,
            "encrypted_api_token": encrypted_token,
            "project_key": req.project_key.upper(),
            "issue_type": req.issue_type,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        store = await self._get_org_config_store(user.organization_id)
        store["jira"] = jira_payload
        await self._save_org_config_store(user.organization_id, store)

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="integration.configuration_updated",
            resource_type="integration_provider",
            resource_id="jira",
            actor_user_id=user.id,
            details={
                "provider": "jira",
                "host_url": req.host_url,
                "project_key": req.project_key.upper(),
            },
        )

        return JiraConfigDTO(
            host_url=req.host_url,
            email=req.email,
            api_token_masked=f"vn_token_{'*' * 8}{encrypted_token[-4:]}",
            project_key=req.project_key.upper(),
            issue_type=req.issue_type,
            is_configured=True,
        )

    async def save_github_config(
        self, user: UserModel, req: SaveGitHubConfigRequest
    ) -> GitHubConfigDTO:
        """Encrypt GitHub PAT token and save GitHub configuration for tenant."""
        encrypted_token = self.encryption_service.encrypt_secret(
            req.personal_access_token
        )

        github_payload = {
            "repo_owner": req.repo_owner,
            "repo_name": req.repo_name,
            "encrypted_pat": encrypted_token,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        store = await self._get_org_config_store(user.organization_id)
        store["github"] = github_payload
        await self._save_org_config_store(user.organization_id, store)

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="integration.configuration_updated",
            resource_type="integration_provider",
            resource_id="github",
            actor_user_id=user.id,
            details={
                "provider": "github",
                "repo_owner": req.repo_owner,
                "repo_name": req.repo_name,
            },
        )

        return GitHubConfigDTO(
            repo_owner=req.repo_owner,
            repo_name=req.repo_name,
            personal_access_token_masked=f"ghp_{'*' * 8}{encrypted_token[-4:]}",
            is_configured=True,
        )

    async def _get_finding_with_tenant_isolation(
        self, organization_id: UUID, finding_id: UUID
    ) -> SecurityFindingModel:
        """Retrieve finding and verify tenant isolation."""
        stmt = select(SecurityFindingModel).where(
            SecurityFindingModel.id == finding_id,
            SecurityFindingModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        finding = res.scalar_one_or_none()
        if not finding:
            raise ResourceNotFoundException(
                f"Security Finding '{finding_id}' not found",
                details={"finding_id": str(finding_id)},
            )
        return finding

    async def create_jira_issue(
        self, user: UserModel, finding_id: UUID, req: CreateIssueRequest
    ) -> ExternalIssueDTO:
        """Create Jira issue for vulnerability finding."""
        finding = await self._get_finding_with_tenant_isolation(
            user.organization_id, finding_id
        )

        store = await self._get_org_config_store(user.organization_id)
        jira_raw = store.get("jira")
        if not jira_raw or not jira_raw.get("encrypted_api_token"):
            raise IntegrationException(
                "Jira integration is not configured for this organization."
            )

        plain_token = self.encryption_service.decrypt_secret(
            jira_raw["encrypted_api_token"]
        )
        jira_client = JiraClient(
            host_url=jira_raw["host_url"],
            email=jira_raw["email"],
            api_token=plain_token,
        )

        summary = JiraFindingMapper.format_summary(finding)
        adf_desc = JiraFindingMapper.format_adf_description(finding)
        labels = ["vulnova-sec"] + req.custom_labels

        res = await jira_client.create_issue(
            project_key=jira_raw["project_key"],
            issue_type=jira_raw.get("issue_type", "Bug"),
            summary=summary,
            description_adf=adf_desc,
            labels=labels,
        )

        # Store external issue reference inside finding metadata
        ev_json = dict(finding.evidence_json) if finding.evidence_json else {}
        ev_json["external_jira_issue"] = {
            "issue_id": res["issue_id"],
            "issue_key": res["issue_key"],
            "issue_url": res["issue_url"],
            "status": "OPEN",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        finding.evidence_json = ev_json
        await self.session.commit()

        # Record audit event
        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="integration.issue_created",
            resource_type="security_finding",
            resource_id=str(finding_id),
            actor_user_id=user.id,
            details={
                "provider": "jira",
                "issue_key": res["issue_key"],
                "issue_url": res["issue_url"],
            },
        )

        return ExternalIssueDTO(
            issue_id=res["issue_id"],
            issue_key=res["issue_key"],
            issue_url=res["issue_url"],
            provider="jira",
            status="OPEN",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    async def create_github_issue(
        self, user: UserModel, finding_id: UUID, req: CreateIssueRequest
    ) -> ExternalIssueDTO:
        """Create GitHub issue for vulnerability finding."""
        finding = await self._get_finding_with_tenant_isolation(
            user.organization_id, finding_id
        )

        store = await self._get_org_config_store(user.organization_id)
        github_raw = store.get("github")
        if not github_raw or not github_raw.get("encrypted_pat"):
            raise IntegrationException(
                "GitHub integration is not configured for this organization."
            )

        plain_pat = self.encryption_service.decrypt_secret(github_raw["encrypted_pat"])
        github_client = GitHubClient(personal_access_token=plain_pat)

        title = GitHubFindingMapper.format_title(finding)
        body = GitHubFindingMapper.format_body(finding)
        labels = ["security", "vulnova-finding"] + req.custom_labels

        res = await github_client.create_issue(
            owner=github_raw["repo_owner"],
            repo=github_raw["repo_name"],
            title=title,
            body=body,
            labels=labels,
        )

        # Store external issue reference inside finding metadata
        ev_json = dict(finding.evidence_json) if finding.evidence_json else {}
        ev_json["external_github_issue"] = {
            "issue_id": res["issue_id"],
            "issue_key": res["issue_key"],
            "issue_number": res["issue_number"],
            "issue_url": res["issue_url"],
            "status": "OPEN",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        finding.evidence_json = ev_json
        await self.session.commit()

        # Record audit event
        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="integration.issue_created",
            resource_type="security_finding",
            resource_id=str(finding_id),
            actor_user_id=user.id,
            details={
                "provider": "github",
                "issue_key": res["issue_key"],
                "issue_url": res["issue_url"],
            },
        )

        return ExternalIssueDTO(
            issue_id=res["issue_id"],
            issue_key=res["issue_key"],
            issue_url=res["issue_url"],
            provider="github",
            status="OPEN",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    async def sync_jira_status(
        self, user: UserModel, finding_id: UUID, issue_key: str
    ) -> SyncStatusResponse:
        """Sync Jira ticket status through controlled state transition layer."""
        finding = await self._get_finding_with_tenant_isolation(
            user.organization_id, finding_id
        )

        store = await self._get_org_config_store(user.organization_id)
        jira_raw = store.get("jira")
        if not jira_raw or not jira_raw.get("encrypted_api_token"):
            raise IntegrationException("Jira integration is not configured.")

        plain_token = self.encryption_service.decrypt_secret(
            jira_raw["encrypted_api_token"]
        )
        jira_client = JiraClient(
            host_url=jira_raw["host_url"],
            email=jira_raw["email"],
            api_token=plain_token,
        )

        jira_status_res = await jira_client.get_issue_status(issue_key)
        ext_status = jira_status_res["status_name"]

        # Pass through ControlledJiraStatusMapper state transition layer
        triage_history = await self.triage_repo.get_triage_history(
            user.organization_id, finding_id
        )
        prev_vulnova_status = (
            triage_history[0].new_status if triage_history else "CONFIRMED"
        )
        updated_vulnova_status = (
            ControlledJiraStatusMapper.map_jira_status_to_vulnova_state(
                external_status=ext_status,
                current_vulnova_status=prev_vulnova_status,
            )
        )

        if updated_vulnova_status != prev_vulnova_status:
            await self.triage_repo.record_triage_action(
                organization_id=user.organization_id,
                finding_id=finding_id,
                new_status=updated_vulnova_status,
                previous_status=prev_vulnova_status,
                actor_user_id=user.id,
                comment=f"Status synchronized from external Jira issue '{issue_key}' ({ext_status})",
            )
            if (
                finding
                and finding.evidence_json
                and isinstance(finding.evidence_json, dict)
            ):
                ev_dict = dict(finding.evidence_json)
                if "external_jira_issue" in ev_dict:
                    ev_dict["external_jira_issue"]["status"] = ext_status
                    finding.evidence_json = ev_dict
            await self.session.commit()

        # Record audit event
        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="integration.issue_synced",
            resource_type="security_finding",
            resource_id=str(finding_id),
            actor_user_id=user.id,
            details={
                "provider": "jira",
                "issue_key": issue_key,
                "external_status": ext_status,
                "previous_status": prev_vulnova_status,
                "updated_status": updated_vulnova_status,
            },
        )

        return SyncStatusResponse(
            finding_id=str(finding_id),
            provider="jira",
            external_issue_id=issue_key,
            external_status=ext_status,
            previous_vulnova_status=prev_vulnova_status,
            updated_vulnova_status=updated_vulnova_status,
            synced_at=datetime.now(timezone.utc).isoformat(),
        )

    async def sync_github_status(
        self, user: UserModel, finding_id: UUID, issue_number: str
    ) -> SyncStatusResponse:
        """Sync GitHub issue status through controlled state transition layer."""
        finding = await self._get_finding_with_tenant_isolation(
            user.organization_id, finding_id
        )

        store = await self._get_org_config_store(user.organization_id)
        github_raw = store.get("github")
        if not github_raw or not github_raw.get("encrypted_pat"):
            raise IntegrationException("GitHub integration is not configured.")

        plain_pat = self.encryption_service.decrypt_secret(github_raw["encrypted_pat"])
        github_client = GitHubClient(personal_access_token=plain_pat)

        gh_issue_res = await github_client.get_issue(
            owner=github_raw["repo_owner"],
            repo=github_raw["repo_name"],
            issue_number=issue_number,
        )
        ext_state = gh_issue_res["state"]
        labels = gh_issue_res.get("labels", [])

        # Pass through ControlledGitHubStatusMapper state transition layer
        triage_history_gh = await self.triage_repo.get_triage_history(
            user.organization_id, finding_id
        )
        prev_vulnova_status = (
            triage_history_gh[0].new_status if triage_history_gh else "CONFIRMED"
        )
        updated_vulnova_status = (
            ControlledGitHubStatusMapper.map_github_status_to_vulnova_state(
                external_state=ext_state,
                labels=labels,
                current_vulnova_status=prev_vulnova_status,
            )
        )

        if updated_vulnova_status != prev_vulnova_status:
            await self.triage_repo.record_triage_action(
                organization_id=user.organization_id,
                finding_id=finding_id,
                new_status=updated_vulnova_status,
                previous_status=prev_vulnova_status,
                actor_user_id=user.id,
                comment=f"Status synchronized from external GitHub issue #{issue_number} ({ext_state})",
            )
            if (
                finding
                and finding.evidence_json
                and isinstance(finding.evidence_json, dict)
            ):
                ev_dict = dict(finding.evidence_json)
                if "external_github_issue" in ev_dict:
                    ev_dict["external_github_issue"]["status"] = ext_state
                    finding.evidence_json = ev_dict
            await self.session.commit()

        # Record audit event
        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="integration.issue_synced",
            resource_type="security_finding",
            resource_id=str(finding_id),
            actor_user_id=user.id,
            details={
                "provider": "github",
                "issue_number": issue_number,
                "external_status": ext_state,
                "previous_status": prev_vulnova_status,
                "updated_status": updated_vulnova_status,
            },
        )

        return SyncStatusResponse(
            finding_id=str(finding_id),
            provider="github",
            external_issue_id=f"#{issue_number}",
            external_status=ext_state,
            previous_vulnova_status=prev_vulnova_status,
            updated_vulnova_status=updated_vulnova_status,
            synced_at=datetime.now(timezone.utc).isoformat(),
        )
