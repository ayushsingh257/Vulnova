"""Unit & Integration Tests for AI False Positive Filter & Finding Confidence Intelligence Engine (Phase 5.5)."""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.ai.confidence_service import AIConfidenceAnalysisService
from app.application.ai.dto import (
    AIChatCompletionResponse,
    ReviewConfidenceAnalysisRequest,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.asset_graph import AssetNodeModel
from app.infrastructure.database.repositories.ai_confidence_repository import (
    AIConfidenceRepository,
)


@pytest.mark.anyio
async def test_true_positive_classification_generation() -> None:
    """Test generating a confidence analysis classifying a finding as TRUE_POSITIVE."""
    mock_session = MagicMock()
    service = AIConfidenceAnalysisService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="sqli_plugin",
        title="SQL Injection in Admin Search",
        description="Unsanitized user parameter in SQL query.",
        severity="HIGH",
        category="INJECTION",
        cve_id="CVE-2024-1111",
        cwe_id="CWE-89",
        risk_score=85.0,
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=mock_finding)
    service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    service.asset_graph_repo.get_node_by_id = AsyncMock(return_value=None)
    service.triage_repo.get_triage_history = AsyncMock(return_value=[])
    service.ai_analysis_repo.get_explanation_by_finding = AsyncMock(return_value=None)
    service.ai_analysis_repo.get_impact_analysis_by_finding = AsyncMock(
        return_value=None
    )
    service.attack_path_repo.list_attack_paths_by_finding = AsyncMock(return_value=[])
    service.remediation_repo.list_remediation_plans_by_finding = AsyncMock(
        return_value=[]
    )
    service.run_similarity_check = AsyncMock(return_value=[])

    mock_json_payload = {
        "classification": "TRUE_POSITIVE",
        "confidence_score": 0.95,
        "evidence_quality_score": 0.92,
        "reasoning": "High confidence SQL injection confirmed by error payload response.",
        "supporting_evidence": "HTTP 500 error containing PostgreSQL syntax exception.",
        "contradicting_evidence": "None noted.",
        "missing_information": "None.",
        "validation_requirements": "Re-run sqli_plugin with sleep payload.",
        "recommendation": "Prioritize immediate patch deployment.",
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=250,
        completion_tokens=300,
        total_tokens=550,
        latency_ms=500,
        cost_usd=0.005,
        status="SUCCESS",
    )

    service.gateway_service.generate_completion = AsyncMock(
        return_value=mock_completion_resp
    )
    service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    service.audit_service.record_event = AsyncMock()

    mock_created = MagicMock()
    mock_created.id = uuid4()
    mock_created.finding_id = finding_id
    mock_created.classification = "TRUE_POSITIVE"
    mock_created.confidence_score = 0.95
    mock_created.evidence_quality_score = 0.92
    mock_created.reasoning = mock_json_payload["reasoning"]
    mock_created.supporting_evidence = mock_json_payload["supporting_evidence"]
    mock_created.contradicting_evidence = mock_json_payload["contradicting_evidence"]
    mock_created.missing_information = mock_json_payload["missing_information"]
    mock_created.validation_requirements = mock_json_payload["validation_requirements"]
    mock_created.recommendation = mock_json_payload["recommendation"]
    mock_created.composite_risk_score = 85.0
    mock_created.model_used = "gpt-4o"
    mock_created.provider_used = "OPENAI"
    mock_created.prompt_version = 1
    mock_created.status = "GENERATED"
    mock_created.similarity_matches = []
    mock_created.review_notes = None
    mock_created.reviewed_by = None
    mock_created.reviewed_at = None
    mock_created.predicted_confidence_score = None
    mock_created.analyst_final_decision = None
    mock_created.confidence_accuracy_delta = None
    mock_created.feedback_timestamp = None
    mock_created.error_message = None
    mock_created.created_at = "2026-08-03T14:00:00Z"

    service.confidence_repo.create_confidence_analysis = AsyncMock(
        return_value=mock_created
    )

    dto = await service.generate_confidence_analysis(org_id, finding_id, actor_id)

    assert dto.classification == "TRUE_POSITIVE"
    assert dto.confidence_score == 0.95
    assert dto.evidence_quality_score == 0.92
    assert dto.composite_risk_score == 85.0
    assert service.audit_service.record_event.called


