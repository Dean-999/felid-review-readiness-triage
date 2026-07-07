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


if __name__ == "__main__":
    unittest.main()
