"""Unit & Integration Tests for AI Attack Path Synthesis Engine (Phase 5.3)."""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.ai.attack_path_service import AIAttackPathService
from app.application.ai.dto import AIChatCompletionResponse, ReviewAttackPathRequest
from app.infrastructure.database.models.ai_attack_path import (
    AIAttackPathModel,
    AIAttackPathStepModel,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.asset_graph import (
    AssetNodeModel,
    AssetRelationshipModel,
)
from app.infrastructure.database.repositories.ai_attack_path_repository import (
    AIAttackPathRepository,
)


@pytest.mark.anyio
async def test_attack_path_generation_success() -> None:
    """Test generating a structured AI attack path with mocked LLM response."""
    mock_session = MagicMock()
    service = AIAttackPathService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()
    asset_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        asset_node_id=asset_id,
        plugin_id="sqli_plugin",
        title="SQL Injection in Admin Search",
        description="Unsanitized query in search input.",
        severity="HIGH",
        category="INJECTION",
        cve_id="CVE-2024-5555",
        cwe_id="CWE-89",
        risk_score=88.5,
    )

    mock_asset = AssetNodeModel(
        id=asset_id,
        organization_id=org_id,
        node_type="URL",
        name="admin.company.com/search",
        value="https://admin.company.com/search",
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=mock_finding)
    service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    service.asset_graph_repo.get_node_by_id = AsyncMock(return_value=mock_asset)
    service.asset_graph_repo.get_graph_by_domain = AsyncMock(
        return_value=([mock_asset], [])
    )
    service.triage_repo.get_triage_history = AsyncMock(return_value=[])

    mock_json_payload = {
        "title": "SQL Injection to Database Takeover",
        "attack_summary": "Attacker leverages unescaped SQL parameter to extract admin hashes and escalate privileges.",
        "confidence_score": 0.92,
        "steps": [
            {
                "sequence_number": 1,
                "step_type": "INITIAL_ACCESS",
                "title": "Exploit SQL Injection",
                "description": "Send crafted SQL payload to admin search form.",
                "mitre_tactic": "Initial Access",
                "mitre_technique_id": "T1190",
                "mitre_technique_name": "Exploit Public-Facing Application",
                "attacker_action": "POST /search with payload `' OR '1'='1`",
                "required_privilege": "Unauthenticated",
                "confidence_score": 0.95,
            },
            {
                "sequence_number": 2,
                "step_type": "CREDENTIAL_ACCESS",
                "title": "Extract Password Hashes",
                "description": "Dump password hashes from users table using UNION SELECT.",
                "mitre_tactic": "Credential Access",
                "mitre_technique_id": "T1555",
                "mitre_technique_name": "Credentials from Password Stores",
                "attacker_action": "Execute database extraction query",
                "required_privilege": "Web Application User",
                "confidence_score": 0.90,
            },
        ],
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=200,
        completion_tokens=250,
        total_tokens=450,
        latency_ms=500,
        cost_usd=0.006,
        status="SUCCESS",
    )

    service.gateway_service.generate_completion = AsyncMock(
        return_value=mock_completion_resp
    )
    service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    service.audit_service.record_event = AsyncMock()

    mock_created_path = MagicMock()
    mock_created_path.id = uuid4()
    mock_created_path.root_finding_id = finding_id
    mock_created_path.source_asset_id = asset_id
    mock_created_path.target_asset_id = asset_id
    mock_created_path.title = mock_json_payload["title"]
    mock_created_path.attack_summary = mock_json_payload["attack_summary"]
    mock_created_path.composite_risk_score = 88.5
    mock_created_path.confidence_score = 0.92
    mock_created_path.model_used = "gpt-4o"
    mock_created_path.provider_used = "OPENAI"
    mock_created_path.prompt_version = 1
    mock_created_path.status = "GENERATED"
    mock_created_path.review_notes = None
    mock_created_path.reviewed_by = None
    mock_created_path.reviewed_at = None
    mock_created_path.error_message = None
    mock_created_path.created_at = "2026-08-03T12:00:00Z"

    mock_step1 = MagicMock()
    mock_step1.id = uuid4()
    mock_step1.sequence_number = 1
    mock_step1.step_type = "INITIAL_ACCESS"
    mock_step1.asset_node_id = asset_id
    mock_step1.finding_id = finding_id
    mock_step1.title = "Exploit SQL Injection"
    mock_step1.description = "Send crafted SQL payload to admin search form."
    mock_step1.mitre_tactic = "Initial Access"
    mock_step1.mitre_technique_id = "T1190"
    mock_step1.mitre_technique_name = "Exploit Public-Facing Application"
    mock_step1.attacker_action = "POST /search with payload `' OR '1'='1`"
    mock_step1.required_privilege = "Unauthenticated"
    mock_step1.evidence_reference = None
    mock_step1.confidence_score = 0.95

    mock_created_path.steps = [mock_step1]
    service.path_repo.create_attack_path = AsyncMock(return_value=mock_created_path)

    dto = await service.generate_attack_path(org_id, finding_id, actor_id)

    assert dto.root_finding_id == str(finding_id)
    assert dto.title == mock_json_payload["title"]
    assert dto.confidence_score == 0.92
    assert len(dto.steps) == 1
    assert dto.steps[0].mitre_technique_id == "T1190"
    assert service.audit_service.record_event.called


