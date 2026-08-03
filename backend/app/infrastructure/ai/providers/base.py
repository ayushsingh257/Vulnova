"""Abstract Base LLM Adapter Interface."""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.ai import LLMProviderType, LLMRequest, LLMResponse


class BaseLLMAdapter(ABC):
    """Abstract interface for provider-independent LLM API adapters."""

    @property
    @abstractmethod
    def provider_type(self) -> LLMProviderType:
        """Return the provider type enum."""
        pass

    @abstractmethod
    async def execute(
        self,
        request: LLMRequest,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> LLMResponse:
        """Execute chat completion request against LLM provider endpoint.

        Args:
            request: Standardized gateway request payload.
            api_key: Decrypted plain text API key.
            endpoint: Optional custom base URL endpoint override.

        Returns:
            Standardized LLMResponse domain object.
        """
        pass

    def count_tokens(self, text: str) -> int:
        """Estimate token count for a text string (rough heuristic: ~4 chars per token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)
