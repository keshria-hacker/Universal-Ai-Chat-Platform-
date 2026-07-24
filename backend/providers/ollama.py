"""
Ollama provider - local models with native streaming.
"""
import asyncio
import json
import shutil
import subprocess
from typing import Any

import httpx

from config import settings

from .base import BaseProvider, ModelInfo
from .inaccessible import is_inaccessible

# Global process tracking
_ollama_process: subprocess.Popen | None = None
_ollama_start_attempted = False


async def _try_start_ollama() -> None:
    """Launch Ollama server in background if not already running."""
    global _ollama_process, _ollama_start_attempted
    if _ollama_start_attempted:
        return
    _ollama_start_attempted = True

    exe = shutil.which("ollama") or shutil.which("ollama.exe")
    if not exe:
        return
    try:
        _ollama_process = subprocess.Popen(
            [exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        # Give it a moment to start
        await asyncio.sleep(2)
    except Exception:
        _ollama_process = None


def _cleanup_ollama() -> None:
    """Cleanup Ollama process on shutdown."""
    global _ollama_process
    if _ollama_process:
        try:
            _ollama_process.terminate()
            _ollama_process.wait(timeout=5)
        except Exception:
            from contextlib import suppress

            with suppress(Exception):
                _ollama_process.kill()
        _ollama_process = None


class OllamaProvider(BaseProvider):
    """Ollama local model provider with native streaming API."""

    async def list_models(self, api_key: str | None = None) -> list[ModelInfo]:
        await _try_start_ollama()

        models = []
        # Connection timeout: 5s, Total timeout: 10s
        timeout = httpx.Timeout(10.0, connect=5.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags",
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()

                for entry in payload.get("models", []) or []:
                    if not isinstance(entry, dict):
                        continue
                    model_id = entry.get("name")
                    if not model_id:
                        continue

                    # Skip known non-chat models
                    lowered = model_id.lower()
                    if any(marker in lowered for marker in ("embedding", "embed", "rerank")):
                        continue

                    litellm_id = f"ollama/{model_id}"
                    if is_inaccessible(litellm_id):
                        continue

                    models.append(ModelInfo(
                        id=f"ollama::{litellm_id}",
                        name=model_id,
                        provider_id="ollama",
                        provider_label="Ollama",
                        litellm_id=litellm_id,
                    ))
        except (httpx.HTTPError, ValueError, KeyError):
            pass

        return models

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
        """Use Ollama's native /api/chat endpoint for streaming."""
        await _try_start_ollama()

        # Extract model name from litellm_id
        litellm_id = model_id
        if "::" in model_id:
            litellm_id = model_id.split("::", 1)[1]

        model_name = litellm_id
        if model_name.startswith("ollama/"):
            model_name = model_name[len("ollama/"):]

        base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        endpoint = f"{base_url}/api/chat"

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        # Connection timeout: 5s, Total timeout: 90s (longer for streaming)
        timeout = httpx.Timeout(90.0, connect=5.0)
        yielded_content = False

        try:
            async with (
                httpx.AsyncClient(timeout=timeout) as client,
                client.stream("POST", endpoint, json=payload) as response,
            ):
                response.raise_for_status()
                async for line in response.aiter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)
                        if chunk.get("error"):
                            raise RuntimeError(chunk["error"])
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yielded_content = True
                            yield content
            if not yielded_content:
                raise RuntimeError(
                    "Ollama returned no visible text. Try increasing the output token limit."
                )
        except (httpx.HTTPError, json.JSONDecodeError, RuntimeError) as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc