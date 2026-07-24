"""
Reusable test fixtures for Nexus backend tests.

Provides async app client, test database, auth token, and mock HTTP fixtures
for integration tests against the FastAPI application.
"""
import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def app():
    """Build the FastAPI application with a clean test database."""
    # Push test settings before importing app
    import os
    os.environ["APP_DEBUG"] = "false"

    # Use in-memory SQLite for testing
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

    from main import app as _app
    yield _app


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client backed by the FastAPI app (ASGI transport)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register and login a test user, returning auth headers (token + CSRF)."""
    # Register a fresh test user
    register_payload = {
        "username": f"testuser_{id({})}",
        "password": "TestPass123!",
    }
    resp = await client.post("/api/register", json=register_payload)
    if resp.status_code != 200:
        # User may already exist from another fixture — try login
        resp = await client.post("/api/login", json=register_payload)

    assert resp.status_code == 200, f"Auth setup failed: {resp.text}"
    data = resp.json()
    token = data.get("access_token") or data.get("token", "")

    # Extract CSRF token from response cookies
    csrf_token = ""
    for cookie in resp.cookies:
        if cookie.name == "nexus_csrf":
            csrf_token = cookie.value
            break

    headers = {"Authorization": f"Bearer {token}"}
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token

    return headers


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict:
    """Register a test user and return user info + auth."""
    username = f"api_test_{id({})}"
    password = "TestPass123!"
    resp = await client.post("/api/register", json={
        "username": username, "password": password,
    })
    data = resp.json()
    csrf_token = ""
    for cookie in resp.cookies:
        if cookie.name == "nexus_csrf":
            csrf_token = cookie.value
            break
    return {
        "username": username,
        "password": password,
        "token": data.get("access_token") or data.get("token", ""),
        "csrf": csrf_token,
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for provider API calls without real network."""
    with MagicMock() as mock:
        yield mock
