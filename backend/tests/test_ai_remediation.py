"""Unit & Integration Tests for AI Remediation Engine & Intelligent Fix Recommendation System (Phase 5.4)."""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.ai.dto import (
    AIChatCompletionResponse,
    ReviewRemediationPlanRequest,
)
from app.application.ai.remediation_service import AIRemediationService
from app.infrastructure.database.models.ai_analysis import (
    AIFindingExplanationModel,
    AIImpactAnalysisModel,
)
from app.infrastructure.database.models.ai_attack_path import AIAttackPathModel
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.asset_graph import AssetNodeModel
from app.infrastructure.database.repositories.ai_remediation_repository import (
    AIRemediationRepository,
)


@pytest.mark.anyio
async def test_remediation_generation_success() -> None:
    """Test generating a structured AI remediation plan with steps and non-executable patch suggestions."""
    mock_session = MagicMock()
    service = AIRemediationService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="sqli_plugin",
        title="SQL Injection in Admin Endpoint",
        description="Unsanitized SQL input in search parameter.",
        severity="HIGH",
        category="INJECTION",
        cve_id="CVE-2024-8888",
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

    mock_json_payload = {
        "title": "Remediation Plan: Parametrize SQL Queries",
        "summary": "Replace concatenated SQL strings with parameterized queries using SQLAlchemy ORM.",
        "technical_solution": "Use bound parameters in SQL query execution.",
        "business_solution": "Prevents unauthorized database access and data leakage.",
        "risk_reduction_explanation": "Eliminates SQL injection vulnerability completely.",
        "validation_strategy": "Re-run SQL injection assessment plugin against /admin endpoint.",
        "ai_confidence_score": 0.96,
        "effectiveness_confidence_score": 0.98,
        "requires_backup": True,
        "requires_downtime": False,
        "rollback_available": True,
        "cve_id": "CVE-2024-8888",
        "cwe_id": "CWE-89",
        "affected_version": "1.2.0",
        "fixed_version": "1.2.1",
        "steps": [
            {
                "sequence_number": 1,
                "step_type": "CODE_PATCH",
                "title": "Parametrize SQL query in auth.py",
                "description": "Refactor raw cursor.execute() to use ORM query binding.",
                "affected_component": "backend/app/api/v1/auth.py",
                "recommended_action": "Update query line 45 to use bound parameter :username",
                "validation_command": "pytest tests/test_auth.py",
                "rollback_strategy": "Git revert commit",
                "confidence_score": 0.95,
            }
        ],
        "patch_suggestions": [
            {
                "language": "PYTHON",
                "file_type": "SOURCE_CODE",
                "target_file_path": "backend/app/api/v1/auth.py",
                "original_code_snippet": "cursor.execute(f'SELECT * FROM users WHERE name={name}')",
                "proposed_patch_diff": "--- auth.py\n+++ auth.py\n-cursor.execute(f'SELECT * FROM users WHERE name={name}')\n+cursor.execute('SELECT * FROM users WHERE name=:name', {'name': name})",
                "explanation": "Replaces string interpolation with parameter binding.",
                "security_impact_notes": "Completely mitigates SQL injection.",
                "confidence_score": 0.97,
            }
        ],
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=300,
        completion_tokens=400,
        total_tokens=700,
        latency_ms=600,
        cost_usd=0.008,
        status="SUCCESS",
    )

    service.gateway_service.generate_completion = AsyncMock(
        return_value=mock_completion_resp
    )
    service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    service.audit_service.record_event = AsyncMock()

    mock_created_plan = MagicMock()
    mock_created_plan.id = uuid4()
    mock_created_plan.root_finding_id = finding_id
    mock_created_plan.attack_path_id = None
    mock_created_plan.cve_id = "CVE-2024-8888"
    mock_created_plan.cwe_id = "CWE-89"
    mock_created_plan.affected_version = "1.2.0"
    mock_created_plan.fixed_version = "1.2.1"
    mock_created_plan.title = mock_json_payload["title"]
    mock_created_plan.summary = mock_json_payload["summary"]
    mock_created_plan.technical_solution = mock_json_payload["technical_solution"]
    mock_created_plan.business_solution = mock_json_payload["business_solution"]
    mock_created_plan.risk_reduction_explanation = mock_json_payload[
        "risk_reduction_explanation"
    ]
    mock_created_plan.validation_strategy = mock_json_payload["validation_strategy"]
    mock_created_plan.composite_risk_score = 85.0
    mock_created_plan.ai_confidence_score = 0.96
    mock_created_plan.effectiveness_confidence_score = 0.98
    mock_created_plan.requires_backup = True
    mock_created_plan.requires_downtime = False
    mock_created_plan.rollback_available = True
    mock_created_plan.model_used = "gpt-4o"
    mock_created_plan.provider_used = "OPENAI"
    mock_created_plan.prompt_version = 1
    mock_created_plan.status = "GENERATED"
    mock_created_plan.review_notes = None
    mock_created_plan.reviewed_by = None
    mock_created_plan.reviewed_at = None
    mock_created_plan.error_message = None
    mock_created_plan.created_at = "2026-08-03T14:00:00Z"

    mock_step1 = MagicMock(
        id=uuid4(),
        sequence_number=1,
        step_type="CODE_PATCH",
        title="Parametrize SQL query in auth.py",
        description="",
        affected_component="backend/app/api/v1/auth.py",
        recommended_action="",
        validation_command="pytest tests/test_auth.py",
        rollback_strategy="Git revert",
        confidence_score=0.95,
    )
    mock_patch1 = MagicMock(
        id=uuid4(),
        language="PYTHON",
        file_type="SOURCE_CODE",
        target_file_path="backend/app/api/v1/auth.py",
        original_code_snippet="",
        proposed_patch_diff="--- auth.py\n+++ auth.py",
        explanation="",
        security_impact_notes="",
        confidence_score=0.97,
    )

    mock_created_plan.steps = [mock_step1]
    mock_created_plan.patch_suggestions = [mock_patch1]

    service.remediation_repo.create_remediation_plan = AsyncMock(
        return_value=mock_created_plan
    )

    dto = await service.generate_remediation_plan(org_id, finding_id, actor_id)

    assert dto.root_finding_id == str(finding_id)
    assert dto.cve_id == "CVE-2024-8888"
    assert dto.ai_confidence_score == 0.96
    assert dto.effectiveness_confidence_score == 0.98
    assert dto.requires_backup is True
    assert len(dto.steps) == 1
    assert len(dto.patch_suggestions) == 1
    assert service.audit_service.record_event.called


