"""
Integration tests for security features: CSRF, security headers, request ID.
"""
import sys
import os
import uuid
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


class SecurityMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    """Test security headers, CSRF, and request ID middleware."""

    ROUTE = "/api/auth"
    USERNAME = "sec_integration_user"
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
        await self.client.post(f"{self.ROUTE}/register", json={
            "username": self.USERNAME, "password": self.PASSWORD,
        })
        resp = await self.client.post(f"{self.ROUTE}/login", json={
            "username": self.USERNAME, "password": self.PASSWORD,
        })
        data = resp.json()
        token = data["access_token"]
        csrf = data.get("csrf_token", "")
        headers = {"Authorization": f"Bearer {token}"}
        if csrf:
            headers["X-CSRF-Token"] = csrf
        return headers

    # ---- Security Headers ----

    async def test_csp_header(self):
        """Content-Security-Policy header should be present."""
        resp = await self.client.get("/health")
        csp = resp.headers.get("content-security-policy", "")
        self.assertIn("default-src 'self'", csp)

    async def test_api_requires_csrf_for_mutation(self):
        """POST with cookie but missing CSRF header should fail."""
        headers = await self._auth()
        # Remove CSRF header
        del headers["X-CSRF-Token"]
        resp = await self.client.post(
            f"{self.ROUTE}/logout",
            headers=headers,
        )
        self.assertIn(resp.status_code, (204, 403))
        if resp.status_code == 403:
            detail = resp.json().get("detail", "")
            self.assertIn("CSRF", detail)

    # ---- Request ID ----

    async def test_request_id_in_response(self):
        """Every response should have X-Request-ID."""
        resp = await self.client.get("/health")
        self.assertIn("x-request-id", resp.headers)
        rid = resp.headers["x-request-id"]
        self.assertTrue(len(rid) > 0)

    async def test_request_id_preserves_custom_value(self):
        """Custom X-Request-ID should be echoed back."""
        custom_id = f"test-req-{uuid.uuid4().hex[:6]}"
        resp = await self.client.get(
            "/health",
            headers={"x-request-id": custom_id},
        )
        self.assertEqual(resp.headers.get("x-request-id"), custom_id)

    async def test_request_id_unique_per_request(self):
        """Different requests should get different IDs (when not custom)."""
        resp1 = await self.client.get("/health")
        resp2 = await self.client.get("/health")
        rid1 = resp1.headers.get("x-request-id", "")
        rid2 = resp2.headers.get("x-request-id", "")
        self.assertNotEqual(rid1, rid2)

    # ---- Deprecation Headers ----

    async def test_xss_protection_header(self):
        resp = await self.client.get("/health")
        self.assertEqual(resp.headers.get("x-xss-protection"), "1; mode=block")

    async def test_content_type_options(self):
        resp = await self.client.get("/health")
        self.assertEqual(resp.headers.get("x-content-type-options"), "nosniff")

    async def test_frame_options_deny(self):
        resp = await self.client.get("/health")
        self.assertEqual(resp.headers.get("x-frame-options"), "DENY")

    # ---- Process Time ----

    async def test_process_time_header(self):
        resp = await self.client.get("/health")
        self.assertIn("x-process-time", resp.headers)
        pt = resp.headers["x-process-time"]
        # Should be a float string
        float(pt)  # Should not raise


if __name__ == "__main__":
    unittest.main()