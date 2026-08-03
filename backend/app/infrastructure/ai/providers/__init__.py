"""LLM Provider Adapters Package."""

from typing import Dict, Type

from app.domain.entities.ai import LLMProviderType
from app.infrastructure.ai.providers.anthropic import AnthropicAdapter
from app.infrastructure.ai.providers.base import BaseLLMAdapter
from app.infrastructure.ai.providers.google import GoogleAdapter
from app.infrastructure.ai.providers.local import LocalOllamaAdapter
from app.infrastructure.ai.providers.openai import OpenAIAdapter

ADAPTER_REGISTRY: Dict[LLMProviderType, Type[BaseLLMAdapter]] = {
    LLMProviderType.OPENAI: OpenAIAdapter,
    LLMProviderType.ANTHROPIC: AnthropicAdapter,
    LLMProviderType.GOOGLE: GoogleAdapter,
    LLMProviderType.OLLAMA: LocalOllamaAdapter,
}


def get_adapter_for_provider(provider_type: LLMProviderType) -> BaseLLMAdapter:
    """Instantiate and return the appropriate LLM provider adapter."""
    adapter_cls = ADAPTER_REGISTRY.get(provider_type)
    if not adapter_cls:
        # Fall back to OpenAI or Ollama
        adapter_cls = OpenAIAdapter
    return adapter_cls()


__all__ = [
    "BaseLLMAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "GoogleAdapter",
    "LocalOllamaAdapter",
    "ADAPTER_REGISTRY",
    "get_adapter_for_provider",
]
