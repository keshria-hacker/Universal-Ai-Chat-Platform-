import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("start_launcher", ROOT / "start.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class StartupLauncherTests(unittest.TestCase):
    def test_build_commands_include_backend_and_frontend_servers(self):
        backend_cmd, frontend_cmd = MODULE.build_commands("python")

        self.assertEqual(backend_cmd[0], "python")
        self.assertIn("uvicorn", backend_cmd)
        self.assertIn("main:app", backend_cmd)

        self.assertEqual(frontend_cmd[0], "python")
        self.assertIn("http.server", frontend_cmd)
        self.assertIn("5500", frontend_cmd)

    def test_skips_dependency_install_when_requirements_are_unchanged(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            requirements = temp_path / "requirements.txt"
            requirements.write_text("fastapi==0.115.6\n", encoding="utf-8")
            marker = temp_path / ".requirements.sha256"
            marker.write_text(MODULE.hashlib.sha256(requirements.read_bytes()).hexdigest(), encoding="utf-8")

            with patch.object(MODULE, "REQ_FILE", requirements), patch.object(MODULE, "REQUIREMENTS_MARKER", marker), patch("subprocess.run") as run:
                MODULE.install_requirements("python")

            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
