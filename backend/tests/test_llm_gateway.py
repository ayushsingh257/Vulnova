"""Unit & Integration Tests for Multi-Provider LLM Gateway & Prompt Orchestrator (Phase 5.1)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import Response
from uuid import uuid4

from app.application.ai.dto import (
    AIChatCompletionRequest,
    CreatePromptTemplateRequest,
    CreateProviderRequest,
    LLMMessageDTO,
    RegisterModelRequest,
)
from app.application.ai.llm_gateway_service import LLMGatewayService
from app.application.ai.prompt_orchestrator_service import (
    PromptOrchestratorService,
    mask_sensitive_prompt_context,
)
from app.domain.entities.ai import (
    LLMMessage,
    LLMProviderType,
    LLMRequest,
    PromptCategory,
)
from app.domain.entities.assessment import (
    Finding,
    SeverityLevel,
    CVSSMetrics,
    RiskMetrics,
)
from app.infrastructure.ai.providers import (
    AnthropicAdapter,
    GoogleAdapter,
    LocalOllamaAdapter,
    OpenAIAdapter,
    get_adapter_for_provider,
)
from app.infrastructure.database.models.user import UserModel
from app.security.encryption import SecretEncryptionService

# ── 1. Secret Encryption Service Tests ─────────────────


def test_secret_encryption_service() -> None:
    """Test AES-256-GCM secret encryption and decryption."""
    encryption = SecretEncryptionService(key_seed="test-secret-key-123456789")
    plain_api_key = "sk-proj-openai-secret-key-9988776655"

    cipher_text = encryption.encrypt_secret(plain_api_key)
    assert cipher_text != plain_api_key
    assert len(cipher_text) > 20

    decrypted_key = encryption.decrypt_secret(cipher_text)
    assert decrypted_key == plain_api_key

    # Test empty string
    assert encryption.encrypt_secret("") == ""
    assert encryption.decrypt_secret("") == ""


# ── 2. Provider Adapters Tests (httpx Mocked) ─────────


@pytest.mark.anyio
async def test_openai_adapter_execute() -> None:
    """Test OpenAIAdapter REST API call parsing."""
    adapter = OpenAIAdapter()
    req = LLMRequest(
        messages=[LLMMessage(role="user", content="Test prompt")],
        model_alias="gpt-4o",
    )

    mock_resp_json = {
        "choices": [{"message": {"content": "OpenAI mock response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(200, json=mock_resp_json)
        res = await adapter.execute(req, api_key="sk-test-key")

        assert res.content == "OpenAI mock response"
        assert res.provider_type == LLMProviderType.OPENAI
        assert res.prompt_tokens == 10
        assert res.completion_tokens == 20
        assert res.total_tokens == 30


@pytest.mark.anyio
async def test_anthropic_adapter_execute() -> None:
    """Test AnthropicAdapter REST API call parsing."""
    adapter = AnthropicAdapter()
    req = LLMRequest(
        messages=[LLMMessage(role="user", content="Test prompt")],
        model_alias="claude-3-5-sonnet",
    )

    mock_resp_json = {
        "content": [{"type": "text", "text": "Anthropic mock response"}],
        "usage": {"input_tokens": 15, "output_tokens": 25},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(200, json=mock_resp_json)
        res = await adapter.execute(req, api_key="sk-ant-key")

        assert res.content == "Anthropic mock response"
        assert res.provider_type == LLMProviderType.ANTHROPIC
        assert res.prompt_tokens == 15
        assert res.completion_tokens == 25


@pytest.mark.anyio
async def test_google_adapter_execute() -> None:
    """Test GoogleAdapter REST API call parsing."""
    adapter = GoogleAdapter()
    req = LLMRequest(
        messages=[LLMMessage(role="user", content="Test prompt")],
        model_alias="gemini-1.5-pro",
    )

    mock_resp_json = {
        "candidates": [{"content": {"parts": [{"text": "Gemini mock response"}]}}],
        "usageMetadata": {
            "promptTokenCount": 8,
            "candidatesTokenCount": 12,
            "totalTokenCount": 20,
        },
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(200, json=mock_resp_json)
        res = await adapter.execute(req, api_key="AIzaSyTest")

        assert res.content == "Gemini mock response"
        assert res.provider_type == LLMProviderType.GOOGLE
        assert res.total_tokens == 20


@pytest.mark.anyio
async def test_local_ollama_adapter_execute() -> None:
    """Test LocalOllamaAdapter REST API call parsing."""
    adapter = LocalOllamaAdapter()
    req = LLMRequest(
        messages=[LLMMessage(role="user", content="Test prompt")],
        model_alias="llama3",
    )

    mock_resp_json = {
        "message": {"content": "Ollama mock response"},
        "prompt_eval_count": 12,
        "eval_count": 18,
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(200, json=mock_resp_json)
        res = await adapter.execute(req)

        assert res.content == "Ollama mock response"
        assert res.provider_type == LLMProviderType.OLLAMA
        assert res.cost_usd == 0.0


def test_adapter_registry_factory() -> None:
    """Test get_adapter_for_provider factory."""
    assert isinstance(get_adapter_for_provider(LLMProviderType.OPENAI), OpenAIAdapter)
    assert isinstance(
        get_adapter_for_provider(LLMProviderType.ANTHROPIC), AnthropicAdapter
    )
    assert isinstance(get_adapter_for_provider(LLMProviderType.GOOGLE), GoogleAdapter)
    assert isinstance(
        get_adapter_for_provider(LLMProviderType.OLLAMA), LocalOllamaAdapter
    )


# ── 3. Prompt Orchestrator & Context Builder Tests ─────


def test_mask_sensitive_prompt_context() -> None:
    """Test masking Authorization headers, cookies, and passwords in prompt context."""
    raw_prompt = (
        "Target endpoint response headers:\n"
        "Authorization: Bearer secret_jwt_token_12345\n"
        "Cookie: session_id=abc123xyz; admin=true\n"
        "Connecting with password=SuperSecretPassword123!\n"
    )
    masked = mask_sensitive_prompt_context(raw_prompt)

    assert "secret_jwt_token_12345" not in masked
    assert "session_id=abc123xyz" not in masked
    assert "SuperSecretPassword123!" not in masked
    assert "[REDACTED_SECRET]" in masked


def test_build_security_finding_context() -> None:
    """Test building markdown security context for LLM prompt ingestion."""
    session = MagicMock()
    orchestrator = PromptOrchestratorService(session)

    finding = Finding(
        organization_id=uuid4(),
        plugin_id="sqli_assessment",
        title="SQL Injection in Login Form",
        description="Unsanitized user input in username parameter.",
        severity=SeverityLevel.HIGH,
        cwe_id="CWE-89",
        remediation="Use parameterized queries.",
        risk=RiskMetrics(
            composite_risk_score=85.0,
            business_impact="CRITICAL",
            fix_sla_hours=72,
        ),
    )

    evidence_dumps = [
        "POST /login HTTP/1.1\nHost: example.com\nAuthorization: Bearer secret_token\n\nusername=admin' OR '1'='1"
    ]

    context_md = orchestrator.build_security_finding_context(
        finding=finding,
        evidence_dumps=evidence_dumps,
        triage_status="CONFIRMED",
    )

    assert "SQL Injection in Login Form" in context_md
    assert "CWE-89" in context_md
    assert "85.0/100.0" in context_md
    assert "CONFIRMED" in context_md
    assert (
        "secret_token" not in context_md
    )  # Asserts masking works inside finding context!


# ── 4. LLMGatewayService & Fallback Routing Tests ──────


@pytest.mark.anyio
async def test_gateway_service_fallback_routing() -> None:
    """Test automatic provider fallback when primary provider fails."""
    mock_session = MagicMock()
    service = LLMGatewayService(mock_session)

    org_id = uuid4()
    req = AIChatCompletionRequest(
        messages=[LLMMessageDTO(role="user", content="Analyze vulnerability")],
        model_alias="gpt-4o",
    )

    # Mock DB providers returned: primary OpenAI, secondary Anthropic
    p1 = MagicMock(
        id=uuid4(),
        provider_type="OPENAI",
        name="Primary OpenAI",
        encrypted_api_key=None,
        api_endpoint=None,
    )
    p2 = MagicMock(
        id=uuid4(),
        provider_type="ANTHROPIC",
        name="Secondary Anthropic",
        encrypted_api_key=None,
        api_endpoint=None,
    )

    service.ai_repo.list_active_providers = AsyncMock(return_value=[p1, p2])
    service.ai_repo.record_provider_failure = AsyncMock()
    service.ai_repo.record_provider_success = AsyncMock()
    service.ai_repo.log_request = AsyncMock()

    # Mock OpenAI adapter failure and Anthropic adapter success
    mock_openai = AsyncMock()
    mock_openai.execute.side_effect = Exception("OpenAI API Rate Limit 429")

    mock_anthropic = AsyncMock()
    mock_anthropic.execute.return_value = MagicMock(
        content="Anthropic fallback answer",
        model_used="claude-3-5-sonnet",
        provider_type=LLMProviderType.ANTHROPIC,
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        latency_ms=150,
    )

    with patch(
        "app.application.ai.llm_gateway_service.get_adapter_for_provider"
    ) as mock_get_adapter:
        mock_get_adapter.side_effect = lambda ptype: (
            mock_openai if ptype == LLMProviderType.OPENAI else mock_anthropic
        )

        resp = await service.generate_completion(org_id, req)

        assert resp.content == "Anthropic fallback answer"
        assert resp.provider_used == "ANTHROPIC"
        assert service.ai_repo.record_provider_failure.called
        assert service.ai_repo.record_provider_success.called
