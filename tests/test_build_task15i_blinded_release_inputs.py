from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task15i_release_inputs", ROOT / "scripts/build_task15i_blinded_release_inputs.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Task15IBlindedReleaseInputsTests(unittest.TestCase):
    def test_select_execution_rows_is_complete_and_deduplicated(self) -> None:
        assignment = [
            {"left_image_id": "a", "right_image_id": "b"},
            {"left_image_id": "b", "right_image_id": "c"},
        ]
        execution = [
            {"image_id": "a", "image_path_relative": "a.jpg", "content_sha256": "a" * 64},
            {"image_id": "b", "image_path_relative": "b.jpg", "content_sha256": "b" * 64},
            {"image_id": "c", "image_path_relative": "c.jpg", "content_sha256": "c" * 64},
        ]
        selected = MODULE.select_execution_rows(assignment, execution)
        self.assertEqual([row["image_id"] for row in selected], ["a", "b", "c"])

    def test_select_execution_rows_rejects_missing_image(self) -> None:
        with self.assertRaisesRegex(ValueError, "omits"):
            MODULE.select_execution_rows([{"left_image_id": "a", "right_image_id": "missing"}], [{"image_id": "a", "image_path_relative": "a.jpg", "content_sha256": "a" * 64}])


if __name__ == "__main__":
    unittest.main()
