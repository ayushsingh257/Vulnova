"""Google Gemini API Adapter using httpx REST Client."""

import time
from typing import Any, Dict, List, Optional

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

logger = get_logger("vulnova.llm_google_adapter")


class GoogleAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini generateContent REST API using httpx."""

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.GOOGLE

    async def execute(
        self,
        request: LLMRequest,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> LLMResponse:
        model = request.model_alias or "gemini-1.5-pro"
        base_url = (
            endpoint or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")
        url = f"{base_url}/models/{model}:generateContent?key={api_key or ''}"

        contents: List[Dict[str, Any]] = []
        for m in request.messages:
            role_mapped = "user" if m.role in ("user", "system") else "model"
            contents.append({"role": role_mapped, "parts": [{"text": m.content}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
            },
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)

            latency_ms = int((time.time() - start_time) * 1000)

            if resp.status_code != 200:
                err_msg = (
                    f"Google Gemini API HTTP {resp.status_code}: {resp.text[:200]}"
                )
                logger.error(
                    "google_adapter.request_failed",
                    status_code=resp.status_code,
                    error=err_msg,
                )
                raise LLMProviderException(err_msg)

            data = resp.json()
            candidates = data.get("candidates", [])
            text_res = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for p in parts:
                    text_res += p.get("text", "")

            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)
            total_tokens = usage.get(
                "totalTokenCount", prompt_tokens + completion_tokens
            )

            return LLMResponse(
                content=text_res,
                model_used=model,
                provider_type=LLMProviderType.GOOGLE,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                status=AIRequestState.COMPLETED,
            )
        except Exception as e:
            if not isinstance(e, LLMProviderException):
                logger.error("google_adapter.execution_error", error=str(e))
                raise LLMProviderException(f"Google adapter error: {str(e)}") from e
            raise
