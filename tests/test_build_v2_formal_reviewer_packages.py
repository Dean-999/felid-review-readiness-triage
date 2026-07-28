from __future__ import annotations

import csv
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, PngImagePlugin

from scripts import build_v2_formal_reviewer_packages as builder


class FormalReviewerPackageTests(unittest.TestCase):
    def write_csv(self, path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def make_inputs(self, root: Path) -> dict[str, Path]:
        image_dir = root / "data/frozen/pferi_v2/lynx-wild/images"
        image_dir.mkdir(parents=True)
        execution_rows = []
        for index in range(4):
            path = image_dir / f"source_{index}.jpg"
            Image.new("RGB", (41 + index, 29 + index), (index * 30, 40, 80)).save(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            execution_rows.append(
                {
                    "image_id": f"image_{index}",
                    "image_path_relative": f"outputs/final_freeze/lynx-wild/images/source_{index}.jpg",
                    "content_sha256": digest,
                }
            )
        codes = ["rv_a", "rv_b", "rv_c", "rv_d"]
        aliases = ["reviewer_A", "reviewer_B", "reviewer_C", "reviewer_D"]
        roster_rows = [
            {
                "reviewer_code": code,
                "restricted_person_name": alias,
                "eligible_roles": "first_pass_reviewer;adjudicator",
                "training_confirmed": "yes",
                "pair_or_role_conflicts": "",
                "conflict_attestation": "pending",
                "signed_at_utc": "",
            }
            for code, alias in zip(codes, aliases)
        ]
        assignment_rows = []
        pair_specs = [
            ("pair_1", "image_0", "image_1", "development", ("rv_a", "rv_b")),
            ("pair_2", "image_2", "image_3", "deployment_confirmation", ("rv_c", "rv_d")),
        ]
        for pair_id, left, right, stage, reviewers in pair_specs:
            for reviewer in reviewers:
                peer = reviewers[1] if reviewer == reviewers[0] else reviewers[0]
                eligible = ";".join(code for code in codes if code not in reviewers)
                assignment_rows.append(
                    {
                        "assignment_contract_version": "pferi_v2_formal_review_instrument_contract_v1",
                        "review_packet_id": f"task_{pair_id}_{reviewer}",
                        "canonical_pair_id": pair_id,
                        "formal_sampling_stage": stage,
                        "reviewer_assignment_id": f"assignment_{pair_id}_{reviewer}",
                        "reviewer_code": reviewer,
                        "peer_reviewer_code": peer,
                        "eligible_adjudicator_codes": eligible,
                        "left_image_id": left,
                        "right_image_id": right,
                        "left_asset_token": f"asset_{hashlib.sha256((reviewer + left).encode()).hexdigest()[:20]}",
                        "right_asset_token": f"asset_{hashlib.sha256((reviewer + right).encode()).hexdigest()[:20]}",
                        "packet_batch_id": "batch",
                        "assignment_status": "provisional_not_released",
                    }
                )
        assignment = root / "assignment.csv"
        roster = root / "roster.csv"
        execution = root / "execution.csv"
        self.write_csv(assignment, builder.ASSIGNMENT_COLUMNS, assignment_rows)
        self.write_csv(roster, builder.ROSTER_COLUMNS, roster_rows)
        self.write_csv(execution, builder.EXECUTION_COLUMNS, execution_rows)
        return {"assignment": assignment, "roster": roster, "execution": execution}

    def test_builds_four_isolated_candidate_packages_without_restricted_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self.make_inputs(root)
            output = root / "delivery"
            audit = builder.build_packages(
                assignment_path=inputs["assignment"],
                roster_path=inputs["roster"],
                execution_manifest_path=inputs["execution"],
                project_root=root,
                output_dir=output,
            )
            self.assertEqual(audit["status"], "PASS_CANDIDATE_NOT_RELEASED")
            self.assertFalse(audit["packet_release_authorized"])
            self.assertEqual(audit["reviewer_package_count"], 4)
            for alias in ["reviewer_A", "reviewer_B", "reviewer_C", "reviewer_D"]:
                zip_path = output / "candidate_reviewer_packages" / f"PAIR_REVIEW_{alias}.zip"
                self.assertTrue(zip_path.is_file())
                with zipfile.ZipFile(zip_path) as archive:
                    names = archive.namelist()
                    self.assertIn("reviewer_view/reviewer_packet.csv", names)
                    self.assertFalse(any("restricted" in name.lower() for name in names))
                    packet_text = archive.read("reviewer_view/reviewer_packet.csv").decode()
                    self.assertNotIn("canonical_pair_id", packet_text)
                    self.assertNotIn("formal_sampling_stage", packet_text)

    def test_rendering_preserves_oriented_pixel_dimensions_and_strips_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self.make_inputs(root)
            output = root / "delivery"
            builder.build_packages(
                assignment_path=inputs["assignment"],
                roster_path=inputs["roster"],
                execution_manifest_path=inputs["execution"],
                project_root=root,
                output_dir=output,
            )
            assets = list((output / "candidate_reviewer_packages_unzipped/reviewer_A/reviewer_view/assets").glob("*.png"))
            self.assertEqual(len(assets), 2)
            dimensions = []
            for path in assets:
                with Image.open(path) as rendered:
                    dimensions.append(rendered.size)
            dimensions.sort()
            self.assertEqual(dimensions, [(41, 29), (42, 30)])
            for path in assets:
                with Image.open(path) as rendered:
                    self.assertEqual(rendered.info, {})

    def test_rendering_strips_png_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            target = root / "rendered.png"
            metadata = PngImagePlugin.PngInfo()
            metadata.add_text("source_note", "restricted")
            Image.new("RGBA", (17, 11), (10, 20, 30, 255)).save(
                source,
                format="PNG",
                pnginfo=metadata,
            )
            with Image.open(source) as original:
                self.assertEqual(original.info["source_note"], "restricted")
            builder.render_asset(source, target)
            with Image.open(target) as rendered:
                self.assertEqual(rendered.mode, "RGB")
                self.assertEqual(rendered.size, (17, 11))
                self.assertEqual(rendered.info, {})

    def test_rejects_hash_mismatch_before_writing_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self.make_inputs(root)
            with inputs["execution"].open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["content_sha256"] = "0" * 64
            self.write_csv(inputs["execution"], builder.EXECUTION_COLUMNS, rows)
            with self.assertRaisesRegex(ValueError, "hash verification"):
                builder.build_packages(
                    assignment_path=inputs["assignment"],
                    roster_path=inputs["roster"],
                    execution_manifest_path=inputs["execution"],
                    project_root=root,
                    output_dir=root / "delivery",
                )


if __name__ == "__main__":
    unittest.main()
