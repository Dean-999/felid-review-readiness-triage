from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts import build_v2_full_image_quality_execution_manifest as builder
from scripts import run_v2_full_image_quality_measurements as runner


class FullImageQualityMeasurementTests(unittest.TestCase):
    def make_image(self, root: Path, name: str, color: tuple[int, int, int]) -> tuple[Path, str]:
        path = root / name
        Image.new("RGB", (8, 6), color).save(path, format="PNG")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return path, digest

    def test_builder_emits_restricted_verified_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, digest = self.make_image(root, "image.png", (10, 20, 30))
            source = [{
                "species": "czechlynx",
                "final_freeze_image_path": path.name,
                "final_freeze_image_exists": "yes",
                "final_freeze_sha256": digest,
                "source_identity_label": "must_not_leak",
            }]
            rows, audit = builder.build_rows(source, project_root=root, expected_count=1)
            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(list(rows[0]), builder.OUTPUT_COLUMNS)
            self.assertEqual(rows[0]["image_id"], f"pferi_v2_image_{digest}")
            self.assertNotIn("identity", " ".join(rows[0]).lower())

    def test_builder_rejects_content_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = self.make_image(root, "image.png", (10, 20, 30))
            source = [{
                "species": "czechlynx",
                "final_freeze_image_path": path.name,
                "final_freeze_image_exists": "yes",
                "final_freeze_sha256": "0" * 64,
            }]
            with self.assertRaises(ValueError):
                builder.build_rows(source, project_root=root, expected_count=1)

    def test_runner_measures_only_retained_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, digest = self.make_image(root, "image.png", (10, 20, 30))
            source = {"image_id": f"pferi_v2_image_{digest}", "image_path_relative": path.name, "content_sha256": digest}
            row = runner.measure_one(source, project_root=root)
            self.assertEqual(row["image_integrity_status"], "pass")
            self.assertEqual(row["native_pixel_count"], 48)
            self.assertEqual(row["native_pixel_count_value_status"], "not_missing")
            self.assertNotIn("animal_coverage_fraction", row)


if __name__ == "__main__":
    unittest.main()
