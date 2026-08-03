"""Unit & Integration Tests for AI Finding Explainer & Impact Analysis Engine (Phase 5.2)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.ai.dto import AIChatCompletionResponse
from app.application.ai.explainer_service import AIFindingExplainerService
from app.application.ai.impact_analysis_service import ImpactAnalysisService
from app.domain.entities.assessment import Finding, SeverityLevel
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.asset_graph import AssetNodeModel
from app.infrastructure.database.repositories.ai_analysis_repository import (
    AIAnalysisRepository,
)


@pytest.mark.anyio
async def test_explainer_service_generates_explanation() -> None:
    """Test generating a structured AI finding explanation with mocked LLM response."""
    mock_session = MagicMock()
    explainer_service = AIFindingExplainerService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="sqli_plugin",
        title="SQL Injection in Login Form",
        description="Unsanitized user input in username field.",
        severity="HIGH",
        category="INJECTION",
        cve_id="CVE-2024-1234",
        cwe_id="CWE-89",
        remediation="Use parameterized queries.",
        risk_score=85.0,
        cvss_json={
            "version": "3.1",
            "base_score": 8.5,
            "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        },
        epss_json={"epss_score": 0.75, "percentile": 0.95},
    )

    explainer_service.assessment_repo.get_finding_by_id = AsyncMock(
        return_value=mock_finding
    )
    explainer_service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    explainer_service.triage_repo.list_triage_history = AsyncMock(return_value=[])

    mock_json_payload = {
        "vulnerability_summary": "SQL Injection allowing database extraction.",
        "technical_root_cause": "Direct string concatenation in SQL query builder.",
        "affected_asset_context": "Login authentication API endpoint.",
        "exploitability_analysis": "High exploitability; public tool availability.",
        "business_impact": "Potential data breach and unauthorized database access.",
        "attack_prerequisites": "Network access to login form.",
        "severity_reasoning": "High CVSS base score of 8.5 due to complete loss of confidentiality and integrity.",
        "remediation_priority": "P1 - Fix immediately within 72 hours.",
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=150,
        completion_tokens=200,
        total_tokens=350,
        latency_ms=450,
        cost_usd=0.005,
        status="SUCCESS",
    )

    explainer_service.gateway_service.generate_completion = AsyncMock(
        return_value=mock_completion_resp
    )
    explainer_service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    explainer_service.ai_analysis_repo.create_explanation = AsyncMock()
    explainer_service.audit_service.record_event = AsyncMock()

    # Mock the return value of create_explanation to simulate DB persistence
    mock_created_model = MagicMock()
    mock_created_model.id = uuid4()
    mock_created_model.finding_id = finding_id
    mock_created_model.vulnerability_summary = mock_json_payload[
        "vulnerability_summary"
    ]
    mock_created_model.technical_root_cause = mock_json_payload["technical_root_cause"]
    mock_created_model.affected_asset_context = mock_json_payload[
        "affected_asset_context"
    ]
    mock_created_model.exploitability_analysis = mock_json_payload[
        "exploitability_analysis"
    ]
    mock_created_model.business_impact = mock_json_payload["business_impact"]
    mock_created_model.attack_prerequisites = mock_json_payload["attack_prerequisites"]
    mock_created_model.severity_reasoning = mock_json_payload["severity_reasoning"]
    mock_created_model.remediation_priority = mock_json_payload["remediation_priority"]
    mock_created_model.model_used = "gpt-4o"
    mock_created_model.provider_used = "OPENAI"
    mock_created_model.prompt_version = 1
    mock_created_model.status = "COMPLETED"
    mock_created_model.created_at = "2026-08-03T12:00:00Z"
    explainer_service.ai_analysis_repo.create_explanation.return_value = (
        mock_created_model
    )

    dto = await explainer_service.generate_explanation(org_id, finding_id, actor_id)

    assert dto.finding_id == str(finding_id)
    assert dto.vulnerability_summary == mock_json_payload["vulnerability_summary"]
    assert dto.technical_root_cause == mock_json_payload["technical_root_cause"]
    assert dto.model_used == "gpt-4o"
    assert dto.provider_used == "OPENAI"
    assert dto.status == "COMPLETED"
    assert explainer_service.audit_service.record_event.called


@pytest.mark.anyio
async def test_impact_analysis_service_generates_report() -> None:
    """Test generating a structured AI impact analysis report with asset topology context."""
    mock_session = MagicMock()
    impact_service = ImpactAnalysisService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    asset_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        asset_node_id=asset_id,
        plugin_id="rce_plugin",
        title="Remote Code Execution in Upload API",
        description="Arbitrary file upload allows shell execution.",
        severity="CRITICAL",
        category="INJECTION",
        cve_id="CVE-2024-9999",
        cwe_id="CWE-434",
        remediation="Validate file extensions and store files off-webroot.",
        risk_score=98.0,
        cvss_json={
            "version": "3.1",
            "base_score": 9.8,
            "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        },
        epss_json={"epss_score": 0.92, "percentile": 0.99},
    )

    mock_asset = AssetNodeModel(
        id=asset_id,
        organization_id=org_id,
        node_type="ENDPOINT",
        name="api.company.com/upload",
        value="https://api.company.com/upload",
    )

    impact_service.assessment_repo.get_finding_by_id = AsyncMock(
        return_value=mock_finding
    )
    impact_service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    impact_service.asset_graph_repo.get_node_by_id = AsyncMock(return_value=mock_asset)
    impact_service.asset_graph_repo.get_node_neighbors = AsyncMock(return_value=[])
    impact_service.triage_repo.list_triage_history = AsyncMock(return_value=[])

    mock_json_payload = {
        "technical_impact_summary": "Full compromise of web application server host.",
        "executive_impact_summary": "Critical threat to customer data confidentiality and business operational continuity.",
        "risk_justification": "Maximum risk rating driven by high EPSS exploit probability (92%) and unauthenticated remote code execution.",
        "affected_business_components": "Core Payment Processing Service and User File Vault.",
        "cvss_interpretation": "CVSS 9.8 Critical rating reflecting complete destruction of system authorization boundaries.",
        "epss_context": "92nd percentile exploit probability indicating active threat actor targeting.",
        "exposure_assessment": "Publicly exposed Internet facing API endpoint without access control restrictions.",
        "evidence_correlation": "Proof-of-exploit HTTP request dump confirms remote shell execution.",
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="claude-3-5-sonnet",
        provider_used="ANTHROPIC",
        prompt_tokens=250,
        completion_tokens=300,
        total_tokens=550,
        latency_ms=600,
        cost_usd=0.008,
        status="SUCCESS",
    )

    impact_service.gateway_service.generate_completion = AsyncMock(
        return_value=mock_completion_resp
    )
    impact_service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    impact_service.ai_analysis_repo.create_impact_analysis = AsyncMock()
    impact_service.audit_service.record_event = AsyncMock()

    mock_created_model = MagicMock()
    mock_created_model.id = uuid4()
    mock_created_model.finding_id = finding_id
    mock_created_model.technical_impact_summary = mock_json_payload[
        "technical_impact_summary"
    ]
    mock_created_model.executive_impact_summary = mock_json_payload[
        "executive_impact_summary"
    ]
    mock_created_model.risk_justification = mock_json_payload["risk_justification"]
    mock_created_model.affected_business_components = mock_json_payload[
        "affected_business_components"
    ]
    mock_created_model.cvss_interpretation = mock_json_payload["cvss_interpretation"]
    mock_created_model.epss_context = mock_json_payload["epss_context"]
    mock_created_model.exposure_assessment = mock_json_payload["exposure_assessment"]
    mock_created_model.evidence_correlation = mock_json_payload["evidence_correlation"]
    mock_created_model.model_used = "claude-3-5-sonnet"
    mock_created_model.provider_used = "ANTHROPIC"
    mock_created_model.prompt_version = 1
    mock_created_model.status = "COMPLETED"
    mock_created_model.created_at = "2026-08-03T12:00:00Z"
    impact_service.ai_analysis_repo.create_impact_analysis.return_value = (
        mock_created_model
    )

    dto = await impact_service.generate_impact_analysis(org_id, finding_id, actor_id)

    assert dto.finding_id == str(finding_id)
    assert dto.executive_impact_summary == mock_json_payload["executive_impact_summary"]
    assert dto.model_used == "claude-3-5-sonnet"
    assert dto.provider_used == "ANTHROPIC"
    assert dto.status == "COMPLETED"


@pytest.mark.anyio
async def test_explainer_retry_on_malformed_json() -> None:
    """Test retry-once recovery strategy when initial LLM response contains malformed JSON."""
    mock_session = MagicMock()
    explainer_service = AIFindingExplainerService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="xss_plugin",
        title="Reflected XSS",
        description="Reflected XSS in search parameter.",
        severity="MEDIUM",
        category="INJECTION",
    )

    explainer_service.assessment_repo.get_finding_by_id = AsyncMock(
        return_value=mock_finding
    )
    explainer_service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    explainer_service.triage_repo.list_triage_history = AsyncMock(return_value=[])

    # Initial malformed non-JSON response
    malformed_resp = AIChatCompletionResponse(
        content="Here is your analysis:\nSummary: Reflected XSS\nRoot cause: Unescaped output",
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        latency_ms=200,
        cost_usd=0.001,
        status="SUCCESS",
    )

    # Repaired JSON response from retry attempt
    repaired_json = {
        "vulnerability_summary": "Reflected XSS in search parameter.",
        "technical_root_cause": "Unescaped HTML output injection.",
        "affected_asset_context": "Search page URL query string.",
        "exploitability_analysis": "Requires user interaction via phishing link.",
        "business_impact": "Session hijacking of non-HTTPOnly cookie tokens.",
        "attack_prerequisites": "Victim clicking crafted link.",
        "severity_reasoning": "Medium CVSS rating due to required user interaction.",
        "remediation_priority": "P3 - Fix in next sprint release.",
    }

    repaired_resp = AIChatCompletionResponse(
        content=json.dumps(repaired_json),
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=80,
        completion_tokens=120,
        total_tokens=200,
        latency_ms=250,
        cost_usd=0.002,
        status="SUCCESS",
    )

    # First call returns malformed, second call returns repaired JSON
    explainer_service.gateway_service.generate_completion = AsyncMock(
        side_effect=[malformed_resp, repaired_resp]
    )
    explainer_service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    explainer_service.audit_service.record_event = AsyncMock()

    mock_created_model = MagicMock()
    mock_created_model.id = uuid4()
    mock_created_model.finding_id = finding_id
    mock_created_model.vulnerability_summary = repaired_json["vulnerability_summary"]
    mock_created_model.technical_root_cause = repaired_json["technical_root_cause"]
    mock_created_model.affected_asset_context = repaired_json["affected_asset_context"]
    mock_created_model.exploitability_analysis = repaired_json[
        "exploitability_analysis"
    ]
    mock_created_model.business_impact = repaired_json["business_impact"]
    mock_created_model.attack_prerequisites = repaired_json["attack_prerequisites"]
    mock_created_model.severity_reasoning = repaired_json["severity_reasoning"]
    mock_created_model.remediation_priority = repaired_json["remediation_priority"]
    mock_created_model.model_used = "gpt-4o"
    mock_created_model.provider_used = "OPENAI"
    mock_created_model.prompt_version = 1
    mock_created_model.status = "COMPLETED"
    mock_created_model.created_at = "2026-08-03T12:00:00Z"
    explainer_service.ai_analysis_repo.create_explanation = AsyncMock(
        return_value=mock_created_model
    )

    dto = await explainer_service.generate_explanation(org_id, finding_id, actor_id)

    assert dto.status == "COMPLETED"
    assert dto.vulnerability_summary == repaired_json["vulnerability_summary"]
    # Verify gateway generate_completion was called TWICE (initial + repair retry)
    assert explainer_service.gateway_service.generate_completion.call_count == 2


@pytest.mark.anyio
async def test_explainer_persists_failed_status_when_repair_fails() -> None:
    """Test persisting FAILED status record when LLM response remains unparseable after retry."""
    mock_session = MagicMock()
    explainer_service = AIFindingExplainerService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="bad_plugin",
        title="Bad Finding",
        description="Bad description",
        severity="LOW",
        category="OTHER",
    )

    explainer_service.assessment_repo.get_finding_by_id = AsyncMock(
        return_value=mock_finding
    )
    explainer_service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    explainer_service.triage_repo.list_triage_history = AsyncMock(return_value=[])

    malformed_resp = AIChatCompletionResponse(
        content="Not JSON text at all",
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        latency_ms=200,
        cost_usd=0.001,
        status="SUCCESS",
    )

    # Both initial and retry attempts return non-JSON text
    explainer_service.gateway_service.generate_completion = AsyncMock(
        return_value=malformed_resp
    )
    explainer_service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )

    mock_failed_model = MagicMock()
    mock_failed_model.id = uuid4()
    mock_failed_model.finding_id = finding_id
    mock_failed_model.vulnerability_summary = ""
    mock_failed_model.technical_root_cause = ""
    mock_failed_model.affected_asset_context = ""
    mock_failed_model.exploitability_analysis = ""
    mock_failed_model.business_impact = ""
    mock_failed_model.attack_prerequisites = ""
    mock_failed_model.severity_reasoning = ""
    mock_failed_model.remediation_priority = ""
    mock_failed_model.model_used = "gpt-4o"
    mock_failed_model.provider_used = "OPENAI"
    mock_failed_model.prompt_version = 1
    mock_failed_model.status = "FAILED"
    mock_failed_model.created_at = "2026-08-03T12:00:00Z"
    explainer_service.ai_analysis_repo.create_explanation = AsyncMock(
        return_value=mock_failed_model
    )

    dto = await explainer_service.generate_explanation(org_id, finding_id, actor_id)

    assert dto.status == "FAILED"
    assert explainer_service.ai_analysis_repo.create_explanation.called


@pytest.mark.anyio
async def test_ai_analysis_repository_crud() -> None:
    """Test AIAnalysisRepository tenant-isolated creation and retrieval queries."""
    mock_session = AsyncMock()
    repo = AIAnalysisRepository(mock_session)

    org_id = uuid4()
    finding_id = uuid4()

    # Test create_explanation
    await repo.create_explanation(
        organization_id=org_id,
        finding_id=finding_id,
        vulnerability_summary="Summary",
        technical_root_cause="Cause",
        affected_asset_context="Asset",
        exploitability_analysis="Exploit",
        business_impact="Impact",
        attack_prerequisites="Prereqs",
        severity_reasoning="Reasoning",
        remediation_priority="Priority",
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_version=1,
    )
    assert mock_session.add.called
    assert mock_session.flush.called

    # Test create_impact_analysis
    await repo.create_impact_analysis(
        organization_id=org_id,
        finding_id=finding_id,
        technical_impact_summary="Tech impact",
        executive_impact_summary="Exec impact",
        risk_justification="Risk rationale",
        affected_business_components="Components",
        cvss_interpretation="CVSS notes",
        epss_context="EPSS notes",
        exposure_assessment="Exposure",
        evidence_correlation="Evidence notes",
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_version=1,
    )
    assert mock_session.add.call_count == 2


@pytest.mark.anyio
async def test_explanation_retrieval_returns_latest() -> None:
    """Test retrieving most recent explanation for a finding."""
    mock_session = MagicMock()
    explainer_service = AIFindingExplainerService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()

    mock_explanation_model = MagicMock()
    mock_explanation_model.id = uuid4()
    mock_explanation_model.finding_id = finding_id
    mock_explanation_model.vulnerability_summary = "Latest summary"
    mock_explanation_model.technical_root_cause = "Latest cause"
    mock_explanation_model.affected_asset_context = "Asset"
    mock_explanation_model.exploitability_analysis = "Exploit"
    mock_explanation_model.business_impact = "Impact"
    mock_explanation_model.attack_prerequisites = "Prereqs"
    mock_explanation_model.severity_reasoning = "Reasoning"
    mock_explanation_model.remediation_priority = "Priority"
    mock_explanation_model.model_used = "gpt-4o"
    mock_explanation_model.provider_used = "OPENAI"
    mock_explanation_model.prompt_version = 2
    mock_explanation_model.status = "COMPLETED"
    mock_explanation_model.created_at = "2026-08-03T12:00:00Z"

    explainer_service.ai_analysis_repo.get_explanation_by_finding = AsyncMock(
        return_value=mock_explanation_model
    )

    dto = await explainer_service.get_explanation(org_id, finding_id)

    assert dto is not None
    assert dto.vulnerability_summary == "Latest summary"
    assert dto.prompt_version == 2


@pytest.mark.anyio
async def test_tenant_boundary_isolation_on_explanation_retrieval() -> None:
    """Test that explanation retrieval for non-existent or cross-tenant finding returns None."""
    mock_session = MagicMock()
    explainer_service = AIFindingExplainerService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()

    explainer_service.ai_analysis_repo.get_explanation_by_finding = AsyncMock(
        return_value=None
    )

    dto = await explainer_service.get_explanation(org_id, finding_id)

    assert dto is None
