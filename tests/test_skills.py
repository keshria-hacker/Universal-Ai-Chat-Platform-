import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from skills.router import SkillRouter
import llm


class SkillModelSelectionTests(unittest.TestCase):
    def test_skills_use_a_real_available_model_not_hardcoded(self):
        """Skill execution must pick a real discovered model (e.g. a local
        Ollama model) instead of the old hardcoded phantom 'claude-sonnet-5',
        which had no key and always errored."""
        captured = {}

        async def fake_stream(model_id, messages, db, temperature, max_tokens):
            captured["model_id"] = model_id
            yield "ok"

        class FakeResult:
            def __init__(self, rows):
                self._rows = rows
            def scalars(self):
                class R:
                    def __init__(self, rows):
                        self._rows = rows
                    def __iter__(self):
                        return iter(self._rows)
                return R(self._rows)

        class FakeDB:
            async def execute(self, *a, **k):
                return FakeResult([])

        with patch.object(llm, "stream_completion", fake_stream), \
                patch.object(llm, "default_model_id", AsyncMock(return_value="ollama:llama2-uncensored:7b")):
            router = SkillRouter()
            # web-search exists in the registry and requires a `query` param.
            asyncio.run(
                router.execute("web-search", {"query": "latest AI news"})
            )

        self.assertEqual(captured.get("model_id"), "ollama:llama2-uncensored:7b")
        self.assertNotEqual(captured.get("model_id"), "claude-sonnet-5")


if __name__ == "__main__":
    unittest.main()
