"""Unit and Integration Tests for Phase 4.6 Multi-Modal Evidence Collection & Capture Engine."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.assessment.dto import CreateAssessmentRequest
from app.application.assessment.services import AssessmentService
from app.domain.entities.assessment import (
    AssessmentContext,
    EvidenceType,
    Finding,
    SeverityLevel,
    VulnerabilityCategory,
)
from app.infrastructure.assessment.evidence_engine import (
    EvidenceCollectionEngine,
    mask_sensitive_cookies,
    mask_sensitive_headers,
)
from app.infrastructure.assessment.plugins.headers_plugin import (
    SecurityHeadersPlugin,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.evidence_repository import (
    EvidenceRepository,
)
from app.infrastructure.storage.evidence_store import EvidenceArtifactStorage


def test_mask_sensitive_headers() -> None:
    """Test header masking removes Authorization Bearer tokens, cookies, and API keys."""
    headers = {
        "Host": "example.com",
        "Authorization": "Bearer secret_jwt_token_123",
        "Cookie": "session=abc12345; auth=xyz987",
        "X-API-Key": "super-secret-key",
        "User-Agent": "Mozilla/5.0",
    }
    masked = mask_sensitive_headers(headers)
    assert masked["Host"] == "example.com"
    assert masked["Authorization"] == "Bearer *******"
    assert masked["Cookie"] == "*******"
    assert masked["X-API-Key"] == "*******"
    assert masked["User-Agent"] == "Mozilla/5.0"


def test_mask_sensitive_cookies() -> None:
    """Test cookie masking masks session, jwt, and auth cookies while preserving public cookies."""
    cookies = {
        "theme": "dark",
        "sessionid": "secret_session_id",
        "jwt_token": "secret_jwt",
        "lang": "en",
    }
    masked = mask_sensitive_cookies(cookies)
    assert masked["theme"] == "dark"
    assert masked["sessionid"] == "*******"
    assert masked["jwt_token"] == "*******"
    assert masked["lang"] == "en"


def test_evidence_store_save_and_retrieve() -> None:
    """Test EvidenceArtifactStorage saves content bytes, calculates SHA-256 checksums, and retrieves data."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            with TemporaryDirectory() as tmp_dir:
                storage = EvidenceArtifactStorage(base_dir=Path(tmp_dir))
                org_id = uuid4()
                finding_id = uuid4()
                content = b"<html><body>Proof of XSS</body></html>"

                artifact = await storage.save_artifact(
                    organization_id=org_id,
                    finding_id=finding_id,
                    artifact_type=EvidenceType.DOM_SNAPSHOT,
                    filename="dom.html",
                    content=content,
                    metadata={"url": "https://example.com"},
                )

                assert artifact.organization_id == org_id
                assert artifact.finding_id == finding_id
                assert artifact.artifact_type == EvidenceType.DOM_SNAPSHOT
                assert artifact.checksum != ""

                retrieved = await storage.retrieve_artifact(artifact.storage_path)
                assert retrieved == content

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_evidence_engine_capture_finding() -> None:
    """Test EvidenceCollectionEngine captures HTTP request/response, headers, DOM snapshot, and screenshot artifacts."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            with TemporaryDirectory() as tmp_dir:
                storage = EvidenceArtifactStorage(base_dir=Path(tmp_dir))
                engine = EvidenceCollectionEngine(storage=storage)

                finding = Finding(
                    organization_id=uuid4(),
                    title="SQL Injection",
                    severity=SeverityLevel.CRITICAL,
                    category=VulnerabilityCategory.INJECTION,
                    evidence={
                        "probe_url": "https://example.com/api/users?id=1'",
                        "method": "GET",
                        "status_code": 500,
                        "request_headers": {"Authorization": "Bearer secret"},
                        "response_headers": {"Content-Type": "text/html"},
                        "response_body": "PostgreSQL Syntax Error",
                    },
                )
                ctx = AssessmentContext(
                    target_url="https://example.com",
                    target_domain="example.com",
                    organization_id=finding.organization_id,
                )

                artifacts = await engine.capture_evidence_for_finding(finding, ctx)
                assert len(artifacts) >= 4
                types = [a.artifact_type for a in artifacts]
                assert EvidenceType.HTTP_REQUEST in types
                assert EvidenceType.HTTP_RESPONSE in types
                assert EvidenceType.HEADER_DATA in types
                assert EvidenceType.DOM_SNAPSHOT in types
                assert EvidenceType.SCREENSHOT in types

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_evidence_repository_crud() -> None:
    """Test EvidenceRepository persists and lists artifacts with tenant isolation."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            repo = EvidenceRepository(mock_session)
            org_id = uuid4()
            finding_id = uuid4()

            finding = Finding(
                organization_id=org_id,
                title="Test Finding",
            )
            with TemporaryDirectory() as tmp_dir:
                storage = EvidenceArtifactStorage(base_dir=Path(tmp_dir))
                art = await storage.save_artifact(
                    organization_id=org_id,
                    finding_id=finding_id,
                    artifact_type=EvidenceType.HTTP_REQUEST,
                    filename="request.txt",
                    content=b"GET / HTTP/1.1",
                )

                mock_model = MagicMock()
                mock_model.id = art.id
                mock_model.organization_id = org_id
                mock_model.finding_id = finding_id
                mock_model.artifact_type = "HTTP_REQUEST"
                mock_model.storage_path = art.storage_path
                mock_model.checksum = art.checksum

                mock_execute = MagicMock()
                mock_execute.scalars().all.return_value = [mock_model]
                mock_session.execute.return_value = mock_execute

                created = await repo.create_artifact(org_id, art)
                assert created is not None

                list_result = await repo.list_finding_artifacts(org_id, finding_id)
                assert len(list_result) == 1
                assert list_result[0].artifact_type == "HTTP_REQUEST"

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_assessment_service_evidence_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration test verifying AssessmentService executes plugins -> Risk Engine -> Deduplication -> Evidence Engine -> DB & Storage."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            with TemporaryDirectory() as tmp_dir:
                mock_session = AsyncMock()
                service = AssessmentService(mock_session)
                service.evidence_engine = EvidenceCollectionEngine(
                    storage=EvidenceArtifactStorage(base_dir=Path(tmp_dir))
                )

                service.plugin_registry.clear()
                service.plugin_registry.register(SecurityHeadersPlugin())

                mock_user = MagicMock(spec=UserModel)
                mock_user.id = uuid4()
                mock_user.organization_id = uuid4()

                mock_job = MagicMock()
                mock_job.id = uuid4()
                mock_job.target_url = "https://example.com"
                mock_job.execution_state = "QUEUED"
                mock_job.created_at = "2026-08-02T22:00:00Z"

                service.repo.create_job = AsyncMock(return_value=mock_job)
                service.repo.get_job_by_id = AsyncMock(return_value=mock_job)
                service.repo.update_execution_state = AsyncMock(return_value=mock_job)
                service.repo.update_job_status = AsyncMock()
                service.repo.create_finding = AsyncMock()
                service.evidence_repo.create_artifact = AsyncMock()

                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.headers = {"content-type": "text/html"}
                mock_resp.text = "<html><body>Hello Proof</body></html>"

                mock_client = AsyncMock()
                mock_client.get.return_value = mock_resp
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None

                monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

                service.assessment_policy_engine.validate_scan_authorization = (
                    AsyncMock(
                        return_value=MagicMock(is_allowed=True, rejection_reason=None)
                    )
                )

                req = CreateAssessmentRequest(
                    target_url="https://example.com",
                    is_authorized_assessment=True,
                )
                res = await service.create_and_run_assessment(req, mock_user)

                assert res.status == "COMPLETED"
                assert res.total_findings >= 1

                finding_dto = res.findings[0]
                assert finding_dto.evidence_count > 0
                assert finding_dto.evidence_available is True
                assert len(finding_dto.artifacts) > 0
                assert finding_dto.artifacts[0].checksum != ""

        loop.run_until_complete(_run())
    finally:
        loop.close()
