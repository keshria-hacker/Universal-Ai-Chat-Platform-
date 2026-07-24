"""
Live model discovery - fetches available models from provider APIs.
"""
import asyncio
import json

import httpx

from .base import NON_CHAT_MARKERS, ModelInfo, ProviderConfig
from .inaccessible import is_inaccessible


async def fetch_models_from_provider(
    api_key: str,
    config: ProviderConfig,
    timeout_seconds: float = 20.0,
) -> list[ModelInfo]:
    """Fetch all available models from a provider's model listing endpoint."""
    if not api_key:
        return []

    headers = {"Accept": "application/json"}
    if config.auth_type == "bearer":
        headers["Authorization"] = f"Bearer {api_key}"
    elif config.auth_type == "header":
        headers[config.auth_header_name] = api_key
    if config.extra_headers:
        headers.update(config.extra_headers)

    is_query_auth = config.auth_type == "query"
    query_key_name = config.query_key if is_query_auth else None

    all_models: list[ModelInfo] = []
    seen_ids: set[str] = set()
    url = config.model_endpoint

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds, connect=min(10.0, timeout_seconds / 2))
        ) as client:
            visited: set[str] = set()

            while url and url not in visited:
                visited.add(url)

                # Attach query auth (Gemini-style) per request
                request_url = url
                if is_query_auth and query_key_name:
                    sep = "&" if "?" in url else "?"
                    request_url = f"{url}{sep}{query_key_name}={api_key}"

                response = await client.get(request_url, headers=headers)
                response.raise_for_status()
                payload = response.json()

                for entry in payload.get(config.json_path, []) or []:
                    if not isinstance(entry, dict):
                        continue

                    raw_id = entry.get(config.id_field)
                    if not raw_id or not isinstance(raw_id, str):
                        continue

                    model_id = str(raw_id)
                    if config.strip_prefix and model_id.startswith(config.strip_prefix):
                        model_id = model_id[len(config.strip_prefix):]
                    if not model_id or model_id in seen_ids:
                        continue

                    # Filter non-chat models
                    lowered = model_id.lower()
                    if any(marker in lowered for marker in NON_CHAT_MARKERS):
                        continue

                    seen_ids.add(model_id)

                    # Derive name
                    name = _derive_name(model_id, entry, config)

                    # Extract description if available
                    description = ""
                    if config.description_field:
                        raw_desc = entry.get(config.description_field)
                        if raw_desc and isinstance(raw_desc, str):
                            description = raw_desc

                    # Build litellm_id with prefix
                    litellm_id = model_id
                    if config.litellm_prefix and not model_id.startswith(config.litellm_prefix):
                        litellm_id = f"{config.litellm_prefix}{model_id}"

                    # Skip if known inaccessible
                    if is_inaccessible(litellm_id):
                        continue

                    all_models.append(ModelInfo(
                        id=f"{config.provider_id}::{litellm_id}",
                        name=name,
                        provider_id=config.provider_id,
                        provider_label=config.label,
                        litellm_id=litellm_id,
                        description=description,
                        model_id=model_id,
                    ))

                # Follow pagination
                next_url = payload.get("next")
                if next_url and isinstance(next_url, str) and next_url not in visited:
                    url = next_url
                else:
                    url = None

    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        # Return whatever we collected before the failure
        pass

    return all_models


def _derive_name(model_id: str, entry: dict, config: ProviderConfig) -> str:
    """Derive a human-readable name from the model entry."""
    if config.name_field:
        raw_name = entry.get(config.name_field)
        if raw_name and isinstance(raw_name, str):
            return raw_name
    # Fallback: last segment after /
    return model_id.rsplit("/", maxsplit=1)[-1] if "/" in model_id else model_id


async def _ollama_reachable(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama server is reachable."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


async def fetch_ollama_models(base_url: str = "http://localhost:11434") -> list[ModelInfo]:
    """Fetch models from local Ollama server."""
    endpoint = f"{base_url.rstrip('/')}/api/tags"
    models: list[ModelInfo] = []

    # Try direct connection first
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            for item in response.json().get("models", []):
                if isinstance(item.get("name"), str) and item["name"]:
                    name = item["name"]
                    models.append(ModelInfo(
                        id=f"ollama::{name}",
                        name=name,
                        provider_id="ollama",
                        provider_label="Ollama",
                        litellm_id=f"ollama/{name}",
                    ))
        return models
    except httpx.HTTPError:
        pass

    # Auto-start Ollama and retry with backoff
    from .ollama import _try_start_ollama as _async_ollama_start
    await _async_ollama_start()

    backoff_delays = [1.0, 2.0, 3.0, 5.0]
    for delay in backoff_delays:
        await asyncio.sleep(delay)
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                models = []
                for item in response.json().get("models", []):
                    if isinstance(item.get("name"), str) and item["name"]:
                        name = item["name"]
                        models.append(ModelInfo(
                            id=f"ollama::{name}",
                            name=name,
                            provider_id="ollama",
                            provider_label="Ollama",
                            litellm_id=f"ollama/{name}",
                        ))
                return models
        except httpx.HTTPError:
            continue

    return models


# Re-export Ollama process management from ollama.py (single source of truth)
from .ollama import _ollama_start_attempted, _ollama_process, _cleanup_ollama as cleanup_ollama  # noqa: F401