@pytest.mark.anyio
async def test_remediation_uses_existing_risk_score() -> None:
    """Test that remediation engine reads composite risk score directly from finding without recalculating."""
    mock_session = MagicMock()
    service = AIRemediationService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="plugin",
        title="RCE Finding",
        description="RCE vulnerability.",
        severity="CRITICAL",
        category="INJECTION",
        risk_score=97.5,
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

    mock_json_payload = {
        "title": "Remediation",
        "summary": "Fix RCE",
        "technical_solution": "Patch",
        "business_solution": "Secure",
        "risk_reduction_explanation": "Eliminate RCE",
        "validation_strategy": "Test",
        "ai_confidence_score": 0.9,
        "effectiveness_confidence_score": 0.9,
        "steps": [],
        "patch_suggestions": [],
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

    captured_kwargs = {}

    async def mock_create(**kwargs):
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        mock_p = MagicMock()
        mock_p.id = uuid4()
        mock_p.root_finding_id = finding_id
        mock_p.attack_path_id = None
        mock_p.cve_id = None
        mock_p.cwe_id = None
        mock_p.affected_version = None
        mock_p.fixed_version = None
        mock_p.title = kwargs.get("title")
        mock_p.summary = kwargs.get("summary")
        mock_p.technical_solution = kwargs.get("technical_solution")
        mock_p.business_solution = kwargs.get("business_solution")
        mock_p.risk_reduction_explanation = kwargs.get("risk_reduction_explanation")
        mock_p.validation_strategy = kwargs.get("validation_strategy")
        mock_p.composite_risk_score = kwargs.get("composite_risk_score")
        mock_p.ai_confidence_score = 0.9
        mock_p.effectiveness_confidence_score = 0.9
        mock_p.requires_backup = False
        mock_p.requires_downtime = False
        mock_p.rollback_available = True
        mock_p.model_used = "gpt-4o"
        mock_p.provider_used = "OPENAI"
        mock_p.prompt_version = 1
        mock_p.status = "GENERATED"
        mock_p.steps = []
        mock_p.patch_suggestions = []
        mock_p.review_notes = None
        mock_p.reviewed_by = None
        mock_p.reviewed_at = None
        mock_p.error_message = None
        mock_p.created_at = "2026-08-03T14:00:00Z"
        return mock_p

    service.remediation_repo.create_remediation_plan = AsyncMock(
        side_effect=mock_create
    )

    await service.generate_remediation_plan(org_id, finding_id, actor_id)

    assert captured_kwargs["composite_risk_score"] == 97.5


@pytest.mark.anyio
async def test_remediation_context_contains_explanation_impact_and_attack_path() -> (
    None
):
    """Test that remediation context builder enriches prompt payload with explanation, impact, and attack path."""
    mock_session = MagicMock()
    service = AIRemediationService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="plugin",
        title="Target Finding Title",
        description="Finding Description",
        severity="HIGH",
        category="INJECTION",
        cve_id="CVE-2024-9999",
        cwe_id="CWE-89",
        risk_score=90.0,
    )

    mock_asset = AssetNodeModel(
        id=uuid4(),
        organization_id=org_id,
        node_type="SERVER",
        name="web-server-01",
        value="10.0.0.1",
    )

    mock_explanation = AIFindingExplanationModel(
        organization_id=org_id,
        finding_id=finding_id,
        vulnerability_summary="Vulnerability summary text.",
        technical_root_cause="Unbound variable execution.",
        affected_asset_context="",
        exploitability_analysis="",
        business_impact="",
        attack_prerequisites="",
        severity_reasoning="",
        remediation_priority="",
        model_used="gpt-4o",
        provider_used="OPENAI",
    )

    mock_impact = AIImpactAnalysisModel(
        organization_id=org_id,
        finding_id=finding_id,
        technical_impact_summary="Technical impact summary text.",
        executive_impact_summary="Executive impact summary text.",
        risk_justification="",
        affected_business_components="",
        cvss_interpretation="",
        epss_context="",
        exposure_assessment="",
        evidence_correlation="",
        model_used="gpt-4o",
        provider_used="OPENAI",
    )

    mock_attack_path = AIAttackPathModel(
        organization_id=org_id,
        root_finding_id=finding_id,
        title="Path from Web to DB",
        attack_summary="Attacker pivots across network boundary.",
        composite_risk_score=90.0,
        model_used="gpt-4o",
        provider_used="OPENAI",
    )

    context_str = service._build_remediation_context(
        finding=mock_finding,
        evidence_artifacts=[],
        asset_node=mock_asset,
        graph_relationships=[],
        triage_status="CONFIRMED",
        explanation=mock_explanation,
        impact_analysis=mock_impact,
        attack_path=mock_attack_path,
    )

    assert "Target Finding Title" in context_str
    assert "web-server-01" in context_str
    assert "Vulnerability summary text." in context_str
    assert "Technical impact summary text." in context_str
    assert "Path from Web to DB" in context_str


