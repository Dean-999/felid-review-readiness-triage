from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task15i_runner", ROOT / "scripts/task15i_descriptor_modelscope_runner.py")
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class Task15IDescriptorRunnerTests(unittest.TestCase):
    def test_score_rows_are_directed_ranked_and_exclude_self(self) -> None:
        vectors = np.eye(25, dtype=np.float32)
        rows = RUNNER.score_rows([f"id{index}" for index in range(25)], vectors, "test", 20)
        self.assertEqual(len(rows), 500)
        for index in range(25):
            group = rows[index * 20:(index + 1) * 20]
            self.assertEqual([row["candidate_rank"] for row in group], list(range(1, 21)))
            self.assertTrue(all(row["query_image_id"] != row["candidate_image_id"] for row in group))

    def test_manifest_rejects_extra_column_without_touching_images(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "manifest.csv"
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=RUNNER.MANIFEST_COLUMNS + ["outcome"])
                writer.writeheader()
                writer.writerow({"image_id": "x", "image_path_relative": "x.jpg", "content_sha256": "0" * 64, "outcome": "1"})
            with self.assertRaisesRegex(ValueError, "manifest columns"):
                RUNNER.load_and_verify_images(manifest, root, {"expected_image_count": 1})

    def test_normalized_rejects_zero_vector(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "zero"):
            RUNNER.normalized(np.zeros((1, 3), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
