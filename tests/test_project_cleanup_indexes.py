from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import build_project_cleanup_indexes as cleanup


class ProjectCleanupIndexesTests(unittest.TestCase):
    def test_review_classifier_marks_identity_balanced_as_final_evidence(self) -> None:
        path = Path("archive/pferi_v1/outputs/modeling-validation/pair-level-validation/identity-balanced-analysis")

        category, role = cleanup.classify_review_packet(path)

        self.assertEqual(category, "final_claim_evidence")
        self.assertIn("identity-balanced", role)

    def test_photo_gate_classifier_marks_final_seed(self) -> None:
        path = Path("archive/pferi_v1/outputs/photo-selection/photo-entry-gates/bobcat-final3000-seed")

        category, role = cleanup.classify_photo_gate(path)

        self.assertEqual(category, "final_seed")
        self.assertIn("final 3000", role)

    def test_build_writes_indexes_without_moving_source_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original_project_root = cleanup.PROJECT_ROOT
            original_output_dir = cleanup.OUTPUT_DIR
            original_review_roots = cleanup.REVIEW_ROOTS
            original_photo_gate_root = cleanup.PHOTO_GATE_ROOT
            original_review_index = cleanup.REVIEW_INDEX_CSV
            original_photo_index = cleanup.PHOTO_GATE_INDEX_CSV
            original_audit = cleanup.AUDIT_JSON
            original_report = cleanup.REPORT_MD
            try:
                cleanup.PROJECT_ROOT = root
                cleanup.OUTPUT_DIR = root / "archive/pferi_v1/outputs/project-governance/project-structure/cleanup_indexes"
                cleanup.REVIEW_INDEX_CSV = cleanup.OUTPUT_DIR / "review_packet_index.csv"
                cleanup.PHOTO_GATE_INDEX_CSV = cleanup.OUTPUT_DIR / "photo_selection_gate_index.csv"
                cleanup.AUDIT_JSON = cleanup.OUTPUT_DIR / "cleanup_indexes_audit.json"
                cleanup.REPORT_MD = cleanup.OUTPUT_DIR / "README.md"
                cleanup.REVIEW_ROOTS = [root / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation"]
                cleanup.PHOTO_GATE_ROOT = root / "archive/pferi_v1/outputs/photo-selection/photo-entry-gates"

                review_dir = cleanup.REVIEW_ROOTS[0] / "identity-balanced-analysis"
                review_dir.mkdir(parents=True)
                (review_dir / "labels.csv").write_text("pair_id,label\np1,review_ready\n", encoding="utf-8")
                photo_dir = cleanup.PHOTO_GATE_ROOT / "bobcat-final3000-seed"
                photo_dir.mkdir(parents=True)
                (photo_dir / "audit.json").write_text("{}\n", encoding="utf-8")

                audit = cleanup.build()

                self.assertEqual(audit["status"], "PASS")
                self.assertTrue(cleanup.REVIEW_INDEX_CSV.exists())
                self.assertTrue(cleanup.PHOTO_GATE_INDEX_CSV.exists())
                self.assertTrue(review_dir.exists())
                self.assertTrue(photo_dir.exists())
            finally:
                cleanup.PROJECT_ROOT = original_project_root
                cleanup.OUTPUT_DIR = original_output_dir
                cleanup.REVIEW_ROOTS = original_review_roots
                cleanup.PHOTO_GATE_ROOT = original_photo_gate_root
                cleanup.REVIEW_INDEX_CSV = original_review_index
                cleanup.PHOTO_GATE_INDEX_CSV = original_photo_index
                cleanup.AUDIT_JSON = original_audit
                cleanup.REPORT_MD = original_report


if __name__ == "__main__":
    unittest.main()
