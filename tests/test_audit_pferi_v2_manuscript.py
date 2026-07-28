import tempfile
import unittest
from pathlib import Path

from scripts.audit_pferi_v2_manuscript import MANUSCRIPT, audit


class ManuscriptAuditTests(unittest.TestCase):
    def test_current_manuscript_passes(self):
        result = audit(output=None)
        self.assertEqual(result["status"], "PASS", result["failures"])
        self.assertGreaterEqual(result["reference_doi_count"], 12)
        self.assertEqual(result["remaining_author_metadata_placeholders"], [])
        self.assertFalse(result["models_refit"])
        self.assertFalse(result["task15l_parameters_recomputed"])

    def test_rejects_internal_task_number_and_overclaim(self):
        text = MANUSCRIPT.read_text(encoding="utf-8")
        text += "\nTask17 showed that P5 was confirmed superior.\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manuscript.md"
            path.write_text(text, encoding="utf-8")
            result = audit(path, output=None)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("prohibited_claim:internal_task17", result["failures"])
        self.assertIn("prohibited_claim:p5_confirmed_superior", result["failures"])


if __name__ == "__main__":
    unittest.main()
