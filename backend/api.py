"""
api.py — route handlers. Business logic (provider routing, text
extraction) stays in llm.py / document.py; this module wires HTTP in and
out and persists chat state via SQLAlchemy.
"""
import asyncio
import magic
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import llm
import websearch
from database import AsyncSessionLocal, get_db
from document import extract_text, truncate_preview
from prompt_injection import detect_injection, sanitize_for_log
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from models import Chat, Message, ProviderKey, UploadedFile
from schemas import (
    ChatDetailOut,
    ChatOut,
    ChatStreamRequest,
    FileUploadOut,
    ModelInfo,
    ProviderKeyIn,
    ProviderKeyOut,
    ProviderModelEntry,
    ProviderStatus,
    RefreshModelsOut,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings

router = APIRouter()
public_router = APIRouter()

# Magic byte validator for file uploads
# Maps extension to expected MIME types (using python-magic)
ALLOWED_MIME_TYPES = {
    "pdf": ["application/pdf"],
    "docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    "txt": ["text/plain"],
    "csv": ["text/csv"],
    "xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    "pptx": ["application/vnd.openxmlformats-officedocument.presentationml.presentation"],
    "json": ["application/json"],
    "html": ["text/html"],
    "xml": ["application/xml", "text/xml"],
    "md": ["text/markdown"],
    "py": ["text/x-python", "text/plain"],
    "java": ["text/x-java", "text/plain"],
    "js": ["text/javascript", "application/javascript", "text/plain"],
    "c": ["text/x-c", "text/plain"],
    "cpp": ["text/x-c++src", "text/plain"],
    "cs": ["text/x-csharp", "text/plain"],
    "go": ["text/x-go", "text/plain"],
    "rs": ["text/x-rust", "text/plain"],
    "php": ["application/x-php", "text/plain"],
    "sql": ["application/sql", "text/plain"],
    "r": ["text/plain"],
}

_magic = magic.Magic(mime=True)


def sse_event(data: str, event: str | None = None) -> str:
    """Serialize multiline provider output as a valid SSE frame."""
    event_line = f"event: {event}\n" if event else ""
    data_lines = str(data).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # SSE comments (lines starting with :) are ignored by clients but keep connection alive
    if event_line == "" and len(data_lines) == 1 and data_lines[0].startswith(":"):
        return f"{data_lines[0]}\n\n"
    data_text = "\n".join(f"data: {line}" for line in data_lines)
    return f"{event_line}{data_text}\n\n"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@public_router.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


@router.get("/websearch")
async def get_websearch(q: str, max_results: int = 5):
    """Live web search. Works out of the box via DuckDuckGo (no key); upgrade
    by setting WEB_SEARCH_PROVIDER + WEB_SEARCH_API_KEY in .env."""
    if not q or not q.strip():
        raise HTTPException(status_code=422, detail="Query (q) is required")
    try:
        results = await websearch.web_search(q, max_results=max_results)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "query": q,
        "provider": (settings.WEB_SEARCH_PROVIDER or "duckduckgo"),
        "results": [
            {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results
        ],
    }


# ---------------------------------------------------------------------------
# Models & providers
# ---------------------------------------------------------------------------

@router.get("/models", response_model=list[ModelInfo])
async def get_models(db: AsyncSession = Depends(get_db)):
    return await llm.list_models(db)


@router.get("/providers", response_model=list[ProviderStatus])
async def get_providers(db: AsyncSession = Depends(get_db)):
    return await llm.list_provider_status(db)


@router.post("/models/inaccessible/clear", status_code=204)
async def clear_inaccessible_models():
    """Clear the set of models that have been flagged as inaccessible
    (NotFoundError during streaming) so they reappear on the next fetch."""
    llm.clear_inaccessible_models()


# ---------------------------------------------------------------------------
# Provider API key management — this is what lets a user link a provider
# entirely from the Settings UI, no .env editing required.
# ---------------------------------------------------------------------------

@router.get("/settings/providers", response_model=list[ProviderKeyOut])
async def list_provider_keys(db: AsyncSession = Depends(get_db)):
    """Return ALL known providers with their key status and human-readable
    label. Unlike /api/providers (which only shows linked providers), this
    endpoint is used by the Settings UI to let users manage keys for any
    provider — linked or not."""
    db_keys = await llm.get_db_keys(db)
    out = []
    for pid, meta in llm.list_providers_static().items():
        if meta["local"]:
            continue
        db_key = db_keys.get(pid)
        if db_key:
            masked = f"{db_key[:6]}···{db_key[-4:]}" if len(db_key) > 10 else "···"
            out.append(ProviderKeyOut(provider_id=pid, label=meta["label"], linked=True, masked_key=masked))
        elif meta["env_key_set"]:
            out.append(ProviderKeyOut(provider_id=pid, label=meta["label"], linked=True, masked_key="(from .env)"))
        else:
            out.append(ProviderKeyOut(provider_id=pid, label=meta["label"], linked=False, masked_key=None))
    return out


@router.put("/settings/providers/{provider_id}/key", response_model=ProviderKeyOut)
async def set_provider_key(provider_id: str, payload: ProviderKeyIn, db: AsyncSession = Depends(get_db)):
    static = llm.list_providers_static()
    if provider_id not in static:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    if static[provider_id]["local"]:
        raise HTTPException(status_code=400, detail="Local runtimes don't use an API key")

    api_key = payload.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=422, detail="API key cannot be blank")

    existing = await db.get(ProviderKey, provider_id)
    if existing:
        existing.api_key = api_key
    else:
        db.add(ProviderKey(provider_id=provider_id, api_key=api_key))
    await db.commit()

    key = api_key
    masked = f"{key[:6]}···{key[-4:]}" if len(key) > 10 else "···"
    return ProviderKeyOut(provider_id=provider_id, linked=True, masked_key=masked)


