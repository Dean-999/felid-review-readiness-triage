from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import build_v2_canonical_pair_contract as pairs
from scripts import build_v2_measurement_feasibility_pilot_manifest as pilot


def canonical_row(left: str, right: str) -> dict[str, str]:
    left, right = sorted((left, right))
    return {
        "contract_version": pairs.CONTRACT_VERSION,
        "canonical_pair_id": pairs.canonical_pair_id(left, right),
        "endpoint_a_image_id": left,
        "endpoint_b_image_id": right,
        "source_dataset": "czechlynx_v2_reservoir",
        "pair_availability_status": "available",
        "pair_inclusion_status": "eligible",
        "exclusion_reason": "",
    }


def membership_row(pair: dict[str, str], rank: str, descriptor: str = "descriptor_a") -> dict[str, str]:
    return {
        "contract_version": pairs.CONTRACT_VERSION,
        "canonical_pair_id": pair["canonical_pair_id"],
        "descriptor_name": descriptor,
        "queue_name": "v2_frozen_queue",
        "queue_snapshot_id": "v2_queue_001",
        "query_image_id": pair["endpoint_a_image_id"],
        "candidate_image_id": pair["endpoint_b_image_id"],
        "candidate_rank": rank,
        "descriptor_similarity": "0.8",
        "membership_direction": "a_to_b",
    }


def image_context(image_id: str, illumination: str = "day") -> dict[str, str]:
    return {
        "image_id": image_id,
        "image_decode_status": "ok",
        "illumination_metadata": illumination,
        "source_camera_context": "camera_context_available",
    }


class BuildV2MeasurementFeasibilityPilotManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pairs = [canonical_row("img_a", "img_b"), canonical_row("img_c", "img_d"), canonical_row("img_e", "img_f"), canonical_row("img_g", "img_h")]
        self.memberships = [membership_row(pair, str(index + 1), "descriptor_a" if index % 2 == 0 else "descriptor_b") for index, pair in enumerate(self.pairs)]
        self.contexts = [image_context(image_id, "day" if index % 2 == 0 else "infrared") for index, image_id in enumerate("img_a img_b img_c img_d img_e img_f img_g img_h".split())]

    def test_builds_deterministic_restricted_manifest(self) -> None:
        rows, audit = pilot.build_pilot_manifest(self.pairs, self.memberships, self.contexts, target_count=4, seed="pilot-seed")

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({row["canonical_pair_id"] for row in rows}), 4)
        self.assertTrue(all(row["selection_seed_id"] == "pilot-seed" for row in rows))
        self.assertTrue(all("identity" not in " ".join(row).lower() for row in rows))

    def test_rejects_legacy_or_identity_bearing_source_headers(self) -> None:
        contaminated = [dict(self.pairs[0], same_identity_known_id="yes")]

        with self.assertRaises(ValueError):
            pilot.build_pilot_manifest(contaminated, self.memberships[:1], self.contexts[:2], target_count=1, seed="pilot-seed")

    def test_rejects_insufficient_eligible_pairs(self) -> None:
        with self.assertRaises(ValueError):
            pilot.build_pilot_manifest(self.pairs, self.memberships, self.contexts, target_count=5, seed="pilot-seed")

    def test_cli_writes_manifest_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical_path = root / "canonical.csv"
            membership_path = root / "membership.csv"
            context_path = root / "context.csv"
            output_path = root / "pilot.csv"
            audit_path = root / "audit.json"
            pilot.write_csv(canonical_path, self.pairs, pairs.CANONICAL_PAIR_COLUMNS)
            pilot.write_csv(membership_path, self.memberships, pairs.CANDIDATE_MEMBERSHIP_COLUMNS)
            pilot.write_csv(context_path, self.contexts, pilot.IMAGE_CONTEXT_COLUMNS)

            exit_code = pilot.main(["--canonical-pairs", str(canonical_path), "--candidate-memberships", str(membership_path), "--image-context", str(context_path), "--target-count", "4", "--seed", "pilot-seed", "--output-csv", str(output_path), "--audit-json", str(audit_path)])

            self.assertEqual(exit_code, 0)
            with output_path.open(newline="", encoding="utf-8") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 4)
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
