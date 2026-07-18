from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from scripts import audit_v2_reviewer_interface_dry_run as auditor
from scripts import build_v2_reviewer_interface_dry_run as builder


class V2ReviewerInterfaceDryRunTests(unittest.TestCase):

    def test_builder_cli_is_directly_runnable(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "build_v2_reviewer_interface_dry_run.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def write_csv(self, path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def make_inputs(self, root: Path, pair_count: int = 12) -> dict[str, Path]:
        images = root / "images"
        images.mkdir()
        pilot_rows: list[dict[str, str]] = []
        canonical_rows: list[dict[str, str]] = []
        execution_rows: list[dict[str, str]] = []
        for index in range(pair_count * 2):
            filename = f"source_image_{index:03d}.jpg"
            image_path = images / filename
            Image.new("RGB", (32, 24), color=(index % 255, 20, 40)).save(image_path)
            execution_rows.append(
                {
                    "image_id": f"image_{index:03d}",
                    "image_path_relative": str(image_path.relative_to(root)),
                    "content_sha256": builder.sha256_file(image_path),
                }
            )
        for index in range(pair_count):
            pair_id = f"pair_{index:03d}"
            pilot_rows.append(
                {
                    "contract_version": "pferi_v2_measurement_feasibility_pilot_contract_v1",
                    "pilot_pair_id": f"pilot_{index:03d}",
                    "canonical_pair_id": pair_id,
                    "selection_seed_id": "seed",
                    "selection_stratum": "test",
                    "pair_availability_status": "available",
                    "pilot_inclusion_status": "included",
                    "exclusion_reason": "",
                }
            )
            canonical_rows.append(
                {
                    "contract_version": "pferi_v2_canonical_pair_contract_v1",
                    "canonical_pair_id": pair_id,
                    "endpoint_a_image_id": f"image_{index * 2:03d}",
                    "endpoint_b_image_id": f"image_{index * 2 + 1:03d}",
                    "source_dataset": "czechlynx",
                    "pair_availability_status": "available",
                    "pair_inclusion_status": "included",
                    "exclusion_reason": "",
                }
            )
        pilot = root / "pilot.csv"
        canonical = root / "canonical.csv"
        execution = root / "execution.csv"
        self.write_csv(pilot, builder.PILOT_COLUMNS, pilot_rows)
        self.write_csv(canonical, builder.CANONICAL_COLUMNS, canonical_rows)
        self.write_csv(execution, builder.EXECUTION_COLUMNS, execution_rows)
        pilot_audit = root / "pilot_audit.json"
        pilot_audit.write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "confirmation_overlap_rule": "pilot_pairs_are_ineligible_for_v2_confirmation_samples",
                }
            ),
            encoding="utf-8",
        )
        return {"pilot": pilot, "canonical": canonical, "execution": execution, "pilot_audit": pilot_audit}

    def build(self, root: Path) -> Path:
        inputs = self.make_inputs(root)
        output = root / "dry_run"
        audit = builder.build_dry_run(
            pilot_manifest=inputs["pilot"],
            pilot_audit=inputs["pilot_audit"],
            canonical_pairs=inputs["canonical"],
            execution_manifest=inputs["execution"],
            project_root=root,
            output_dir=output,
            contract_path=builder.DEFAULT_CONTRACT_PATH,
        )
        self.assertEqual(audit["status"], "PASS")
        return output

    def test_build_makes_opaque_public_packet_and_isolates_restricted_linkage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = self.build(root)

            with (output / "reviewer_view" / "reviewer_packet.csv").open(newline="", encoding="utf-8") as handle:
                packet = list(csv.DictReader(handle))
                self.assertEqual(handle.seek(0) or next(csv.reader(handle)), builder.REVIEWER_PACKET_COLUMNS)
            self.assertEqual(len(packet), 12)
            public_text = (output / "reviewer_view" / "reviewer_packet.csv").read_text(encoding="utf-8")
            self.assertNotIn("pair_000", public_text)
            self.assertNotIn("image_000", public_text)
            for asset in (output / "reviewer_view" / "assets").iterdir():
                self.assertRegex(asset.name, r"^asset_[a-f0-9]{20}\.png$")
            self.assertFalse((output / "reviewer_view" / "restricted_linkage.csv").exists())
            machine_audit = auditor.audit_dry_run(output, builder.DEFAULT_CONTRACT_PATH)
            self.assertEqual(machine_audit["status"], "PASS")
            delivery = output / "independent_browser_audit" / "PF_ERI_V2_INTERFACE_AUDIT_DELIVERY.zip"
            self.assertTrue(delivery.is_file())
            with zipfile.ZipFile(delivery) as archive:
                members = archive.namelist()
            self.assertIn("reviewer_view/app.py", members)
            self.assertIn("human_browser_leakage_checklist.csv", members)
            self.assertIn("INDEPENDENT_AUDITOR_GUIDE_zh.md", members)
            self.assertFalse(any("restricted" in member.lower() for member in members))

    def test_static_audit_rejects_forbidden_public_packet_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = self.build(Path(temporary))
            packet_path = output / "reviewer_view" / "reviewer_packet.csv"
            with packet_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            fields = list(rows[0]) + ["candidate_rank"]
            for row in rows:
                row["candidate_rank"] = "1"
            self.write_csv(packet_path, fields, rows)

            machine_audit = auditor.audit_dry_run(output, builder.DEFAULT_CONTRACT_PATH)
            self.assertEqual(machine_audit["status"], "FAIL")
            self.assertIn("reviewer_packet_header_mismatch", machine_audit["error_codes"])

    def test_builder_rejects_pilot_without_confirmation_exclusion_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self.make_inputs(root)
            inputs["pilot_audit"].write_text(json.dumps({"status": "PASS"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "confirmation exclusion"):
                builder.build_dry_run(
                    pilot_manifest=inputs["pilot"],
                    pilot_audit=inputs["pilot_audit"],
                    canonical_pairs=inputs["canonical"],
                    execution_manifest=inputs["execution"],
                    project_root=root,
                    output_dir=root / "dry_run",
                    contract_path=builder.DEFAULT_CONTRACT_PATH,
                )


if __name__ == "__main__":
    unittest.main()