@router.delete("/settings/providers/{provider_id}/key", status_code=204)
async def delete_provider_key(provider_id: str, db: AsyncSession = Depends(get_db)):
    static = llm.list_providers_static()
    if provider_id not in static:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    existing = await db.get(ProviderKey, provider_id)
    if existing:
        await db.delete(existing)
        await db.commit()


@router.get("/settings/providers/{provider_id}/models/refresh", response_model=RefreshModelsOut)
async def refresh_provider_models(provider_id: str, db: AsyncSession = Depends(get_db)):
    """Live-fetch the full model catalogue for a linked provider.

    Queries the provider's model listing endpoint (e.g. ``/v1/models``),
    returns the standardized model list with count.  Errors inside the
    fetch function are caught gracefully (returns count=0), so the caller
    always gets a valid response — no 5xx for transient network blips.
    """
    config = llm.registry.get_config(provider_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    if config.local:
        raise HTTPException(status_code=400, detail="Local runtimes don't support model listing")

    api_key = await llm.resolve_api_key(provider_id, db)
    if not api_key:
        raise HTTPException(status_code=400, detail=f"No API key linked for {config.label}")

    models = await llm.fetch_models_from_provider(
        api_key=api_key,
        endpoint_url=config.model_endpoint,
        provider_id=provider_id,
        provider_label=config.label,
        auth_type=config.auth_type,
        auth_header_name=config.auth_header_name or "x-api-key",
        query_key=config.query_key,
        json_path=config.json_path,
        id_field=config.id_field,
        strip_prefix=config.strip_prefix or "",
        extra_headers=config.extra_headers,
        timeout_seconds=20.0,
    )

    return RefreshModelsOut(
        provider_id=provider_id,
        success=True,
        count=len(models),
        models=[ProviderModelEntry(**m) for m in models],
    )


# ---------------------------------------------------------------------------
# Chats (history)
# ---------------------------------------------------------------------------

@router.get("/chats", response_model=list[ChatOut])
async def list_chats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Chat).order_by(Chat.updated_at.desc()).limit(100)
    )
    return result.scalars().all()


@router.get("/chats/{chat_id}", response_model=ChatDetailOut)
async def get_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id).options(selectinload(Chat.messages))
    )
    chat = result.scalar_one_or_none()
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.delete("/chats/{chat_id}", status_code=204)
async def delete_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id).options(selectinload(Chat.messages))
    )
    chat = result.scalar_one_or_none()
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    await db.delete(chat)
    await db.commit()


# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------

