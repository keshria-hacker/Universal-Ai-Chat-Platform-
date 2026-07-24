"""
Universal AI Provider System - Public Facade

This module provides the main public API for the provider system.
All external code should import from here, not from individual modules.
"""
from collections.abc import AsyncGenerator
from typing import Any

# Import provider implementations to register them
from . import (
    anthropic,  # noqa: F401
    gemini,  # noqa: F401
    litellm_fallback,  # noqa: F401
    nvidia,  # noqa: F401
    ollama,  # noqa: F401
    openai_compatible,  # noqa: F401
)
from .base import ModelInfo, ProviderConfig
from .inaccessible import (
    clear_inaccessible,
)
from .key_resolver import get_db_keys, get_static_env_key, list_linked_providers, resolve_api_key
from .model_discovery import (
    cleanup_ollama,
    fetch_models_from_provider,
    fetch_ollama_models,
)
from .registry import init_provider_registry, registry

# Initialize registry on import
_init_done = False


def _ensure_initialized() -> None:
    """Lazy initialization of provider registry."""
    global _init_done
    if not _init_done:
        init_provider_registry()
        # Register custom provider classes
        from .anthropic import AnthropicProvider
        from .gemini import GeminiProvider
        from .nvidia import NVIDIAProvider
        from .ollama import OllamaProvider
        from .openai_compatible import (
            DeepSeekProvider,
            GroqProvider,
            MistralProvider,
            OmniRouteProvider,
            OpenAIProvider,
            OpenRouterProvider,
            TogetherProvider,
        )

        registry.register(
            ProviderConfig(
                provider_id="openai",
                label="OpenAI",
                local=False,
                env_key_name="OPENAI_API_KEY",
                api_base="https://api.openai.com/v1",
                model_endpoint="https://api.openai.com/v1/models",
                auth_type="bearer",
                json_path="data",
                id_field="id",
                litellm_prefix="openai/",
            ),
            OpenAIProvider
        )
        registry.register(
            ProviderConfig(
                provider_id="anthropic",
                label="Anthropic",
                local=False,
                env_key_name="ANTHROPIC_API_KEY",
                api_base="https://api.anthropic.com/v1",
                model_endpoint="https://api.anthropic.com/v1/models",
                auth_type="header",
                auth_header_name="x-api-key",
                extra_headers={"anthropic-version": "2023-06-01"},
                json_path="data",
                id_field="id",
                litellm_prefix="anthropic/",
            ),
            AnthropicProvider
        )
        registry.register(
            ProviderConfig(
                provider_id="nvidia",
                label="NVIDIA NIM",
                local=False,
                env_key_name="NVIDIA_NIM_API_KEY",
                api_base="https://integrate.api.nvidia.com/v1",
                model_endpoint="https://integrate.api.nvidia.com/v1/models",
                auth_type="bearer",
                json_path="data",
                id_field="id",
                litellm_prefix="nvidia_nim/",
            ),
            NVIDIAProvider
        )
        registry.register(
            ProviderConfig(
                provider_id="together",
                label="Together AI",
                local=False,
                env_key_name="TOGETHER_API_KEY",
                api_base="https://api.together.xyz/v1",
                model_endpoint="https://api.together.xyz/v1/models",
                auth_type="bearer",
                json_path="data",
                id_field="id",
                litellm_prefix="together_ai/",
            ),
            TogetherProvider
        )
        registry.register(
            ProviderConfig(
                provider_id="groq",
                label="Groq",
                local=False,
                env_key_name="GROQ_API_KEY",
                api_base="https://api.groq.com/openai/v1",
                model_endpoint="https://api.groq.com/openai/v1/models",
                auth_type="bearer",
                json_path="data",
                id_field="id",
                litellm_prefix="groq/",
            ),
            GroqProvider
        )
        registry.register(
            ProviderConfig(
                provider_id="openrouter",
                label="OpenRouter",
                local=False,
                env_key_name="OPENROUTER_API_KEY",
                api_base="https://openrouter.ai/api/v1",
                model_endpoint="https://openrouter.ai/api/v1/models",
                auth_type="bearer",
                json_path="data",
                id_field="id",
                litellm_prefix="openrouter/",
            ),
            OpenRouterProvider
        )
        registry.register(
            ProviderConfig(
                provider_id="deepseek",
                label="DeepSeek",
                local=False,
                env_key_name="DEEPSEEK_API_KEY",
                api_base="https://api.deepseek.com/v1",
                model_endpoint="https://api.deepseek.com/v1/models",
                auth_type="bearer",
                json_path="data",
                id_field="id",
                litellm_prefix="deepseek/",
            ),
            DeepSeekProvider
        )
        registry.register(
            ProviderConfig(
                provider_id="mistral",
                label="Mistral",
                local=False,
                env_key_name="MISTRAL_API_KEY",
                api_base="https://api.mistral.ai/v1",
                model_endpoint="https://api.mistral.ai/v1/models",
                auth_type="bearer",
                json_path="data",
                id_field="id",
                litellm_prefix="mistral/",
            ),
            MistralProvider
        )
        registry.register(
            ProviderConfig(
                provider_id="gemini",
                label="Gemini",
                local=False,
                env_key_name="GEMINI_API_KEY",
                api_base="https://generativelanguage.googleapis.com/v1beta",
                model_endpoint="https://generativelanguage.googleapis.com/v1beta/models",
                auth_type="query",
                query_key="key",
                json_path="models",
                id_field="name",
                strip_prefix="models/",
                litellm_prefix="gemini/",
            ),
            GeminiProvider
        )
        registry.register(
            ProviderConfig(
                provider_id="ollama",
                label="Ollama",
                local=True,
                env_key_name=None,
                api_base="http://localhost:11434",
                model_endpoint="http://localhost:11434/api/tags",
                auth_type="none",
                json_path="models",
                id_field="name",
                litellm_prefix="ollama/",
            ),
            OllamaProvider
        )
        registry.register(
            ProviderConfig(
                provider_id="omniroute",
                label="OmniRoute",
                local=True,
                env_key_name="OMNIROUTE_API_KEY",
                api_base="http://localhost:20128/v1",
                model_endpoint="http://localhost:20128/v1/models",
                auth_type="bearer",
                json_path="data",
                id_field="id",
                litellm_prefix="openai/",
            ),
            OmniRouteProvider
        )
        _init_done = True


