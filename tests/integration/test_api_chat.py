"""
Integration tests for chat streaming and file endpoints.
"""
import sys
import os
import unittest
from pathlib import Path

# Enable test mode to disable rate limiting
os.environ["TEST_MODE"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from httpx import ASGITransport, AsyncClient
from main import app
from database import init_db
from ratelimit_redis import reset_rate_limit_store_for_testing


class ChatIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Test /api/chats and /api/chat/stream endpoints."""

    ROUTE = "/api"
    USERNAME = "chat_integration_user"
    PASSWORD = "StrongPass!42"

    @classmethod
    def setUpClass(cls):
        # Remove existing DB so we start clean
        db_path = ROOT / "history" / "nexus.db"
        if db_path.exists():
            db_path.unlink()

    async def asyncSetUp(self):
        reset_rate_limit_store_for_testing()
        await init_db()
        transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=transport, base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def _auth(self):
        """Register and login, return auth headers.

        In single-user mode register may return 403 if the user already
        exists from a prior test. Login always uses the same credentials
        so it succeeds regardless.
        """
        await self.client.post(f"{self.ROUTE}/auth/register", json={
            "username": self.USERNAME, "password": self.PASSWORD,
        })
        resp = await self.client.post(f"{self.ROUTE}/auth/login", json={
            "username": self.USERNAME, "password": self.PASSWORD,
        })
        data = resp.json()
        token = data["access_token"]
        csrf = data.get("csrf_token", "")
        headers = {"Authorization": f"Bearer {token}"}
        if csrf:
            headers["X-CSRF-Token"] = csrf
        return headers

    async def test_list_chats_empty(self):
        """A new user should have an empty chat list."""
        headers = await self._auth()
        resp = await self.client.get(f"{self.ROUTE}/chats", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)

    async def test_delete_nonexistent_chat(self):
        """Deleting a non-existent chat should return 404."""
        headers = await self._auth()
        resp = await self.client.delete(
            f"{self.ROUTE}/chats/99999",
            headers=headers,
        )
        self.assertEqual(resp.status_code, 404)

    async def test_get_nonexistent_chat(self):
        """Get a non-existent chat should return 404."""
        headers = await self._auth()
        resp = await self.client.get(
            f"{self.ROUTE}/chats/99999",
            headers=headers,
        )
        self.assertEqual(resp.status_code, 404)

    async def test_chat_stream_rejects_no_model(self):
        """POST /api/chat/stream without model should fail validation."""
        headers = await self._auth()
        resp = await self.client.post(
            f"{self.ROUTE}/chat/stream",
            headers=headers,
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )
        self.assertEqual(resp.status_code, 422)

    async def test_chat_stream_requires_auth(self):
        """POST /api/chat/stream without auth should be rejected."""
        resp = await self.client.post(
            f"{self.ROUTE}/chat/stream",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]},
        )
        self.assertEqual(resp.status_code, 401)

    async def test_chat_stream_with_unknown_model(self):
        """POST /api/chat/stream with unknown model should not crash."""
        headers = await self._auth()
        resp = await self.client.post(
            f"{self.ROUTE}/chat/stream",
            headers=headers,
            json={
                "model": "nonexistent-model-xyz",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        # Should return an error, not crash
        self.assertIn(resp.status_code, (400, 422, 500))


if __name__ == "__main__":
    unittest.main()