@router.post("/files", response_model=FileUploadOut)
async def upload_file(request: Request, file: UploadFile, db: AsyncSession = Depends(get_db)):
    filename = Path(file.filename or "upload").name
    if not filename or filename == ".":
        raise HTTPException(status_code=400, detail="A valid filename is required")
    # Prevent path traversal via ..\ or ../ sequences in the filename
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    extension = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if extension not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: .{extension}")

    # Early size check via Content-Length header — reject before reading into memory
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > settings.MAX_UPLOAD_SIZE_MB:
                raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")
        except (ValueError, TypeError):
            pass  # Malformed header — fall through to the read-based check below

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    # Magic byte validation - verify the file contents match the declared extension
    try:
        detected_mime = _magic.from_buffer(contents)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not determine file type")

    allowed_mimes = ALLOWED_MIME_TYPES.get(extension, [])
    if allowed_mimes and detected_mime not in allowed_mimes:
        raise HTTPException(
            status_code=415,
            detail=f"File content does not match extension .{extension}. Detected: {detected_mime}"
        )

    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex[:12]}_{filename}"
    stored_path = settings.UPLOAD_DIR / stored_name
    stored_path.write_bytes(contents)

    extracted = extract_text(stored_path, extension)

    record = UploadedFile(
        filename=filename,
        stored_path=str(stored_path),
        extension=extension,
        size_bytes=len(contents),
        extracted_text=extracted,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return FileUploadOut(
        file_id=record.id,
        filename=record.filename,
        extension=record.extension,
        size_bytes=record.size_bytes,
        preview=truncate_preview(extracted) if extracted else None,
    )


# ---------------------------------------------------------------------------
# Chat streaming
# ---------------------------------------------------------------------------

# SSE heartbeat interval (seconds) — keeps proxies/load-balancers from timing out
# long-lived streaming connections during slow model generations.
SSE_HEARTBEAT_INTERVAL = 15


@router.post("/chat/stream")


async def chat_stream(payload: ChatStreamRequest, db: AsyncSession = Depends(get_db)):
    # Validate the model exists before allocating any resources — a fast 400
    # is much better than failing mid-stream after the chat has been created.
    model_info = llm._resolve_model(payload.model)
    if model_info is None:
        raise HTTPException(status_code=400, detail=f"Unknown model: {payload.model}")

    # Optional web-search augmentation: when the client requests it, fetch live
    # results for the latest user turn and inject them as context so the model
    # can answer with current information. Failures never break the chat — they
    # surface as a notice inside the stream instead.
    web_context = ""
    if getattr(payload, "web_search", False):
        try:
            last_user = next((m.content for m in reversed(payload.messages) if m.role == "user"), "")
            if last_user:
                results = await websearch.web_search(last_user)
                web_context = websearch.format_context(last_user, results)
        except Exception as exc:  # noqa: BLE001 — surface but don't kill the chat
            web_context = f"[Web search unavailable: {exc}]"

    # 1. Resolve or create the chat
    if payload.chat_id:
        chat = await db.get(Chat, payload.chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
    else:
        first_user_msg = next((m.content for m in payload.messages if m.role == "user"), "New chat")
        chat = Chat(title=first_user_msg[:60], model=payload.model)
        db.add(chat)
        await db.flush()
        await db.commit()
        await db.refresh(chat)

    # 2. Fold any attached files' extracted text into the latest user message
    messages = [m.model_dump() for m in payload.messages]
    if payload.file_ids:
        result = await db.execute(select(UploadedFile).where(UploadedFile.id.in_(payload.file_ids)))
        files = result.scalars().all()
        file_context = "\n\n".join(
            f"--- {f.filename} ---\n{f.extracted_text}" for f in files if f.extracted_text
        )
        if file_context and messages:
            messages[-1]["content"] = f"{messages[-1]['content']}\n\n[Attached files]\n{file_context}"
    if web_context and messages:
        # Inject as a system message so the model sees the sources.
        messages.insert(0, {"role": "system", "content": web_context})

    # 3. Stream the assistant's reply, persisting user + assistant messages atomically
    #    inside the generator so a client disconnect or stream error never leaves
    #    orphaned user messages in the database.
    async def event_generator():
        # Use a dedicated session so the outer request-scoped `db` is free for
        # concurrent requests — prevents race conditions with connection pool.
        async with AsyncSessionLocal() as stream_db:
            collected = ""
            last_heartbeat = time.monotonic()
            try:
                yield sse_event(chat.id, event="chat_id")

                async for token in llm.stream_completion(
                    model_id=payload.model,
                    messages=messages,
                    db=stream_db,
                    temperature=payload.temperature,
                    max_tokens=payload.max_tokens,
                    reasoning_effort=payload.reasoning_effort,
                ):
                    collected += token
                    yield sse_event(token)

                    now = time.monotonic()
                    if now - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                        yield f": heartbeat {int(now)}\n\n"
                        last_heartbeat = now

                if time.monotonic() - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                    yield f": heartbeat {int(time.monotonic())}\n\n"

                if not payload.regenerate:
                    stream_db.add(Message(chat_id=chat.id, role="user",
                                   content=payload.messages[-1].content,
                                   file_ids=",".join(payload.file_ids) or None))
                stream_db.add(Message(chat_id=chat.id, role="assistant", content=collected,
                               model=payload.model))
                # Merge the chat into the new session so the model/updated_at
                # changes are tracked and persisted on commit.
                chat.model = payload.model
                chat.updated_at = datetime.now(UTC)
                await stream_db.merge(chat)
                await stream_db.commit()
                yield sse_event("[DONE]")
            except (GeneratorExit, asyncio.CancelledError):
                await stream_db.rollback()
                # Clean up orphaned chat if this was a new chat
                if not payload.chat_id:
                    await stream_db.execute(delete(Chat).where(Chat.id == chat.id))
                    await stream_db.commit()
                return
            except Exception as exc:
                await stream_db.rollback()
                # Clean up orphaned chat if this was a new chat
                if not payload.chat_id:
                    await stream_db.execute(delete(Chat).where(Chat.id == chat.id))
                    await stream_db.commit()
                yield sse_event(str(exc), event="error")
                return

    return StreamingResponse(event_generator(), media_type="text/event-stream")