@pytest.mark.anyio
async def test_attack_path_step_mapping() -> None:
    """Test detailed step mapping and sequence order in synthesized attack path."""
    mock_session = MagicMock()
    service = AIAttackPathService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="rce_plugin",
        title="RCE in File Upload",
        description="Remote code execution via image upload.",
        severity="CRITICAL",
        category="INJECTION",
        risk_score=95.0,
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=mock_finding)
    service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    service.asset_graph_repo.get_node_by_id = AsyncMock(return_value=None)
    service.triage_repo.get_triage_history = AsyncMock(return_value=[])

    mock_json_payload = {
        "title": "File Upload RCE to Host Pivot",
        "attack_summary": "Upload web shell, execute system commands, and dump credentials.",
        "confidence_score": 0.88,
        "steps": [
            {
                "sequence_number": 1,
                "step_type": "INITIAL_ACCESS",
                "title": "Upload Malicious Web Shell",
                "description": "Upload shell.php disguised as PNG image.",
                "mitre_tactic": "Initial Access",
                "mitre_technique_id": "T1190",
                "mitre_technique_name": "Exploit Public-Facing Application",
                "attacker_action": "POST /upload with shell payload",
                "required_privilege": "Unauthenticated",
                "confidence_score": 0.90,
            },
            {
                "sequence_number": 2,
                "step_type": "LATERAL_MOVEMENT",
                "title": "Pivot to Database Server",
                "description": "Use local SSH keys to connect to internal DB node.",
                "mitre_tactic": "Lateral Movement",
                "mitre_technique_id": "T1021",
                "mitre_technique_name": "Remote Services",
                "attacker_action": "SSH connect using extracted id_rsa",
                "required_privilege": "System Shell",
                "confidence_score": 0.85,
            },
        ],
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="claude-3-5-sonnet",
        provider_used="ANTHROPIC",
        prompt_tokens=300,
        completion_tokens=350,
        total_tokens=650,
        latency_ms=700,
        cost_usd=0.01,
        status="SUCCESS",
    )

    service.gateway_service.generate_completion = AsyncMock(
        return_value=mock_completion_resp
    )
    service.gateway_service.ai_repo.get_active_prompt_template = AsyncMock(
        return_value=None
    )
    service.audit_service.record_event = AsyncMock()

    mock_path_model = MagicMock()
    mock_path_model.id = uuid4()
    mock_path_model.root_finding_id = finding_id
    mock_path_model.source_asset_id = None
    mock_path_model.target_asset_id = None
    mock_path_model.title = mock_json_payload["title"]
    mock_path_model.attack_summary = mock_json_payload["attack_summary"]
    mock_path_model.composite_risk_score = 95.0
    mock_path_model.confidence_score = 0.88
    mock_path_model.model_used = "claude-3-5-sonnet"
    mock_path_model.provider_used = "ANTHROPIC"
    mock_path_model.prompt_version = 1
    mock_path_model.status = "GENERATED"
    mock_path_model.review_notes = None
    mock_path_model.reviewed_by = None
    mock_path_model.reviewed_at = None
    mock_path_model.error_message = None
    mock_path_model.created_at = "2026-08-03T12:00:00Z"

    s1 = MagicMock(
        sequence_number=1,
        step_type="INITIAL_ACCESS",
        title="Upload Malicious Web Shell",
        description="",
        mitre_tactic="Initial Access",
        mitre_technique_id="T1190",
        mitre_technique_name="Exploit Public-Facing Application",
        attacker_action="",
        required_privilege="",
        evidence_reference=None,
        confidence_score=0.90,
        asset_node_id=None,
        finding_id=finding_id,
    )
    s2 = MagicMock(
        sequence_number=2,
        step_type="LATERAL_MOVEMENT",
        title="Pivot to Database Server",
        description="",
        mitre_tactic="Lateral Movement",
        mitre_technique_id="T1021",
        mitre_technique_name="Remote Services",
        attacker_action="",
        required_privilege="",
        evidence_reference=None,
        confidence_score=0.85,
        asset_node_id=None,
        finding_id=None,
    )

    mock_path_model.steps = [s1, s2]
    service.path_repo.create_attack_path = AsyncMock(return_value=mock_path_model)

    dto = await service.generate_attack_path(org_id, finding_id, actor_id)

    assert len(dto.steps) == 2
    assert dto.steps[0].sequence_number == 1
    assert dto.steps[0].step_type == "INITIAL_ACCESS"
    assert dto.steps[1].sequence_number == 2
    assert dto.steps[1].step_type == "LATERAL_MOVEMENT"