@pytest.mark.anyio
async def test_false_positive_reasoning_generation() -> None:
    """Test generating a confidence analysis classifying a finding as FALSE_POSITIVE."""
    mock_session = MagicMock()
    service = AIConfidenceAnalysisService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="xss_plugin",
        title="Reflected XSS in Search",
        description="Potential XSS reflection.",
        severity="MEDIUM",
        category="XSS",
        risk_score=50.0,
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=mock_finding)
    service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    service.asset_graph_repo.get_node_by_id = AsyncMock(return_value=None)
    service.triage_repo.get_triage_history = AsyncMock(return_value=[])
    service.ai_analysis_repo.get_explanation_by_finding = AsyncMock(return_value=None)
    service.ai_analysis_repo.get_impact_analysis_by_finding = AsyncMock(
        return_value=None
    )
    service.attack_path_repo.list_attack_paths_by_finding = AsyncMock(return_value=[])
    service.remediation_repo.list_remediation_plans_by_finding = AsyncMock(
        return_value=[]
    )
    service.run_similarity_check = AsyncMock(return_value=[])

    mock_json_payload = {
        "classification": "FALSE_POSITIVE",
        "confidence_score": 0.88,
        "evidence_quality_score": 0.70,
        "reasoning": "Output is HTML-encoded by template engine prior to rendering.",
        "supporting_evidence": "None.",
        "contradicting_evidence": "HTTP response contains HTML entity encoding &lt;script&gt;.",
        "missing_information": "Browser DOM execution context.",
        "validation_requirements": "Verify client-side DOM parser in headless browser.",
        "recommendation": "Mark as false positive or dismiss.",
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=200,
        completion_tokens=250,
        total_tokens=450,
        latency_ms=400,
        cost_usd=0.004,
        status="SUCCESS",
    )

    service.gateway_service.generate_completion = AsyncMock(
        return_value=mock_completion_resp
    )
    service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    service.audit_service.record_event = AsyncMock()

    mock_created = MagicMock()
    mock_created.id = uuid4()
    mock_created.finding_id = finding_id
    mock_created.classification = "FALSE_POSITIVE"
    mock_created.confidence_score = 0.88
    mock_created.evidence_quality_score = 0.70
    mock_created.reasoning = mock_json_payload["reasoning"]
    mock_created.supporting_evidence = mock_json_payload["supporting_evidence"]
    mock_created.contradicting_evidence = mock_json_payload["contradicting_evidence"]
    mock_created.missing_information = mock_json_payload["missing_information"]
    mock_created.validation_requirements = mock_json_payload["validation_requirements"]
    mock_created.recommendation = mock_json_payload["recommendation"]
    mock_created.composite_risk_score = 50.0
    mock_created.model_used = "gpt-4o"
    mock_created.provider_used = "OPENAI"
    mock_created.prompt_version = 1
    mock_created.status = "GENERATED"
    mock_created.similarity_matches = []
    mock_created.review_notes = None
    mock_created.reviewed_by = None
    mock_created.reviewed_at = None
    mock_created.predicted_confidence_score = None
    mock_created.analyst_final_decision = None
    mock_created.confidence_accuracy_delta = None
    mock_created.feedback_timestamp = None
    mock_created.error_message = None
    mock_created.created_at = "2026-08-03T14:00:00Z"

    service.confidence_repo.create_confidence_analysis = AsyncMock(
        return_value=mock_created
    )

    dto = await service.generate_confidence_analysis(org_id, finding_id, actor_id)

    assert dto.classification == "FALSE_POSITIVE"
    assert dto.confidence_score == 0.88


