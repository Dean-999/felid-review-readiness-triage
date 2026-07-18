from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts import structural_oracle_annotation_core as core


class StructuralOracleCoreTests(unittest.TestCase):
    def make_package(self, root: Path) -> Path:
        package = root / "package"; images = package / "images"; images.mkdir(parents=True)
        (images / "asset_a.jpg").write_bytes(b"a")
        (images / "asset_b.jpg").write_bytes(b"b")
        with (package / "annotation_packets.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=core.PACKET_COLUMNS); writer.writeheader()
            writer.writerow({"annotation_packet_id":"packet_a","left_asset_token":"asset_a","right_asset_token":"asset_b","instrument_version":"v1","annotation_form_schema_version":"v1"})
        (package / "ANNOTATOR_INSTRUCTIONS.txt").write_text("instructions")
        return package

    def test_load_packet_and_confined_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = self.make_package(Path(tmp))
            packets = core.load_packet(package)
            self.assertEqual(len(packets), 1)
            self.assertEqual(core.resolve_asset(package, "asset_a").name, "asset_a.jpg")
            with self.assertRaises(ValueError): core.resolve_asset(package, "../secret")

    def test_validate_response_rejects_invalid_grid(self) -> None:
        values = core.empty_response("packet_a")
        values.update(core.CONTINUOUS_FIELDS | {"viewpoint_compatibility_class": "partial", "technical_problem_flag": "no"})
        core.validate_response(values)
        values["left_occlusion_fraction"] = "0.07"
        with self.assertRaises(ValueError): core.validate_response(values)

    def test_output_isolated_by_fixed_annotator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(core.response_path(root, "annotator_a"), root / "annotator_a" / "structural_oracle_responses.csv")
            with self.assertRaises(ValueError): core.response_path(root, "annotator_c")


if __name__ == "__main__":
    unittest.main()