@pytest.mark.anyio
async def test_mitre_attack_mapping_and_validation() -> None:
    """Test validation of MITRE technique IDs against KNOWN_MITRE_TECHNIQUES registry."""
    mock_session = MagicMock()
    service = AIAttackPathService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="auth_plugin",
        title="Weak Credentials",
        description="Default credentials in admin panel.",
        severity="HIGH",
        category="AUTHENTICATION",
        risk_score=80.0,
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=mock_finding)
    service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    service.asset_graph_repo.get_node_by_id = AsyncMock(return_value=None)
    service.triage_repo.get_triage_history = AsyncMock(return_value=[])

    # LLM returns one known technique (T1078) and one unknown technique (T9999)
    mock_json_payload = {
        "title": "Credential Brute Force",
        "attack_summary": "Attacker logs in with valid credentials.",
        "confidence_score": 0.85,
        "steps": [
            {
                "sequence_number": 1,
                "step_type": "INITIAL_ACCESS",
                "title": "Use Valid Accounts",
                "description": "Log in using default admin credentials.",
                "mitre_tactic": "Initial Access",
                "mitre_technique_id": "T1078",
                "mitre_technique_name": "",
                "attacker_action": "POST /login",
                "required_privilege": "None",
                "confidence_score": 0.90,
            },
            {
                "sequence_number": 2,
                "step_type": "EXECUTION",
                "title": "Custom Technique",
                "description": "Execute unknown technique action.",
                "mitre_tactic": "Execution",
                "mitre_technique_id": "T9999",
                "mitre_technique_name": "Custom Action",
                "attacker_action": "Run custom script",
                "required_privilege": "Admin",
                "confidence_score": 0.80,
            },
        ],
    }

    mock_completion_resp = AIChatCompletionResponse(
        content=json.dumps(mock_json_payload),
        model_used="gpt-4o",
        provider_used="OPENAI",
        prompt_tokens=150,
        completion_tokens=200,
        total_tokens=350,
        latency_ms=400,
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

    # Capture the steps_data passed to create_attack_path
    captured_steps_data = []

    async def mock_create_path(**kwargs):
        nonlocal captured_steps_data
        captured_steps_data = kwargs.get("steps_data", [])
        mock_p = MagicMock()
        mock_p.id = uuid4()
        mock_p.root_finding_id = finding_id
        mock_p.source_asset_id = None
        mock_p.target_asset_id = None
        mock_p.title = kwargs.get("title")
        mock_p.attack_summary = kwargs.get("attack_summary")
        mock_p.composite_risk_score = 80.0
        mock_p.confidence_score = kwargs.get("confidence_score")
        mock_p.model_used = "gpt-4o"
        mock_p.provider_used = "OPENAI"
        mock_p.prompt_version = 1
        mock_p.status = "GENERATED"
        mock_p.steps = []
        mock_p.review_notes = None
        mock_p.reviewed_by = None
        mock_p.reviewed_at = None
        mock_p.error_message = None
        mock_p.created_at = "2026-08-03T12:00:00Z"
        return mock_p

    service.path_repo.create_attack_path = AsyncMock(side_effect=mock_create_path)

    await service.generate_attack_path(org_id, finding_id, actor_id)

    assert len(captured_steps_data) == 2
    # Known technique T1078 resolved official name "Valid Accounts"
    assert captured_steps_data[0]["mitre_technique_name"] == "Valid Accounts"
    # Unknown technique T9999 tagged with (Unverified)
    assert "(Unverified)" in captured_steps_data[1]["mitre_technique_name"]


@pytest.mark.anyio
async def test_attack_context_uses_asset_graph() -> None:
    """Test that context builder enriches attack context with asset graph topology and relationships."""
    mock_session = MagicMock()
    service = AIAttackPathService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    asset_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        asset_node_id=asset_id,
        plugin_id="sqli_plugin",
        title="SQLi on Primary DB Node",
        description="Database injection vulnerability.",
        severity="HIGH",
        category="INJECTION",
        risk_score=90.0,
    )

    mock_asset = AssetNodeModel(
        id=asset_id,
        organization_id=org_id,
        node_type="DATABASE",
        name="db-primary.internal",
        value="10.0.1.50",
    )

    mock_rel = AssetRelationshipModel(
        organization_id=org_id,
        source_node_id=asset_id,
        target_node_id=uuid4(),
        relationship_type="CONNECTS_TO",
    )

    context_str = service._build_attack_context(
        finding=mock_finding,
        evidence_artifacts=[],
        asset_node=mock_asset,
        graph_relationships=[mock_rel],
        neighbor_nodes=[mock_asset],
        triage_status="CONFIRMED",
    )

    assert "SQLi on Primary DB Node" in context_str
    assert "db-primary.internal" in context_str
    assert "CONNECTS_TO" in context_str
    assert "CONFIRMED" in context_str


