import sys
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from document import extract_text, truncate_preview


class DocumentExtractionTests(unittest.TestCase):
    def test_extract_plain_text_txt(self):
        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, world!")
            f.flush()
            result = extract_text(Path(f.name), "txt")
        self.assertEqual(result, "Hello, world!")

    def test_extract_plain_text_py(self):
        with NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello():\n    print('hi')")
            f.flush()
            result = extract_text(Path(f.name), "py")
        self.assertIn("def hello()", result)

    def test_extract_plain_text_md(self):
        with NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Title\n\nBody text")
            f.flush()
            result = extract_text(Path(f.name), "md")
        self.assertIn("Title", result)
        self.assertIn("Body text", result)

    def test_extract_plain_text_json(self):
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"key": "value"}')
            f.flush()
            result = extract_text(Path(f.name), "json")
        self.assertIn("key", result)

    def test_extract_unknown_extension_returns_empty(self):
        with NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
            f.write("random data")
            f.flush()
            result = extract_text(Path(f.name), "xyz")
        self.assertEqual(result, "")

    def test_extract_handles_missing_file_gracefully(self):
        result = extract_text(Path("/nonexistent/file.txt"), "txt")
        self.assertIn("Could not extract text", result)

    def test_extract_normalizes_extension_case(self):
        with NamedTemporaryFile(mode="w", suffix=".TXT", delete=False) as f:
            f.write("Case insensitive extension")
            f.flush()
            result = extract_text(Path(f.name), "TXT")
        self.assertEqual(result, "Case insensitive extension")


class TruncatePreviewTests(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(truncate_preview("Hello"), "Hello")

    def test_long_text_truncated(self):
        text = "a" * 500
        result = truncate_preview(text, length=100)
        self.assertEqual(len(result), 101)  # 100 chars + …
        self.assertTrue(result.endswith("…"))

    def test_exact_length_not_truncated(self):
        text = "a" * 300
        result = truncate_preview(text, length=300)
        self.assertEqual(result, text)

    def test_empty_string_handled(self):
        self.assertEqual(truncate_preview(""), "")

    def test_whitespace_stripped(self):
        result = truncate_preview("  hello  ", length=300)
        self.assertEqual(result, "hello")


if __name__ == "__main__":
    unittest.main()
