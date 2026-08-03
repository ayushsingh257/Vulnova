"""Anthropic API Adapter using httpx REST Client."""

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

logger = get_logger("vulnova.llm_anthropic_adapter")


class AnthropicAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Messages REST API using httpx."""

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.ANTHROPIC

    async def execute(
        self,
        request: LLMRequest,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> LLMResponse:
        base_url = (endpoint or "https://api.anthropic.com/v1").rstrip("/")
        url = f"{base_url}/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key or "",
            "anthropic-version": "2023-06-01",
        }

        # Extract system prompt if present
        system_prompt = ""
        user_messages: List[Dict[str, str]] = []
        for m in request.messages:
            if m.role == "system":
                system_prompt += f"{m.content}\n"
            else:
                user_messages.append({"role": m.role, "content": m.content})

        if not user_messages:
            user_messages = [
                {"role": "user", "content": system_prompt or "Analyze vulnerability"}
            ]
            system_prompt = ""

        payload: Dict[str, Any] = {
            "model": request.model_alias or "claude-3-5-sonnet-20240620",
            "messages": user_messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt.strip()

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)

            latency_ms = int((time.time() - start_time) * 1000)

            if resp.status_code != 200:
                err_msg = f"Anthropic API HTTP {resp.status_code}: {resp.text[:200]}"
                logger.error(
                    "anthropic_adapter.request_failed",
                    status_code=resp.status_code,
                    error=err_msg,
                )
                raise LLMProviderException(err_msg)

            data = resp.json()
            content_blocks = data.get("content", [])
            text_res = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text_res += block.get("text", "")

            usage = data.get("usage", {})
            prompt_tokens = usage.get("input_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0)
            total_tokens = prompt_tokens + completion_tokens

            return LLMResponse(
                content=text_res,
                model_used=request.model_alias,
                provider_type=LLMProviderType.ANTHROPIC,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                status=AIRequestState.COMPLETED,
            )
        except Exception as e:
            if not isinstance(e, LLMProviderException):
                logger.error("anthropic_adapter.execution_error", error=str(e))
                raise LLMProviderException(f"Anthropic adapter error: {str(e)}") from e
            raise