async def list_models(db: Any) -> list[ModelInfo]:
    """Return all selectable models from all linked providers."""
    _ensure_initialized()

    linked = await list_linked_providers(db)

    models: list[ModelInfo] = []

    # Ollama first (local, free, preferred default)
    try:
        ollama_models = await fetch_ollama_models()
        for m in ollama_models:
            models.append(m)
    except Exception:
        pass

    # Cloud providers - fetch concurrently
    async def _fetch_one(pid: str) -> list[ModelInfo]:
        api_key = await resolve_api_key(pid, db)
        if not api_key:
            return []
        config = registry.get_config(pid)
        if not config:
            return []
        try:
            return await fetch_models_from_provider(api_key, config)
        except Exception:
            return []

    if linked:
        import asyncio
        results = await asyncio.gather(
            *[_fetch_one(pid) for pid in linked],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                continue
            models.extend(result)

    # Filter out inaccessible models
    from .inaccessible import is_inaccessible
    models = [m for m in models if not is_inaccessible(m.litellm_id)]

    return models


async def list_provider_status(db: Any) -> list[dict[str, Any]]:
    """Return only providers currently reachable with keys."""
    from .model_discovery import _ollama_reachable

    _ensure_initialized()

    keys = await get_db_keys(db)
    statuses = []

    # Check Ollama
    if await _ollama_reachable():
        statuses.append({
            "id": "ollama",
            "label": "Ollama",
            "state": "online",
        })

    # Check cloud providers
    for pid in ["openai", "anthropic", "nvidia", "together", "groq",
                "openrouter", "deepseek", "mistral", "gemini", "omniroute"]:
        api_key = keys.get(pid) or get_static_env_key(pid)
        if api_key and isinstance(api_key, str):
            try:
                config = registry.get_config(pid)
                if config and await _provider_reachable(config, api_key):
                    statuses.append({
                        "id": pid,
                        "label": config.label,
                        "state": "online",
                    })
            except Exception:
                pass

    return statuses


async def _provider_reachable(config: ProviderConfig, api_key: str) -> bool:
    """Check if provider endpoint is reachable with given key."""
    import httpx

    headers = {"Accept": "application/json"}
    if config.auth_type == "bearer":
        headers["Authorization"] = f"Bearer {api_key}"
    elif config.auth_type == "header":
        headers[config.auth_header_name] = api_key
    if config.extra_headers:
        headers.update(config.extra_headers)

    url = config.model_endpoint
    if config.auth_type == "query" and config.query_key:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{config.query_key}={api_key}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return True
    except httpx.HTTPError:
        return False


async def default_model_id(db: Any) -> str | None:
    """Pick first available model (prefers Ollama)."""
    models = await list_models(db)
    return models[0].id if models else None


async def stream_completion(
    model_id: str,
    messages: list[dict],
    db: Any,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
) -> AsyncGenerator[str]:
    """Stream completion from the appropriate provider."""
    _ensure_initialized()

    # Resolve which provider this model belongs to
    provider_id, litellm_id = _resolve_model(model_id)

    # Get API key
    api_key = await resolve_api_key(provider_id, db)

    # Get provider class
    provider_class = registry.get_provider_class(provider_id)
    if not provider_class:
        # Fallback to LiteLLM
        from .litellm_fallback import LiteLLMProvider
        provider = LiteLLMProvider(registry.get_config(provider_id) or ProviderConfig(
            provider_id=provider_id, label=provider_id, local=False,
            env_key_name=None, api_base="", model_endpoint="",
            json_path="", id_field="", litellm_prefix=""
        ))
    else:
        config = registry.get_config(provider_id)
        if not config:
            raise ValueError(f"Unknown provider: {provider_id}")
        # Pass API key to provider constructor for validation
        provider = provider_class(config, api_key)

    # Stream
    async for chunk in provider.stream_completion(
        model_id=model_id,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        api_key=api_key,
    ):
        yield chunk


def _resolve_model(model_id: str) -> tuple[str, str]:
    """Parse app-side model ID (provider::litellm_id) into components."""
    if "::" not in model_id:
        raise ValueError(f"Invalid model ID format: {model_id}")
    provider_id, litellm_id = model_id.split("::", 1)
    return provider_id, litellm_id


def list_providers_static() -> dict[str, dict]:
    """Return provider metadata without exposing keys.

    ``env_key_set`` reflects *actual* availability of a key in the
    environment — not just whether a config slot exists — so the
    Settings UI correctly shows only linked providers.
    """
    _ensure_initialized()
    return {
        pid: {
            "label": cfg.label,
            "local": cfg.local,
            "env_key_set": bool(get_static_env_key(pid)),
        }
        for pid, cfg in registry.get_all_configs().items()
    }


def clear_inaccessible_models() -> int:
    """Clear the inaccessible model cache."""
    return clear_inaccessible()


# Backwards compatibility exports
from .compat import CURATED_MODELS, MODELS, PROVIDERS  # noqa: E402,F401
from .inaccessible import _inaccessible_models  # noqa: F401

__all__ = [
    # Main API
    "list_models",
    "list_provider_status",
    "default_model_id",
    "stream_completion",
    "list_providers_static",
    "clear_inaccessible_models",
    # Key resolution
    "resolve_api_key",
    "get_db_keys",
    # Models
    "ModelInfo",
    "ProviderConfig",
    # Provider registry
    "registry",
    # Legacy (for compatibility)
    "CURATED_MODELS",
    "MODELS",
    "PROVIDERS",
    "_inaccessible_models",
    "cleanup_ollama",
]