from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import build_final_modeling_bootstrap as bootstrap


class FinalModelingBootstrapTests(unittest.TestCase):
    def test_missing_image_count_treats_empty_and_absent_paths_as_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "image.jpg"
            existing.write_bytes(b"fake")
            rows = [
                {"final_freeze_image_path": str(existing)},
                {"final_freeze_image_path": ""},
                {"final_freeze_image_path": str(Path(tmp) / "missing.jpg")},
            ]

            self.assertEqual(bootstrap.missing_image_count(rows), 2)

    def test_lynx_known_id_scope_requires_complete_identity_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_root = bootstrap.FINAL_FREEZE_ROOT
            try:
                bootstrap.FINAL_FREEZE_ROOT = Path(tmp)
                scope_dir = Path(tmp) / "lynx-wild"
                image_dir = scope_dir / "images"
                image_dir.mkdir(parents=True)
                image = image_dir / "a.jpg"
                image.write_bytes(b"fake")
                (scope_dir / "manifest.csv").write_text(
                    "final_freeze_image_path,source_identity_label\n"
                    f"{image},\n",
                    encoding="utf-8",
                )

                row = bootstrap.audit_scope(
                    "lynx-wild",
                    {
                        "min_rows": 1,
                        "max_rows": 1,
                        "identity_validation_allowed": True,
                        "identity_column": "source_identity_label",
                        "modeling_role": "known ID",
                        "permitted_endpoint": "validation",
                    },
                    required=True,
                )

                self.assertEqual(row["status"], "FAIL")
                self.assertIn("identity_labels_incomplete", row["notes"])
            finally:
                bootstrap.FINAL_FREEZE_ROOT = original_root

    def test_image_index_rows_encode_claim_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_root = bootstrap.PROJECT_ROOT
            try:
                bootstrap.PROJECT_ROOT = Path(tmp)
                scope_dir = Path(tmp) / "data/frozen/pferi_v2/bobcat-wild"
                image_dir = scope_dir / "images"
                image_dir.mkdir(parents=True)
                image = image_dir / "bobcat.jpg"
                image.write_bytes(b"fake")
                manifest = scope_dir / "manifest.csv"
                manifest.write_text(
                    "final_freeze_image_path,candidate_id,final_freeze_sha256,final_freeze_bytes\n"
                    "data/frozen/pferi_v2/bobcat-wild/images/bobcat.jpg,bobcat_001,abc,4\n",
                    encoding="utf-8",
                )

                rows = bootstrap.build_image_index_rows(
                    "bobcat-wild",
                    bootstrap.CORE_SCOPES["bobcat-wild"],
                    manifest,
                )

                self.assertEqual(rows[0]["image_id"], "pferi_bobcat_wild_00001")
                self.assertEqual(rows[0]["scope"], "bobcat-wild")
                self.assertFalse(rows[0]["identity_validation_allowed"])
                self.assertEqual(rows[0]["identity_label_status"], "not_applicable")
                self.assertTrue(rows[0]["local_image_exists"])
                self.assertIn("identity accuracy claims are blocked", rows[0]["claim_boundary"])
            finally:
                bootstrap.PROJECT_ROOT = original_root

    def test_claim_gates_block_bobcat_identity_metrics(self) -> None:
        gates = bootstrap.build_claim_gates()
        blocked_claims = {item["claim"] for item in gates["blocked_claims"]}

        self.assertIn("Bobcat identity accuracy", blocked_claims)
        self.assertIn("Bobcat false-match accuracy", blocked_claims)
        self.assertIn("Bobcat mAP/MRR/top-k identity retrieval performance", blocked_claims)


if __name__ == "__main__":
    unittest.main()
