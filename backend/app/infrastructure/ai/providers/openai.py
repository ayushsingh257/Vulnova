"""OpenAI API Adapter using httpx REST Client."""

import time
from typing import Any, Dict, Optional

import httpx

from app.core.exceptions import LLMProviderException
from app.core.logging import get_logger
from app.domain.entities.ai import (
    AIRequestState,
    LLMProviderType,
    LLMRequest,
    LLMResponse,
)
from app.infrastructure.ai.providers.base import BaseLLMAdapter

logger = get_logger("vulnova.llm_openai_adapter")


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI Chat Completions REST API using httpx."""

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OPENAI

    async def execute(
        self,
        request: LLMRequest,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> LLMResponse:
        base_url = (endpoint or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or ''}",
        }

        payload: Dict[str, Any] = {
            "model": request.model_alias or "gpt-4o",
            "messages": [
                {"role": m.role, "content": m.content} for m in request.messages
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)

            latency_ms = int((time.time() - start_time) * 1000)

            if resp.status_code != 200:
                err_msg = f"OpenAI API HTTP {resp.status_code}: {resp.text[:200]}"
                logger.error(
                    "openai_adapter.request_failed",
                    status_code=resp.status_code,
                    error=err_msg,
                )
                raise LLMProviderException(err_msg)

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise LLMProviderException(
                    "OpenAI API returned empty response choices."
                )

            content = choices[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

            return LLMResponse(
                content=content,
                model_used=request.model_alias,
                provider_type=LLMProviderType.OPENAI,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                status=AIRequestState.COMPLETED,
            )
        except Exception as e:
            if not isinstance(e, LLMProviderException):
                logger.error("openai_adapter.execution_error", error=str(e))
                raise LLMProviderException(f"OpenAI adapter error: {str(e)}") from e
            raise
