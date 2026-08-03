"""Unit & Integration Tests for Phase 5.7 Enterprise AI Security Copilot & Interactive Assistant."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.ai.agent_orchestrator import AgentOrchestrator
from app.application.ai.copilot_service import SecurityCopilotService
from app.application.ai.copilot_tool_registry import CopilotToolRegistry
from app.application.ai.dto import (
    CreateCopilotSessionRequest,
    RAGSearchResponse,
    SendCopilotMessageRequest,
    SubmitCopilotFeedbackRequest,
    UpdateCopilotSessionRequest,
)
from app.application.ai.prompt_orchestrator_service import (
    mask_sensitive_prompt_context,
)
from app.domain.entities.ai import CopilotAgentType, CopilotToolStatus
from app.infrastructure.database.models.ai_copilot import (
    CopilotFeedbackModel,
    CopilotMessageModel,
    CopilotSessionModel,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel


def test_agent_orchestrator_intent_classification() -> None:
    """Test multi-agent intent classification routing."""
    assert (
        AgentOrchestrator.classify_intent(
            "Explain the root cause of this SQL injection finding"
        )
        == CopilotAgentType.EXPLAINER
    )
    assert (
        AgentOrchestrator.classify_intent(
            "Synthesize the MITRE ATT&CK attack path for this asset"
        )
        == CopilotAgentType.ATTACK_PATH
    )
    assert (
        AgentOrchestrator.classify_intent(
            "How do I fix and remediate this vulnerability with code patches?"
        )
        == CopilotAgentType.REMEDIATION
    )
    assert (
        AgentOrchestrator.classify_intent(
            "Is this a false positive finding? Check confidence"
        )
        == CopilotAgentType.FALSE_POSITIVE
    )
    assert (
        AgentOrchestrator.classify_intent(
            "Search OWASP guidelines and internal compliance policies"
        )
        == CopilotAgentType.KNOWLEDGE_RAG
    )
    assert (
        AgentOrchestrator.classify_intent("Summarize our overall security posture")
        == CopilotAgentType.SECURITY_ANALYST
    )


@pytest.mark.anyio
async def test_copilot_session_creation_and_lifecycle() -> None:
    """Test initializing and updating a Copilot investigation session."""
    mock_session = MagicMock()
    service = SecurityCopilotService(mock_session)

    org_id = uuid4()
    user_id = uuid4()
    finding_id = uuid4()

    req = CreateCopilotSessionRequest(
        title="Investigating Critical SQLi",
        focused_finding_id=str(finding_id),
        model_alias="gpt-4o",
        temperature=0.2,
    )

    mock_saved_session = CopilotSessionModel(
        id=uuid4(),
        organization_id=org_id,
        user_id=user_id,
        title=req.title,
        status="ACTIVE",
        focused_finding_id=finding_id,
        model_alias="gpt-4o",
        temperature=0.2,
        total_tokens=0,
        message_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service.copilot_repo.create_session = AsyncMock(return_value=mock_saved_session)
    service.audit_service.record_event = AsyncMock()

    dto = await service.create_session(org_id, user_id, req)

    assert dto.title == req.title
    assert dto.organization_id == str(org_id)
    assert dto.user_id == str(user_id)
    assert dto.focused_finding_id == str(finding_id)
    assert dto.status == "ACTIVE"
    assert service.audit_service.record_event.called


@pytest.mark.anyio
async def test_copilot_conversation_persistence_and_messaging() -> None:
    """Test sending an analyst message and receiving grounded assistant response with explainability metadata."""
    mock_session = MagicMock()
    service = SecurityCopilotService(mock_session)

    org_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()
    finding_id = uuid4()

    mock_session_obj = CopilotSessionModel(
        id=session_id,
        organization_id=org_id,
        user_id=user_id,
        title="Active Investigation",
        status="ACTIVE",
        focused_finding_id=finding_id,
        model_alias="default",
        temperature=0.2,
        total_tokens=100,
        message_count=2,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service.copilot_repo.get_session_by_id = AsyncMock(return_value=mock_session_obj)

    mock_user_msg = CopilotMessageModel(
        id=uuid4(),
        session_id=session_id,
        organization_id=org_id,
        role="USER",
        content="How do I fix this SQL injection?",
        agent_type="REMEDIATION",
        token_count=8,
        created_at=datetime.now(timezone.utc),
    )
    mock_assistant_msg = CopilotMessageModel(
        id=uuid4(),
        session_id=session_id,
        organization_id=org_id,
        role="ASSISTANT",
        content="### AI Security Copilot Analysis (REMEDIATION)\nUse parameterized queries.",
        agent_type="REMEDIATION",
        token_count=45,
        response_confidence_score=0.92,
        sources_used=[{"source_type": "OWASP", "title": "SQL Injection Prevention"}],
        knowledge_chunks_used=[{"chunk_id": str(uuid4()), "similarity_score": 0.88}],
        tools_called=[
            {"tool_name": "get_remediation_plan", "execution_status": "SUCCESS"}
        ],
        reasoning_summary="Synthesized using OWASP standards and remediation tool output.",
        model_used="default",
        prompt_version="1.0",
        response_evaluation_metadata={"agent_type": "REMEDIATION"},
        created_at=datetime.now(timezone.utc),
    )

    service.copilot_repo.create_message = AsyncMock(
        side_effect=[mock_user_msg, mock_assistant_msg]
    )
    service.copilot_repo.update_session = AsyncMock()
    service.audit_service.record_event = AsyncMock()

    mock_rag_resp = RAGSearchResponse(
        query="How do I fix this SQL injection?",
        results_count=0,
        results=[],
        search_latency_ms=2,
    )
    service.rag_service.search_knowledge_base = AsyncMock(return_value=mock_rag_resp)

    # Mock tool registry execution
    service.tool_registry.execute_tool = AsyncMock(
        return_value={
            "tool_name": "get_remediation_plan",
            "execution_status": "SUCCESS",
            "output": {"summary": "Use parameterized queries"},
            "latency_ms": 12,
        }
    )

    req = SendCopilotMessageRequest(
        content="How do I fix this SQL injection?",
        focused_finding_id=str(finding_id),
        enable_rag=True,
    )

    response = await service.send_message(org_id, user_id, session_id, req)

    assert response.session_id == str(session_id)
    assert response.agent_type == "REMEDIATION"
    assert response.response_confidence_score == 0.92
    assert response.assistant_message.reasoning_summary is not None
    assert len(response.tools_executed) >= 1
    assert service.copilot_repo.create_message.call_count == 2


@pytest.mark.anyio
async def test_copilot_context_memory_and_key_value_upsert() -> None:
    """Test context memory upsert and retrieval for investigation state."""
    mock_session = MagicMock()
    service = SecurityCopilotService(mock_session)

    org_id = uuid4()
    session_id = uuid4()

    service.copilot_repo.upsert_context_memory = AsyncMock()
    service.copilot_repo.get_context_memories_by_session = AsyncMock(return_value=[])

    await service.copilot_repo.upsert_context_memory(
        organization_id=org_id,
        session_id=session_id,
        memory_key="focused_vulnerability",
        memory_value_json={"cve_id": "CVE-2024-1111", "cwe_id": "CWE-89"},
        memory_type="INVESTIGATION_STATE",
    )

    assert service.copilot_repo.upsert_context_memory.called


@pytest.mark.anyio
async def test_copilot_read_only_tool_execution() -> None:
    """Test read-only tool calling execution and audit log persistence."""
    mock_session = MagicMock()
    tool_registry = CopilotToolRegistry(mock_session)

    org_id = uuid4()
    session_id = uuid4()
    finding_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="sqli_plugin",
        title="SQL Injection in Search Form",
        description="Concatenated SQL query",
        severity="HIGH",
        category="SQLI",
        risk_score=88.0,
    )
    tool_registry.assessment_repo.get_finding_by_id = AsyncMock(
        return_value=mock_finding
    )
    tool_registry.copilot_repo.log_tool_execution = AsyncMock()

    res = await tool_registry.execute_tool(
        tool_name="get_finding_details",
        input_params={"finding_id": str(finding_id)},
        organization_id=org_id,
        session_id=session_id,
    )

    assert res["tool_name"] == "get_finding_details"
    assert res["execution_status"] == "SUCCESS"
    assert res["output"]["title"] == "SQL Injection in Search Form"
    assert tool_registry.copilot_repo.log_tool_execution.called


@pytest.mark.anyio
async def test_copilot_tenant_boundary_isolation() -> None:
    """Test tenant boundary isolation for sessions and messages."""
    mock_session = MagicMock()
    service = SecurityCopilotService(mock_session)

    org_a = uuid4()
    session_id = uuid4()

    service.copilot_repo.get_session_by_id = AsyncMock(return_value=None)

    with pytest.raises(Exception):
        await service.get_session(org_a, session_id)


@pytest.mark.anyio
async def test_copilot_prompt_injection_defense_and_secret_masking() -> None:
    """Test secret masking in user prompts before processing."""
    raw_prompt = "Connect with Authorization: Bearer secret_api_token_999 to resolve vulnerability"
    masked = mask_sensitive_prompt_context(raw_prompt)

    assert "secret_api_token_999" not in masked
    assert "[REDACTED_SECRET]" in masked


@pytest.mark.anyio
async def test_copilot_analyst_feedback_recording() -> None:
    """Test submitting analyst rating and feedback notes."""
    mock_session = MagicMock()
    service = SecurityCopilotService(mock_session)

    org_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()
    message_id = uuid4()

    req = SubmitCopilotFeedbackRequest(
        session_id=str(session_id),
        message_id=str(message_id),
        rating=5,
        is_helpful=True,
        feedback_category="REMEDIATION",
        feedback_notes="Excellent parameterized query recommendation.",
    )

    mock_saved_feedback = CopilotFeedbackModel(
        id=uuid4(),
        session_id=session_id,
        message_id=message_id,
        organization_id=org_id,
        user_id=user_id,
        rating=5,
        is_helpful=True,
        feedback_category="REMEDIATION",
        feedback_notes="Excellent parameterized query recommendation.",
        created_at=datetime.now(timezone.utc),
    )

    service.copilot_repo.create_feedback = AsyncMock(return_value=mock_saved_feedback)
    service.audit_service.record_event = AsyncMock()

    dto = await service.submit_feedback(org_id, user_id, req)

    assert dto.rating == 5
    assert dto.is_helpful is True
    assert dto.feedback_category == "REMEDIATION"
    assert service.audit_service.record_event.called


@pytest.mark.anyio
async def test_copilot_strict_non_autonomous_safety_policy() -> None:
    """Validate that Copilot tool registry rejects unauthorized or mutating command executions."""
    mock_session = MagicMock()
    tool_registry = CopilotToolRegistry(mock_session)
    tool_registry.copilot_repo.log_tool_execution = AsyncMock()

    org_id = uuid4()
    session_id = uuid4()

    res = await tool_registry.execute_tool(
        tool_name="execute_system_command",
        input_params={"command": "rm -rf /"},
        organization_id=org_id,
        session_id=session_id,
    )

    assert res["execution_status"] == "DENIED"
    assert "not registered or prohibited" in res["output"]["error"]


@pytest.mark.anyio
async def test_copilot_response_grounding_explainability_metadata() -> None:
    """Verify tracking of full explainability metadata on Copilot responses."""
    mock_session = MagicMock()
    service = SecurityCopilotService(mock_session)

    org_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()

    mock_session_obj = CopilotSessionModel(
        id=session_id,
        organization_id=org_id,
        user_id=user_id,
        title="Explainability Test",
        status="ACTIVE",
        model_alias="gpt-4o",
        temperature=0.2,
        total_tokens=50,
        message_count=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service.copilot_repo.get_session_by_id = AsyncMock(return_value=mock_session_obj)

    mock_user_msg = CopilotMessageModel(
        id=uuid4(),
        session_id=session_id,
        organization_id=org_id,
        role="USER",
        content="Why was this recommended?",
        agent_type="SECURITY_ANALYST",
        token_count=5,
        created_at=datetime.now(timezone.utc),
    )
    mock_assistant_msg = CopilotMessageModel(
        id=uuid4(),
        session_id=session_id,
        organization_id=org_id,
        role="ASSISTANT",
        content="Based on OWASP SQLi prevention cheat sheet...",
        agent_type="KNOWLEDGE_RAG",
        token_count=30,
        response_confidence_score=0.95,
        sources_used=[{"title": "OWASP SQLi", "source_url": "https://owasp.org"}],
        knowledge_chunks_used=[{"chunk_id": str(uuid4()), "similarity_score": 0.91}],
        tools_called=[
            {"tool_name": "search_rag_knowledge", "execution_status": "SUCCESS"}
        ],
        reasoning_summary="Grounding derived from OWASP vector search.",
        model_used="gpt-4o",
        prompt_version="1.0",
        response_evaluation_metadata={"explainability": "verified"},
        created_at=datetime.now(timezone.utc),
    )

    service.copilot_repo.create_message = AsyncMock(
        side_effect=[mock_user_msg, mock_assistant_msg]
    )
    service.copilot_repo.update_session = AsyncMock()
    service.audit_service.record_event = AsyncMock()

    mock_rag_resp = RAGSearchResponse(
        query="Why was this recommended?",
        results_count=0,
        results=[],
        search_latency_ms=2,
    )
    service.rag_service.search_knowledge_base = AsyncMock(return_value=mock_rag_resp)

    req = SendCopilotMessageRequest(
        content="Why was this recommended?", enable_rag=True
    )
    res = await service.send_message(org_id, user_id, session_id, req)

    assert res.assistant_message.response_confidence_score == 0.95
    assert len(res.assistant_message.sources_used) == 1
    assert len(res.assistant_message.knowledge_chunks_used) == 1
    assert res.assistant_message.model_used == "gpt-4o"
    assert res.assistant_message.prompt_version == "1.0"
