"""Local Ollama REST API Adapter using httpx Client."""

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

logger = get_logger("vulnova.llm_local_ollama_adapter")


class LocalOllamaAdapter(BaseLLMAdapter):
    """Adapter for Local Ollama REST API using httpx."""

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OLLAMA

    async def execute(
        self,
        request: LLMRequest,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> LLMResponse:
        base_url = (endpoint or "http://localhost:11434").rstrip("/")
        url = f"{base_url}/api/chat"

        payload: Dict[str, Any] = {
            "model": request.model_alias or "llama3",
            "messages": [
                {"role": m.role, "content": m.content} for m in request.messages
            ],
            "stream": False,
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)

            latency_ms = int((time.time() - start_time) * 1000)

            if resp.status_code != 200:
                err_msg = f"Local Ollama API HTTP {resp.status_code}: {resp.text[:200]}"
                logger.error(
                    "ollama_adapter.request_failed",
                    status_code=resp.status_code,
                    error=err_msg,
                )
                raise LLMProviderException(err_msg)

            data = resp.json()
            message_obj = data.get("message", {})
            content = message_obj.get("content", "")

            prompt_eval_count = data.get("prompt_eval_count", 0)
            eval_count = data.get("eval_count", 0)
            total_tokens = prompt_eval_count + eval_count

            return LLMResponse(
                content=content,
                model_used=request.model_alias or "llama3",
                provider_type=LLMProviderType.OLLAMA,
                prompt_tokens=prompt_eval_count,
                completion_tokens=eval_count,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                status=AIRequestState.COMPLETED,
                cost_usd=0.0,  # Local execution cost
            )
        except Exception as e:
            if not isinstance(e, LLMProviderException):
                logger.error("ollama_adapter.execution_error", error=str(e))
                raise LLMProviderException(
                    f"Local Ollama adapter error: {str(e)}"
                ) from e
            raise
