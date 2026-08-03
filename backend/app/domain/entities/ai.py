"""Pure Domain Entities & Enums for Multi-Provider LLM Gateway & Prompt Orchestrator."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    GOOGLE = "GOOGLE"
    OLLAMA = "OLLAMA"
    CUSTOM = "CUSTOM"


class AIModelCapability(str, Enum):
    """Capabilities supported by LLM models."""

    CHAT = "CHAT"
    COMPLETION = "COMPLETION"
    EMBEDDING = "EMBEDDING"
    VISION = "VISION"
    CODE_GEN = "CODE_GEN"


class PromptCategory(str, Enum):
    """Categories of versioned security prompt templates."""

    FINDING_EXPLAINER = "FINDING_EXPLAINER"
    ATTACK_PATH_SYNTHESIS = "ATTACK_PATH_SYNTHESIS"
    REMEDIATION_PATCH = "REMEDIATION_PATCH"
    SYSTEM_PROMPT = "SYSTEM_PROMPT"
    CUSTOM = "CUSTOM"


class AIRequestState(str, Enum):
    """Lifecycle execution status of an AI gateway request."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FALLBACK_TRIGGERED = "FALLBACK_TRIGGERED"


@dataclass
class LLMMessage:
    """Standardized chat message payload."""

    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class LLMRequest:
    """Standardized gateway request to an LLM provider."""

    messages: List[LLMMessage]
    model_alias: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.2
    prompt_category: Optional[PromptCategory] = None
    stream: bool = False


@dataclass
class LLMResponse:
    """Standardized gateway response payload from an LLM provider."""

    content: str
    model_used: str
    provider_type: LLMProviderType
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    status: AIRequestState = AIRequestState.COMPLETED
    error_message: Optional[str] = None


@dataclass
class ProviderHealthState:
    """Track provider health, failures, and cooldown periods."""

    provider_id: UUID
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_failure_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None


@dataclass
class LLMProvider:
    """Domain entity representing a configured LLM provider."""

    organization_id: UUID
    provider_type: LLMProviderType
    name: str
    id: UUID = field(default_factory=uuid4)
    api_endpoint: Optional[str] = None
    encrypted_api_key: Optional[str] = None
    priority: int = 10
    is_active: bool = True
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_failure_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LLMModel:
    """Domain entity representing a registered model and pricing metadata."""

    organization_id: UUID
    provider_type: LLMProviderType
    model_alias: str
    model_name: str
    id: UUID = field(default_factory=uuid4)
    context_window_tokens: int = 128000
    max_output_tokens: int = 4096
    input_cost_per_1k_tokens: float = 0.0
    output_cost_per_1k_tokens: float = 0.0
    is_default: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PromptTemplate:
    """Domain entity representing an immutable versioned security prompt template."""

    organization_id: UUID
    category: PromptCategory
    name: str
    version: int
    system_prompt: str
    user_prompt_template: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
