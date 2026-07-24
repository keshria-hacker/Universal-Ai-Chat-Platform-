# Pull Request Plan: Security Hardening & Refactoring (v1.1)

**Branch**: `security-v1.1`
**Target**: `main`
**Status**: Ready for review

---

## Overview

This PR hardens the Universal AI Chat Platform against OWASP Top 10 vulnerabilities,
refactors the monolithic `llm.py` into a modular provider system, adds database
migrations, and establishes code quality tooling. All 104 tests pass, ruff is clean.

---

## Changesets (in application order)

### Changeset 1: Encrypt API Keys at Rest

**Files**: `backend/security.py` (new), `backend/models.py` (modified), `backend/config.py` (modified)

**Severity**: CRITICAL — API keys stored in plaintext in SQLite

`backend/security.py` — New module providing Fernet (AES-128-GCM) encryption:
- `encrypt_field(plaintext)` → bytes
- `decrypt_field(ciphertext)` → str
- `EncryptionError` for failures (key mismatch, corrupted data)

`backend/models.py` — `ProviderKey` table changes:
- Column renamed from `api_key: str` to `api_key_encrypted: bytes` (LargeBinary)
- `@hybrid_property api_key` transparently decrypts on read
- `@api_key.setter` encrypts on write
- `@api_key.expression` returns SQL NULL (encrypted column is not queryable)

`backend/config.py` — Added `MASTER_KEY: str | None` setting

**Usage**: Keys set via Settings UI or `.env` are encrypted at rest. The hybrid
property means `record.api_key` works transparently. Requires `MASTER_KEY` env var.

**Rollback**: Revert `ProviderKey` columns, remove `security.py`.

---

### Changeset 2: CSRF Validation Enforcement

**Files**: `backend/auth.py` (modified), `backend/main.py` (modified)

**Severity**: HIGH — double-submit cookie CSRF protection

`backend/auth.py`:
- `verify_csrf(request)` — checks `X-CSRF-Token` header matches `nexus_csrf` cookie
- Only enforced for mutating methods (POST/PUT/DELETE)
- Uses `hmac.compare_digest` for constant-time comparison
- CSRF token generated on login, returned in `AuthTokenOut`

`backend/main.py`:
- Fixed `csrf_middleware` to catch `HTTPException` and return `JSONResponse`
  instead of letting it propagate as unhandled exception (BaseHTTPMiddleware wraps
  in `ExceptionGroup` → 500 crash)

**Impact**: All mutation endpoints require CSRF double-submit cookie. Frontend
sends `X-CSRF-Token` header from login response with every mutation.

---

### Changeset 3: DEBUG=False Default, CORS Hardening, Single-User Mode

**File**: `backend/config.py`

**Severity**: HIGH

- `DEBUG: bool = Field(default=False, ...)` — was `True`, stack traces no longer
  leak to clients in production
- Removed `"null"` from `ALLOWED_ORIGINS` — prevents CORS bypass via sandboxed iframe
- Added `http://localhost:3000` to allowed origins (common dev port)

---

### Changeset 4: Request ID Propagation

**Files**: `backend/middleware/request_id.py` (new), `backend/main.py` (modified)

**Severity**: MEDIUM — distributed tracing

New `RequestIDMiddleware`:
- Extracts `X-Request-ID` from incoming request (trace continuation)
- Generates short UUID (12 hex chars) if header absent
- Stores in `request.state.request_id` for downstream access
- Adds `X-Request-ID` header to all responses

Registered as outermost middleware so `request_id` is available to all downstream
middleware and routes. `RequestLoggingMiddleware` includes `request_id` in every
structured log line.

---

### Changeset 5: Rate Limiting with Redis Fallback

**Files**: `backend/ratelimit_redis.py` (new), `backend/ratelimit.py` (modified),
`backend/config.py` (modified), `backend/main.py` (modified)

**Severity**: MEDIUM — brute-force and DoS protection

`backend/ratelimit_redis.py`:
- `MemoryStore` — async in-memory sliding window (same algorithm as original)
- `RedisStore` — Redis-backed sliding window using sorted sets with atomic pipeline
- `get_rate_limit_store()` — auto-detecting factory: Redis when `REDIS_URL` set,
  in-memory otherwise
- Transparent fallback: Redis unavailability degrades to in-memory

`backend/ratelimit.py`:
- `RateLimitMiddleware` now uses async store (lazy-init on first request)
- Auto-detects Redis vs in-memory backing store

Per-endpoint limits: login (5/min), register (3/hr), forgot-password (3/hr),
reset-password (5/hr), chat stream (30/min IP, 60/min user), files (20/min),
skills execute (10/min).

---

### Changeset 6: Refactor llm.py → Modular Provider System

**Files**: `backend/providers/` (11 files, new), `backend/llm.py` (rewritten)

**Severity**: MEDIUM — architectural improvement

**New structure**:
```
backend/providers/
├── __init__.py          # Public facade: stream_completion, list_models, registry
├── base.py              # BaseProvider ABC, ProviderConfig, ModelInfo
├── registry.py          # ProviderRegistry singleton
├── key_resolver.py      # resolve_api_key() — env → DB → None
├── inaccessible.py      # InaccessibleTracker for failed model IDs
├── model_discovery.py   # fetch_models_from_provider(),
├── openai_compatible.py # OpenAI, Together, Groq, OpenRouter, DeepSeek, Mistral, OmniRoute
├── anthropic.py         # AnthropicProvider
├── ollama.py            # OllamaProvider (auto-start, health checks)
├── gemini.py            # GeminiProvider (query-key auth)
└── litellm_fallback.py  # LiteLLMProvider (optional fallback)
```