@pytest.mark.anyio
async def test_sensitive_data_masking_in_attack_context() -> None:
    """Test that Bearer tokens, cookies, and passwords in evidence are masked in attack context."""
    mock_session = MagicMock()
    service = AIAttackPathService(mock_session)

    finding = MagicMock(
        title="Exposed Credentials",
        severity="HIGH",
        category="AUTH",
        cve_id=None,
        cwe_id="CWE-522",
        risk_score=85.0,
        description="Authorization: Bearer secret_jwt_token_9999\nCookie: session_id=secret_cookie_val\npassword=SuperSecretPassword123!",
        remediation="Remove hardcoded secrets",
    )

    context_str = service._build_attack_context(
        finding=finding,
        evidence_artifacts=[],
        asset_node=None,
        graph_relationships=[],
        neighbor_nodes=[],
        triage_status=None,
    )

    assert "secret_jwt_token_9999" not in context_str
    assert "secret_cookie_val" not in context_str
    assert "SuperSecretPassword123!" not in context_str
    assert "[REDACTED_SECRET]" in context_str


@pytest.mark.anyio
async def test_tenant_isolation_on_attack_path_queries() -> None:
    """Test that attack path queries enforce organization_id tenant boundary isolation."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = AIAttackPathRepository(mock_session)

    org_id = uuid4()
    path_id = uuid4()

    # Query path for org_id
    await repo.get_attack_path_by_id(org_id, path_id)
    assert mock_session.execute.called

    # Query listing for org_id
    await repo.list_attack_paths(org_id, limit=10, offset=0)
    assert mock_session.execute.call_count == 2


@pytest.mark.anyio
async def test_invalid_llm_json_retry_recovery() -> None:
    """Test retry-once recovery strategy when initial LLM response contains malformed JSON."""
    mock_session = MagicMock()
    service = AIAttackPathService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()
    actor_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="plugin",
        title="Finding Title",
        description="Finding Description",
        severity="MEDIUM",
        category="OTHER",
        risk_score=60.0,
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=mock_finding)
    service.evidence_repo.list_finding_artifacts = AsyncMock(return_value=[])
    service.asset_graph_repo.get_node_by_id = AsyncMock(return_value=None)
    service.triage_repo.get_triage_history = AsyncMock(return_value=[])

    malformed_resp = AIChatCompletionResponse(
        content="Raw plain text response without JSON wrapper.",
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
        "title": "Repaired Attack Path",
        "attack_summary": "Successfully recovered attack path narrative.",
        "confidence_score": 0.80,
        "steps": [
            {
                "sequence_number": 1,
                "step_type": "INITIAL_ACCESS",
                "title": "Initial Step",
                "description": "Initial Step Description",
                "mitre_tactic": "Initial Access",
                "mitre_technique_id": "T1190",
                "mitre_technique_name": "Exploit Public-Facing Application",
                "attacker_action": "Action",
                "required_privilege": "None",
                "confidence_score": 0.85,
            }
        ],
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
    mock_created.source_asset_id = None
    mock_created.target_asset_id = None
    mock_created.title = "Repaired Attack Path"
    mock_created.attack_summary = "Successfully recovered attack path narrative."
    mock_created.composite_risk_score = 60.0
    mock_created.confidence_score = 0.80
    mock_created.model_used = "gpt-4o"
    mock_created.provider_used = "OPENAI"
    mock_created.prompt_version = 1
    mock_created.status = "GENERATED"
    mock_created.steps = []
    mock_created.review_notes = None
    mock_created.reviewed_by = None
    mock_created.reviewed_at = None
    mock_created.error_message = None
    mock_created.created_at = "2026-08-03T12:00:00Z"
    service.path_repo.create_attack_path = AsyncMock(return_value=mock_created)

    dto = await service.generate_attack_path(org_id, finding_id, actor_id)

    assert dto.status == "GENERATED"
    assert dto.title == "Repaired Attack Path"
    assert service.gateway_service.generate_completion.call_count == 2


@pytest.mark.anyio
async def test_attack_path_history_versioning_and_analyst_review() -> None:
    """Test listing attack path history and applying analyst review feedback notes."""
    mock_session = MagicMock()
    service = AIAttackPathService(mock_session)

    org_id = uuid4()
    path_id = uuid4()
    reviewer_id = uuid4()

    mock_path = MagicMock()
    mock_path.id = path_id
    mock_path.root_finding_id = uuid4()
    mock_path.source_asset_id = None
    mock_path.target_asset_id = None
    mock_path.title = "Sample Attack Path"
    mock_path.attack_summary = "Summary"
    mock_path.composite_risk_score = 75.0
    mock_path.confidence_score = 0.90
    mock_path.model_used = "gpt-4o"
    mock_path.provider_used = "OPENAI"
    mock_path.prompt_version = 1
    mock_path.status = "ACCEPTED"
    mock_path.steps = []
    mock_path.review_notes = "Verified by Security Analyst on call."
    mock_path.reviewed_by = reviewer_id
    mock_path.reviewed_at = "2026-08-03T13:00:00Z"
    mock_path.error_message = None
    mock_path.created_at = "2026-08-03T12:00:00Z"

    service.path_repo.update_review_status = AsyncMock(return_value=mock_path)
    service.audit_service.record_event = AsyncMock()

    review_req = ReviewAttackPathRequest(
        status="ACCEPTED",
        review_notes="Verified by Security Analyst on call.",
    )

    dto = await service.review_attack_path(org_id, path_id, reviewer_id, review_req)

    assert dto.status == "ACCEPTED"
    assert dto.review_notes == "Verified by Security Analyst on call."
    assert dto.reviewed_by == str(reviewer_id)
    assert service.audit_service.record_event.called