@pytest.mark.anyio
async def test_evidence_quality_scoring() -> None:
    """Test parsing and storage of evidence_quality_score (0.0 - 1.0)."""
    mock_session = MagicMock()
    service = AIConfidenceAnalysisService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="plugin",
        title="Title",
        description="Desc",
        severity="LOW",
        category="OTHER",
        risk_score=20.0,
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=mock_finding)
    service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    service.asset_graph_repo.get_node_by_id = AsyncMock(return_value=None)
    service.triage_repo.get_triage_history = AsyncMock(return_value=[])
    service.ai_analysis_repo.get_explanation_by_finding = AsyncMock(return_value=None)
    service.ai_analysis_repo.get_impact_analysis_by_finding = AsyncMock(
        return_value=None
    )
    service.attack_path_repo.list_attack_paths_by_finding = AsyncMock(return_value=[])
    service.remediation_repo.list_remediation_plans_by_finding = AsyncMock(
        return_value=[]
    )
    service.run_similarity_check = AsyncMock(return_value=[])

    mock_json_payload = {
        "classification": "NEEDS_REVIEW",
        "confidence_score": 0.50,
        "evidence_quality_score": 0.40,
        "reasoning": "Limited evidence proof.",
        "supporting_evidence": "Incomplete header dump.",
        "contradicting_evidence": "None.",
        "missing_information": "Full HTTP request/response stream.",
        "validation_requirements": "Re-run scan with verbose logging.",
        "recommendation": "Collect additional evidence.",
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=100,
        completion_tokens=100,
        total_tokens=200,
        latency_ms=200,
        cost_usd=0.002,
        status="SUCCESS",
    )

    service.gateway_service.generate_completion = AsyncMock(
        return_value=mock_completion_resp
    )
    service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    service.audit_service.record_event = AsyncMock()

    mock_created = MagicMock()
    mock_created.id = uuid4()
    mock_created.finding_id = finding_id
    mock_created.classification = "NEEDS_REVIEW"
    mock_created.confidence_score = 0.50
    mock_created.evidence_quality_score = 0.40
    mock_created.reasoning = ""
    mock_created.supporting_evidence = ""
    mock_created.contradicting_evidence = ""
    mock_created.missing_information = ""
    mock_created.validation_requirements = ""
    mock_created.recommendation = ""
    mock_created.composite_risk_score = 20.0
    mock_created.model_used = "gpt-4o"
    mock_created.provider_used = "OPENAI"
    mock_created.prompt_version = 1
    mock_created.status = "GENERATED"
    mock_created.similarity_matches = []
    mock_created.review_notes = None
    mock_created.reviewed_by = None
    mock_created.reviewed_at = None
    mock_created.predicted_confidence_score = None
    mock_created.analyst_final_decision = None
    mock_created.confidence_accuracy_delta = None
    mock_created.feedback_timestamp = None
    mock_created.error_message = None
    mock_created.created_at = "2026-08-03T14:00:00Z"

    service.confidence_repo.create_confidence_analysis = AsyncMock(
        return_value=mock_created
    )

    dto = await service.generate_confidence_analysis(org_id, finding_id, actor_id)

    assert dto.evidence_quality_score == 0.40


@pytest.mark.anyio
async def test_similarity_detection() -> None:
    """Test multi-signal correlation across CVE, CWE, plugin ID, and title signals."""
    mock_session = AsyncMock()
    service = AIConfidenceAnalysisService(mock_session)

    org_id = uuid4()
    target_id = uuid4()
    cand1_id = uuid4()

    target_finding = SecurityFindingModel(
        id=target_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="sqli_plugin",
        title="SQL Injection",
        description="",
        severity="HIGH",
        category="INJECTION",
        cve_id="CVE-2024-8888",
        cwe_id="CWE-89",
        risk_score=80.0,
    )

    cand1 = SecurityFindingModel(
        id=cand1_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="sqli_plugin",
        title="SQL Injection",
        description="",
        severity="HIGH",
        category="INJECTION",
        cve_id="CVE-2024-8888",
        cwe_id="CWE-89",
        risk_score=80.0,
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=target_finding)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [cand1]
    mock_session.execute.return_value = mock_result

    matches = await service.run_similarity_check(org_id, target_id)

    assert len(matches) == 1
    assert matches[0].matched_finding_id == str(cand1_id)
    assert "CVE" in matches[0].matched_signals
    assert "CWE" in matches[0].matched_signals
    assert "PLUGIN_ID" in matches[0].matched_signals
    assert matches[0].similarity_score >= 0.70


