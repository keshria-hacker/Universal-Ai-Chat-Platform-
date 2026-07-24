"""
LiteLLM fallback provider - catches any provider not explicitly implemented.
"""
from typing import Any

import litellm

from .base import BaseProvider, ModelInfo


class LiteLLMProvider(BaseProvider):
    """Generic provider using LiteLLM for any supported model."""

    async def list_models(self, api_key: str | None = None) -> list[ModelInfo]:
        # LiteLLM doesn't have a unified model listing - fallback returns empty
        return []

    async def stream_completion(
        self,
        model_id: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> Any:
        # Extract litellm_id from app-side model ID
        litellm_id = model_id
        if "::" in model_id:
            litellm_id = model_id.split("::", 1)[1]

        completion_kwargs = {
            "model": litellm_id,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "timeout": 60,
        }
        if max_tokens:
            completion_kwargs["max_tokens"] = max_tokens
        if api_key:
            completion_kwargs["api_key"] = api_key
        if reasoning_effort and reasoning_effort != "none":
            completion_kwargs["reasoning_effort"] = reasoning_effort

        response = await litellm.acompletion(**completion_kwargs)
        async for chunk in response:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content or ""
            if content:
                yield content