**Key design decisions**:
- `BaseProvider` abstract class with `stream_completion()` interface
- `ProviderRegistry` singleton with `get_config()`, `register()`, `get_provider_class()`
- `_ensure_initialized()` lazy-init pattern avoids circular imports
- `llm.py` reduced from ~400 to ~40 lines — backward-compatible facade
- All existing `from llm import ...` continue to work

---

### Changeset 7: API Key Sanitization in Logs

**File**: `backend/llm.py` — `sanitize_error()`

**Severity**: HIGH

`sanitize_error()` redacts API key patterns for all providers before logging:
```
sk-...           OpenAI         sk-proj-xxxx
sk-ant-...       Anthropic      sk-ant-xxxx
AIza...          Gemini         AIzaSyDxxxx
nvapi-...        NVIDIA NIM     nvapi-xxxx
tgp_v1_...       Together AI    tgp_v1_xxxx
gsk_...          Groq           gsk_xxxx
sk-or-v1-...     OpenRouter     sk-or-v1-xxxx
[base64 40+]     Generic        AbCdEf...==
[hex 40+]        Generic        a1b2c3d4...
Bearer ...       Bearer token   ***REDACTED***
```

---

### Changeset 8: Security Headers

**File**: `backend/main.py`

**Severity**: MEDIUM

Every response includes:
- `Content-Security-Policy`: strict with `frame-ancestors 'none'`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Process-Time` (performance monitoring)

---

### Changeset 9: Fix Provider Endpoint 500 Errors

**Files**: `backend/providers/model_discovery.py`, `backend/api.py`, `backend/providers/__init__.py`

**Severity**: HIGH — production blockers

Three root causes fixed:
1. **Missing `_ollama_reachable()`**: Function imported by `__init__.py` from
   `model_discovery.py` but never defined. Added async health check.
2. **Env var name used as API key value**: `config.env_key_name` returned
   `"OPENAI_API_KEY"` (variable name) instead of its value. Changed to
   `get_static_env_key(pid)` which resolves the actual env var value.
3. **Missing `PROVIDER_MODEL_API` attribute**: `api.py` referenced
   `llm.PROVIDER_MODEL_API` which didn't exist. Refactored to use
   `llm.registry.get_config(provider_id)`.

---

### Changeset 10: Rate Limit Forgot/Reset Password

**File**: `backend/ratelimit.py`

**Severity**: MEDIUM

Added per-endpoint limits for password reset endpoints:
```python
"/api/auth/forgot-password": [3 req/hr per IP, 3 req/hr per user]
"/api/auth/reset-password":  [5 req/hr per IP, 5 req/hr per user]
```

---

### Changeset 11: Response Validation — Model Required

**Files**: `backend/schemas.py`, `backend/api.py`, `backend/providers/__init__.py`

**Severity**: MEDIUM

`ChatStreamRequest.model` changed from `str = ""` to `Field(min_length=1, ...)`:
- Empty model string rejected at validation layer (422) instead of failing mid-stream
- `_resolve_model()` returns None for unknown models — endpoint checks `if model_info is None`
  instead of only catching `ValueError`
- 2 failing tests fixed (test adapted, 1 added for required field)

---

## Test Plan

### Pre-merge
- [ ] `ruff check backend/` — clean
- [ ] `python -m pytest tests/` — 104 passed
- [ ] `alembic check` — no unapplied migrations

### Security verification

| Check | Expected |
|-------|----------|
| Keys encrypted in DB | `sqlite3 history/nexus.db "SELECT hex(api_key_encrypted) FROM provider_keys LIMIT 1"` — non-null, long hex |
| CSRF blocks mutation | `curl -X POST /api/chat/stream` without header — 403 |
| CSRF allows valid | Login → extract cookie + token → POST with both — 200 |
| Debug off by default | `APP_DEBUG` unset → `settings.DEBUG == False` |
| CORS rejects null | `Origin: null` → rejected |
| Rate limit | 6 rapid login attempts → 429 on 6th |
| Request ID traces | `curl -H "X-Request-ID: abc123" ...` → response has `X-Request-ID: abc123` |

### Functional verification
- `GET /api/health` → 200
- `GET /api/providers` → 200 (no more 500)
- `POST /api/chat/stream` with valid model → SSE stream → `[DONE]`
- Login → logout → login (session rotation works)
- Forgot password → reset → login with new password
- `POST /api/chat/stream` with empty model → 422

---

## Rollback Plan

Each changeset independently revertible:

| Changeset | Rollback |
|-----------|----------|
| #1 Encryption | Revert `ProviderKey` columns, remove `security.py` |
| #2 CSRF | Remove middleware registration |
| #3 CORS/Debug | Revert config defaults |
| #4 Request ID | Remove middleware + logging changes |
| #5 Rate limit | Remove middleware, remove `ratelimit_redis.py` |
| #6 llm.py refactor | `git revert` providers/, restore original `llm.py` |
| #7 Sanitization | Revert `sanitize_error()` |
| #8 Headers | Remove `SecurityHeadersMiddleware` |
| #9 Provider fixes | Remove individual function fixes |
| #10 Rate limit endpoint | Revert ratelimit.py |
| #11 Model required | Revert schemas.py Field change |

---

## Dependencies Added

- `redis >= 8.0` — for distributed rate limiting (feature-gated, optional)

Dev-only (in `requirements-dev.txt`):
- `ruff`, `mypy`, `bandit`, `pre-commit`
- `pytest`, `pytest-asyncio`, `pytest-cov`