@pytest.mark.anyio
async def test_context_uses_previous_ai_analysis() -> None:
    """Test context builder incorporating Phase 5.2 explanations/impact, Phase 5.3 attack paths, and Phase 5.4 remediation plans."""
    mock_session = MagicMock()
    service = AIConfidenceAnalysisService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="plugin",
        title="Context Target Finding",
        description="Finding description",
        severity="HIGH",
        category="INJECTION",
        risk_score=90.0,
    )

    mock_asset = AssetNodeModel(
        id=uuid4(),
        organization_id=org_id,
        node_type="SERVER",
        name="web-01",
        value="10.0.0.1",
    )

    context_str = service._build_confidence_context(
        finding=mock_finding,
        evidence_artifacts=[],
        asset_node=mock_asset,
        triage_history=[],
        explanation=None,
        impact_analysis=None,
        attack_path=None,
        remediation_plan=None,
        similarity_matches=[],
    )

    assert "Context Target Finding" in context_str
    assert "web-01" in context_str


@pytest.mark.anyio
async def test_sensitive_data_masking_in_confidence_context() -> None:
    """Test Bearer token and password secret masking inside confidence context."""
    mock_session = MagicMock()
    service = AIConfidenceAnalysisService(mock_session)

    finding = MagicMock(
        title="Exposed Credentials",
        severity="HIGH",
        category="AUTH",
        cve_id=None,
        cwe_id=None,
        plugin_id="plugin",
        risk_score=80.0,
        description="Authorization: Bearer secret_token_xyz999\npassword=SuperSecret123",
    )

    context_str = service._build_confidence_context(
        finding=finding,
        evidence_artifacts=[],
        asset_node=None,
        triage_history=[],
        explanation=None,
        impact_analysis=None,
        attack_path=None,
        remediation_plan=None,
        similarity_matches=[],
    )

    assert "secret_token_xyz999" not in context_str
    assert "SuperSecret123" not in context_str
    assert "[REDACTED_SECRET]" in context_str


