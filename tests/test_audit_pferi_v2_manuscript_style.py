import tempfile
import unittest
from pathlib import Path

from scripts.audit_pferi_v2_manuscript_style import MANUSCRIPT, audit


class ManuscriptStyleAuditTests(unittest.TestCase):
    def test_rewrite_passes_stop_slop_audit(self):
        result = audit(output=None)
        self.assertEqual(result["status"], "PASS", result["failures"])
        self.assertGreaterEqual(result["total_score"], 35)

    def test_rejects_formulaic_ai_prose(self):
        text = MANUSCRIPT.read_text(encoding="utf-8")
        text = text.replace(
            "\n## References\n",
            (
                "\nHere's the thing: this matters because it is actually important. "
                "This decisive result provides a rigorous foundation and a clear route.\n\n"
                "## References\n"
            ),
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manuscript.md"
            path.write_text(text, encoding="utf-8")
            result = audit(path, output=None)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("throat_clearing", result["failures"])
        self.assertIn("emphasis_crutch", result["failures"])
        self.assertIn("filler_adverb", result["failures"])
        self.assertIn("promotional_closure", result["failures"])


if __name__ == "__main__":
    unittest.main()
