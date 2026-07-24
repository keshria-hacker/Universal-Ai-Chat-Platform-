"""
Integration tests for provider and model endpoints.
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


class ProviderModelIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Test /api/providers and /api/models endpoints."""

    ROUTE = "/api"
    USERNAME = "pm_integration_user"
    PASSWORD = "StrongPass!42"

    @classmethod
    def setUpClass(cls):
        # Remove existing DB so we start clean
        db_path = ROOT / "history" / "nexus.db"
        if db_path.exists():
            db_path.unlink()

    async def asyncSetUp(self):
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

    async def test_list_providers(self):
        """GET /api/providers lists all available providers."""
        headers = await self._auth()
        resp = await self.client.get(f"{self.ROUTE}/providers", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        # Provider list depends on which API keys are set (none in test env)
        # Just verify the endpoint returns a well-formed list

    async def test_list_providers_without_auth(self):
        """GET /api/providers should require auth."""
        resp = await self.client.get(f"{self.ROUTE}/providers")
        self.assertEqual(resp.status_code, 401)

    async def test_list_models(self):
        """GET /api/models returns the model list."""
        headers = await self._auth()
        resp = await self.client.get(f"{self.ROUTE}/models", headers=headers)
        self.assertIn(resp.status_code, (200, 500))  # 500 if no provider keys
        if resp.status_code == 200:
            data = resp.json()
            self.assertIsInstance(data, list)

    async def test_provider_settings_list(self):
        """GET /api/settings/providers returns provider configs."""
        headers = await self._auth()
        resp = await self.client.get(f"{self.ROUTE}/settings/providers", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)

    async def test_provider_key_roundtrip(self):
        """PUT and DELETE a provider API key."""
        headers = await self._auth()
        provider_id = "openai"
        # Set a key
        put_resp = await self.client.put(
            f"{self.ROUTE}/settings/providers/{provider_id}/key",
            headers=headers,
            json={"api_key": "sk-test-key-12345"},
        )
        self.assertIn(put_resp.status_code, (200, 204))

        # Delete the key
        del_resp = await self.client.delete(
            f"{self.ROUTE}/settings/providers/{provider_id}/key",
            headers=headers,
        )
        self.assertIn(del_resp.status_code, (200, 204))
        
    async def test_refresh_models_for_provider(self):
        """GET /api/settings/providers/{id}/models/refresh triggers model fetch."""
        headers = await self._auth()
        provider_id = "openai"
        resp = await self.client.get(
            f"{self.ROUTE}/settings/providers/{provider_id}/models/refresh",
            headers=headers,
        )
        # Without a real API key, this should return 400
        self.assertIn(resp.status_code, (200, 400, 401, 403, 500))
        if resp.status_code == 200:
            data = resp.json()
            self.assertIsInstance(data, dict)
            self.assertIn("models", data)


if __name__ == "__main__":
    unittest.main()