@pytest.mark.anyio
async def test_patch_generation_is_non_executable() -> None:
    """Test that patch suggestions are stored purely as text diffs without shell or git execution."""
    mock_session = MagicMock()
    service = AIRemediationService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="plugin",
        title="XSS Finding",
        description="Reflected XSS",
        severity="MEDIUM",
        category="XSS",
        risk_score=65.0,
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

    mock_json_payload = {
        "title": "Fix XSS",
        "summary": "Sanitize output",
        "technical_solution": "HTML escape",
        "business_solution": "Protect users",
        "risk_reduction_explanation": "Eliminate XSS",
        "validation_strategy": "Check response",
        "ai_confidence_score": 0.9,
        "effectiveness_confidence_score": 0.9,
        "steps": [],
        "patch_suggestions": [
            {
                "language": "JAVASCRIPT",
                "file_type": "SOURCE_CODE",
                "target_file_path": "frontend/src/App.js",
                "original_code_snippet": "element.innerHTML = input;",
                "proposed_patch_diff": "--- App.js\n+++ App.js\n-element.innerHTML = input;\n+element.textContent = input;",
                "explanation": "Replaces innerHTML with textContent",
                "security_impact_notes": "Prevents script execution",
                "confidence_score": 0.95,
            }
        ],
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=100,
        completion_tokens=150,
        total_tokens=250,
        latency_ms=300,
        cost_usd=0.003,
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
    mock_created.root_finding_id = finding_id
    mock_created.attack_path_id = None
    mock_created.cve_id = None
    mock_created.cwe_id = None
    mock_created.affected_version = None
    mock_created.fixed_version = None
    mock_created.title = "Fix XSS"
    mock_created.summary = ""
    mock_created.technical_solution = ""
    mock_created.business_solution = ""
    mock_created.risk_reduction_explanation = ""
    mock_created.validation_strategy = ""
    mock_created.composite_risk_score = 65.0
    mock_created.ai_confidence_score = 0.9
    mock_created.effectiveness_confidence_score = 0.9
    mock_created.requires_backup = False
    mock_created.requires_downtime = False
    mock_created.rollback_available = True
    mock_created.model_used = "gpt-4o"
    mock_created.provider_used = "OPENAI"
    mock_created.prompt_version = 1
    mock_created.status = "GENERATED"
    mock_created.steps = []
    mock_created.review_notes = None
    mock_created.reviewed_by = None
    mock_created.reviewed_at = None
    mock_created.error_message = None

    p1 = MagicMock(
        id=uuid4(),
        language="JAVASCRIPT",
        file_type="SOURCE_CODE",
        target_file_path="frontend/src/App.js",
        original_code_snippet="element.innerHTML = input;",
        proposed_patch_diff="--- App.js\n+++ App.js",
        explanation="",
        security_impact_notes="",
        confidence_score=0.95,
    )
    mock_created.patch_suggestions = [p1]
    service.remediation_repo.create_remediation_plan = AsyncMock(
        return_value=mock_created
    )

    dto = await service.generate_remediation_plan(org_id, finding_id, actor_id)

    assert len(dto.patch_suggestions) == 1
    assert dto.patch_suggestions[0].language == "JAVASCRIPT"
    assert dto.patch_suggestions[0].target_file_path == "frontend/src/App.js"


@pytest.mark.anyio
async def test_sensitive_data_masking_in_remediation_context() -> None:
    """Test that Bearer tokens and passwords in evidence dumps are masked in remediation context."""
    mock_session = MagicMock()
    service = AIRemediationService(mock_session)

    finding = MagicMock(
        title="Exposed API Key",
        severity="HIGH",
        category="AUTH",
        cve_id=None,
        cwe_id="CWE-522",
        risk_score=80.0,
        description="Authorization: Bearer secret_token_abc123\npassword=SuperSecretPass99",
    )

    context_str = service._build_remediation_context(
        finding=finding,
        evidence_artifacts=[],
        asset_node=None,
        graph_relationships=[],
        triage_status=None,
        explanation=None,
        impact_analysis=None,
        attack_path=None,
    )

    assert "secret_token_abc123" not in context_str
    assert "SuperSecretPass99" not in context_str
    assert "[REDACTED_SECRET]" in context_str


@pytest.mark.anyio
async def test_remediation_tenant_isolation() -> None:
    """Test that remediation repository queries enforce organization_id tenant boundary isolation."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = AIRemediationRepository(mock_session)

    org_id = uuid4()
    plan_id = uuid4()

    await repo.get_remediation_plan_by_id(org_id, plan_id)
    assert mock_session.execute.called

    await repo.list_remediation_plans(org_id, limit=10, offset=0)
    assert mock_session.execute.call_count == 2


@pytest.mark.anyio
async def test_invalid_llm_response_recovery() -> None:
    """Test retry-once recovery strategy when initial LLM response contains malformed JSON."""
    mock_session = MagicMock()
    service = AIRemediationService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="plugin",
        title="Finding Title",
        description="Description",
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

    malformed_resp = AIChatCompletionResponse(
        content="Malformed response plain text.",
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
        "title": "Repaired Remediation Plan",
        "summary": "Summary",
        "technical_solution": "Tech Solution",
        "business_solution": "Biz Solution",
        "risk_reduction_explanation": "Risk Explanation",
        "validation_strategy": "Validation Strategy",
        "ai_confidence_score": 0.85,
        "effectiveness_confidence_score": 0.90,
        "requires_backup": False,
        "requires_downtime": False,
        "rollback_available": True,
        "steps": [],
        "patch_suggestions": [],
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
    mock_created.root_finding_id = finding_id
    mock_created.attack_path_id = None
    mock_created.cve_id = None
    mock_created.cwe_id = None
    mock_created.affected_version = None
    mock_created.fixed_version = None
    mock_created.title = "Repaired Remediation Plan"
    mock_created.summary = "Summary"
    mock_created.technical_solution = ""
    mock_created.business_solution = ""
    mock_created.risk_reduction_explanation = ""
    mock_created.validation_strategy = ""
    mock_created.composite_risk_score = 50.0
    mock_created.ai_confidence_score = 0.85
    mock_created.effectiveness_confidence_score = 0.90
    mock_created.requires_backup = False
    mock_created.requires_downtime = False
    mock_created.rollback_available = True
    mock_created.model_used = "gpt-4o"
    mock_created.provider_used = "OPENAI"
    mock_created.prompt_version = 1
    mock_created.status = "GENERATED"
    mock_created.steps = []
    mock_created.patch_suggestions = []
    mock_created.review_notes = None
    mock_created.reviewed_by = None
    mock_created.reviewed_at = None
    mock_created.error_message = None
    mock_created.created_at = "2026-08-03T14:00:00Z"

    service.remediation_repo.create_remediation_plan = AsyncMock(
        return_value=mock_created
    )

    dto = await service.generate_remediation_plan(org_id, finding_id, actor_id)

    assert dto.status == "GENERATED"
    assert dto.title == "Repaired Remediation Plan"
    assert service.gateway_service.generate_completion.call_count == 2


@pytest.mark.anyio
async def test_remediation_review_workflow() -> None:
    """Test analyst approval/rejection and VALIDATION_FAILED review status updates on a remediation plan."""
    mock_session = MagicMock()
    service = AIRemediationService(mock_session)

    org_id = uuid4()
    plan_id = uuid4()
    reviewer_id = uuid4()

    mock_plan = MagicMock()
    mock_plan.id = plan_id
    mock_plan.root_finding_id = uuid4()
    mock_plan.attack_path_id = None
    mock_plan.cve_id = "CVE-2024-1234"
    mock_plan.cwe_id = "CWE-89"
    mock_plan.affected_version = None
    mock_plan.fixed_version = None
    mock_plan.title = "Sample Remediation Plan"
    mock_plan.summary = "Summary"
    mock_plan.technical_solution = ""
    mock_plan.business_solution = ""
    mock_plan.risk_reduction_explanation = ""
    mock_plan.validation_strategy = ""
    mock_plan.composite_risk_score = 80.0
    mock_plan.ai_confidence_score = 0.95
    mock_plan.effectiveness_confidence_score = 0.90
    mock_plan.requires_backup = True
    mock_plan.requires_downtime = False
    mock_plan.rollback_available = True
    mock_plan.model_used = "gpt-4o"
    mock_plan.provider_used = "OPENAI"
    mock_plan.prompt_version = 1
    mock_plan.status = "APPROVED"
    mock_plan.steps = []
    mock_plan.patch_suggestions = []
    mock_plan.review_notes = "Approved for staging deployment."
    mock_plan.reviewed_by = reviewer_id
    mock_plan.reviewed_at = "2026-08-03T15:00:00Z"
    mock_plan.error_message = None
    mock_plan.created_at = "2026-08-03T14:00:00Z"

    service.remediation_repo.update_review_status = AsyncMock(return_value=mock_plan)
    service.audit_service.record_event = AsyncMock()

    review_req = ReviewRemediationPlanRequest(
        status="APPROVED",
        review_notes="Approved for staging deployment.",
    )

    dto = await service.review_remediation_plan(
        org_id, plan_id, reviewer_id, review_req
    )

    assert dto.status == "APPROVED"
    assert dto.review_notes == "Approved for staging deployment."
    assert dto.reviewed_by == str(reviewer_id)
    assert service.audit_service.record_event.called