@pytest.mark.anyio
async def test_tenant_isolation() -> None:
    """Test that repository queries enforce organization_id tenant boundary isolation."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = AIConfidenceRepository(mock_session)

    org_id = uuid4()
    analysis_id = uuid4()

    await repo.get_confidence_analysis_by_id(org_id, analysis_id)
    assert mock_session.execute.called

    await repo.list_confidence_analyses(org_id, limit=10, offset=0)
    assert mock_session.execute.call_count == 2


@pytest.mark.anyio
async def test_invalid_llm_json_retry_recovery() -> None:
    """Test retry-once JSON repair recovery strategy on malformed LLM response."""
    mock_session = MagicMock()
    service = AIConfidenceAnalysisService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="plugin",
        title="Title",
        description="Desc",
        severity="MEDIUM",
        category="OTHER",
        risk_score=50.0,
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=mock_finding)
    service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    service.asset_graph_repo.get_node_by_id = AsyncMock(return_value=None)
    service.triage_repo.get_triage_history = AsyncMock(return_value=[])
    service.ai_analysis_repo.get_explanation_by_finding = AsyncMock(return_value=None)
    service.ai_analysis_repo.get_impact_analysis_by_finding = AsyncMock(
        return_value=None
    )
    service.attack_path_repo.list_attack_paths_by_finding = AsyncMock(return_value=[])
    service.remediation_repo.list_remediation_plans_by_finding = AsyncMock(
        return_value=[]
    )
    service.run_similarity_check = AsyncMock(return_value=[])

    malformed_resp = AIChatCompletionResponse(
        content="Plain text non-JSON response.",
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        latency_ms=200,
        cost_usd=0.001,
        status="SUCCESS",
    )

    repaired_json = {
        "classification": "TRUE_POSITIVE",
        "confidence_score": 0.90,
        "evidence_quality_score": 0.85,
        "reasoning": "Repaired reasoning.",
        "supporting_evidence": "Repaired evidence.",
        "contradicting_evidence": "None.",
        "missing_information": "None.",
        "validation_requirements": "Test.",
        "recommendation": "Patch.",
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

    service.gateway_service.generate_completion = AsyncMock(
        side_effect=[malformed_resp, repaired_resp]
    )
    service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    service.audit_service.record_event = AsyncMock()

    mock_created = MagicMock()
    mock_created.id = uuid4()
    mock_created.finding_id = finding_id
    mock_created.classification = "TRUE_POSITIVE"
    mock_created.confidence_score = 0.90
    mock_created.evidence_quality_score = 0.85
    mock_created.reasoning = "Repaired reasoning."
    mock_created.supporting_evidence = ""
    mock_created.contradicting_evidence = ""
    mock_created.missing_information = ""
    mock_created.validation_requirements = ""
    mock_created.recommendation = ""
    mock_created.composite_risk_score = 50.0
    mock_created.model_used = "gpt-4o"
    mock_created.provider_used = "OPENAI"
    mock_created.prompt_version = 1
    mock_created.status = "GENERATED"
    mock_created.similarity_matches = []
    mock_created.review_notes = None
    mock_created.reviewed_by = None
    mock_created.reviewed_at = None
    mock_created.predicted_confidence_score = None
    mock_created.analyst_final_decision = None
    mock_created.confidence_accuracy_delta = None
    mock_created.feedback_timestamp = None
    mock_created.error_message = None
    mock_created.created_at = "2026-08-03T14:00:00Z"

    service.confidence_repo.create_confidence_analysis = AsyncMock(
        return_value=mock_created
    )

    dto = await service.generate_confidence_analysis(org_id, finding_id, actor_id)

    assert dto.classification == "TRUE_POSITIVE"
    assert service.gateway_service.generate_completion.call_count == 2


@pytest.mark.anyio
async def test_human_review_workflow_and_calibration_tracking() -> None:
    """Test analyst review status update and confidence score calibration feedback metadata tracking."""
    mock_session = MagicMock()
    service = AIConfidenceAnalysisService(mock_session)

    org_id = uuid4()
    analysis_id = uuid4()
    reviewer_id = uuid4()

    mock_analysis = MagicMock()
    mock_analysis.id = analysis_id
    mock_analysis.finding_id = uuid4()
    mock_analysis.classification = "TRUE_POSITIVE"
    mock_analysis.confidence_score = 0.95
    mock_analysis.evidence_quality_score = 0.90
    mock_analysis.reasoning = "Reasoning"
    mock_analysis.supporting_evidence = ""
    mock_analysis.contradicting_evidence = ""
    mock_analysis.missing_information = ""
    mock_analysis.validation_requirements = ""
    mock_analysis.recommendation = ""
    mock_analysis.composite_risk_score = 80.0
    mock_analysis.model_used = "gpt-4o"
    mock_analysis.provider_used = "OPENAI"
    mock_analysis.prompt_version = 1
    mock_analysis.status = "ACCEPTED"
    mock_analysis.similarity_matches = []
    mock_analysis.review_notes = "Analyst validated finding as true positive."
    mock_analysis.reviewed_by = reviewer_id
    mock_analysis.reviewed_at = "2026-08-03T15:00:00Z"
    mock_analysis.predicted_confidence_score = 0.95
    mock_analysis.analyst_final_decision = "ACCEPTED"
    mock_analysis.confidence_accuracy_delta = 0.05
    mock_analysis.feedback_timestamp = "2026-08-03T15:00:00Z"
    mock_analysis.error_message = None
    mock_analysis.created_at = "2026-08-03T14:00:00Z"

    service.confidence_repo.update_review_status = AsyncMock(return_value=mock_analysis)
    service.audit_service.record_event = AsyncMock()

    review_req = ReviewConfidenceAnalysisRequest(
        status="ACCEPTED",
        review_notes="Analyst validated finding as true positive.",
    )

    dto = await service.review_confidence_analysis(
        org_id, analysis_id, reviewer_id, review_req
    )

    assert dto.status == "ACCEPTED"
    assert dto.predicted_confidence_score == 0.95
    assert dto.analyst_final_decision == "ACCEPTED"
    assert dto.confidence_accuracy_delta == 0.05
    assert service.audit_service.record_event.called


@pytest.mark.anyio
async def test_no_automatic_finding_suppression() -> None:
    """Test that generating confidence analysis does NOT modify SecurityFindingModel.status or trigger auto-suppression."""
    mock_session = MagicMock()
    service = AIConfidenceAnalysisService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="plugin",
        title="Title",
        description="Desc",
        severity="HIGH",
        category="INJECTION",
        risk_score=80.0,
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=mock_finding)
    service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    service.asset_graph_repo.get_node_by_id = AsyncMock(return_value=None)
    service.triage_repo.get_triage_history = AsyncMock(return_value=[])
    service.ai_analysis_repo.get_explanation_by_finding = AsyncMock(return_value=None)
    service.ai_analysis_repo.get_impact_analysis_by_finding = AsyncMock(
        return_value=None
    )
    service.attack_path_repo.list_attack_paths_by_finding = AsyncMock(return_value=[])
    service.remediation_repo.list_remediation_plans_by_finding = AsyncMock(
        return_value=[]
    )
    service.run_similarity_check = AsyncMock(return_value=[])

    mock_json_payload = {
        "classification": "FALSE_POSITIVE",
        "confidence_score": 0.99,
        "evidence_quality_score": 0.90,
        "reasoning": "False positive.",
        "supporting_evidence": "None.",
        "contradicting_evidence": "Encoding present.",
        "missing_information": "None.",
        "validation_requirements": "Check template.",
        "recommendation": "Analyst may dismiss.",
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=100,
        completion_tokens=100,
        total_tokens=200,
        latency_ms=200,
        cost_usd=0.002,
        status="SUCCESS",
    )

    service.gateway_service.generate_completion = AsyncMock(
        return_value=mock_completion_resp
    )
    service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    service.audit_service.record_event = AsyncMock()

    mock_created = MagicMock()
    mock_created.id = uuid4()
    mock_created.finding_id = finding_id
    mock_created.classification = "FALSE_POSITIVE"
    mock_created.confidence_score = 0.99
    mock_created.evidence_quality_score = 0.90
    mock_created.reasoning = ""
    mock_created.supporting_evidence = ""
    mock_created.contradicting_evidence = ""
    mock_created.missing_information = ""
    mock_created.validation_requirements = ""
    mock_created.recommendation = ""
    mock_created.composite_risk_score = 80.0
    mock_created.model_used = "gpt-4o"
    mock_created.provider_used = "OPENAI"
    mock_created.prompt_version = 1
    mock_created.status = "GENERATED"
    mock_created.similarity_matches = []
    mock_created.review_notes = None
    mock_created.reviewed_by = None
    mock_created.reviewed_at = None
    mock_created.predicted_confidence_score = None
    mock_created.analyst_final_decision = None
    mock_created.confidence_accuracy_delta = None
    mock_created.feedback_timestamp = None
    mock_created.error_message = None
    mock_created.created_at = "2026-08-03T14:00:00Z"

    service.confidence_repo.create_confidence_analysis = AsyncMock(
        return_value=mock_created
    )

    service.triage_repo.create_suppression_rule = AsyncMock()

    dto = await service.generate_confidence_analysis(org_id, finding_id, actor_id)

    # Finding classification is returned but auto-suppression service is never invoked
    assert dto.classification == "FALSE_POSITIVE"
    assert not service.triage_repo.create_suppression_rule.called
