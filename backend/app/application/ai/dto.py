"""Pydantic v2 DTO Schemas for Multi-Provider LLM Gateway & Prompt Orchestrator."""

from typing import List, Optional

from pydantic import BaseModel


class CreateProviderRequest(BaseModel):
    """Request model for configuring an LLM provider."""

    provider_type: str  # OPENAI, ANTHROPIC, GOOGLE, OLLAMA, CUSTOM
    name: str
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    priority: int = 10


class LLMProviderConfigDTO(BaseModel):
    """DTO representing a configured LLM provider (secrets masked)."""

    id: str
    provider_type: str
    name: str
    api_endpoint: Optional[str] = None
    priority: int
    is_active: bool
    is_healthy: bool
    consecutive_failures: int
    cooldown_until: Optional[str] = None
    created_at: str


class RegisterModelRequest(BaseModel):
    """Request model for registering a supported LLM model."""

    provider_type: str
    model_alias: str
    model_name: str
    context_window_tokens: int = 128000
    max_output_tokens: int = 4096
    input_cost_per_1k_tokens: float = 0.0
    output_cost_per_1k_tokens: float = 0.0
    is_default: bool = False


class LLMModelDTO(BaseModel):
    """DTO representing a registered LLM model."""

    id: str
    provider_type: str
    model_alias: str
    model_name: str
    context_window_tokens: int
    max_output_tokens: int
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    is_default: bool
    created_at: str


class CreatePromptTemplateRequest(BaseModel):
    """Request model for creating an immutable versioned prompt template."""

    category: str  # FINDING_EXPLAINER, ATTACK_PATH_SYNTHESIS, REMEDIATION_PATCH, SYSTEM_PROMPT
    name: str
    system_prompt: str
    user_prompt_template: str


class PromptTemplateDTO(BaseModel):
    """DTO representing an immutable versioned prompt template."""

    id: str
    category: str
    name: str
    version: int
    system_prompt: str
    user_prompt_template: str
    is_active: bool
    created_at: str


class LLMMessageDTO(BaseModel):
    """Message item for AI chat requests."""

    role: str
    content: str


class AIChatCompletionRequest(BaseModel):
    """Request model for AI chat completion execution."""

    messages: List[LLMMessageDTO]
    model_alias: Optional[str] = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.2
    prompt_category: Optional[str] = None


class AIChatCompletionResponse(BaseModel):
    """Response model for AI chat completion execution."""

    content: str
    model_used: str
    provider_used: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    status: str


class AIUsageSummaryDTO(BaseModel):
    """DTO summarizing organizational token usage and cost analytics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class LLMRequestLogDTO(BaseModel):
    """DTO representing a single historical AI request audit log."""

    id: str
    provider_type: str
    model_used: str
    prompt_category: Optional[str] = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    status: str
    error_message: Optional[str] = None
    created_at: str
