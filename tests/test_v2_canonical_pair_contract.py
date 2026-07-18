from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import build_v2_canonical_pair_contract as contract


def canonical_row(endpoint_a: str = "img_a", endpoint_b: str = "img_b") -> dict[str, str]:
    left, right = sorted((endpoint_a, endpoint_b))
    return {
        "contract_version": contract.CONTRACT_VERSION,
        "canonical_pair_id": contract.canonical_pair_id(left, right),
        "endpoint_a_image_id": left,
        "endpoint_b_image_id": right,
        "source_dataset": "czechlynx_known_id",
        "pair_availability_status": "available",
        "pair_inclusion_status": "eligible",
        "exclusion_reason": "",
    }


def membership_row(
    canonical_pair: dict[str, str],
    query_image_id: str = "img_a",
    candidate_image_id: str = "img_b",
    direction: str = "a_to_b",
    descriptor_name: str = "megadescriptor_l_384",
) -> dict[str, str]:
    return {
        "contract_version": contract.CONTRACT_VERSION,
        "canonical_pair_id": canonical_pair["canonical_pair_id"],
        "descriptor_name": descriptor_name,
        "queue_name": "czechlynx_topk",
        "queue_snapshot_id": "queue_freeze_001",
        "query_image_id": query_image_id,
        "candidate_image_id": candidate_image_id,
        "candidate_rank": "4",
        "descriptor_similarity": "0.83",
        "membership_direction": direction,
    }


class V2CanonicalPairContractTests(unittest.TestCase):
    def test_canonical_pair_id_is_order_invariant_and_nonself(self) -> None:
        self.assertEqual(contract.canonical_pair_id("img_a", "img_b"), contract.canonical_pair_id("img_b", "img_a"))
        with self.assertRaises(ValueError):
            contract.canonical_pair_id("img_a", "img_a")

    def test_valid_contract_retains_two_directions_and_two_descriptors(self) -> None:
        pair = canonical_row()
        memberships = [
            membership_row(pair),
            membership_row(pair, "img_b", "img_a", "b_to_a"),
            membership_row(pair, descriptor_name="dinov2_vitl14"),
        ]

        audit = contract.validate_contract([pair], memberships, [])

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["canonical_pair_count"], 1)
        self.assertEqual(audit["candidate_membership_count"], 3)
        self.assertEqual(audit["multi_membership_pair_count"], 1)

    def test_rejects_noncanonical_endpoints_and_self_pair(self) -> None:
        pair = canonical_row("img_b", "img_a")
        pair["endpoint_a_image_id"] = "img_b"
        pair["endpoint_b_image_id"] = "img_a"

        audit = contract.validate_contract([pair], [], [])

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("canonical_endpoints_not_lexicographically_sorted", audit["error_codes"])

    def test_rejects_outcome_and_route_fields_from_pair_manifests(self) -> None:
        pair = canonical_row()
        pair["review_ready_label"] = "yes"

        audit = contract.validate_contract([pair], [], [])

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_column_in_canonical_pairs:review_ready_label", audit["error_codes"])

    def test_rejects_membership_that_does_not_match_canonical_pair(self) -> None:
        pair = canonical_row()
        membership = membership_row(pair, query_image_id="img_a", candidate_image_id="img_c")

        audit = contract.validate_contract([pair], [membership], [])

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("membership_endpoints_do_not_match_canonical_pair", audit["error_codes"])

    def test_identity_truth_is_restricted_and_separate(self) -> None:
        pair = canonical_row()
        identity_rows = [
            {
                "canonical_pair_id": pair["canonical_pair_id"],
                "same_identity_known_id": "yes",
                "identity_truth_source": "czechlynx_verified_id",
                "access_class": "restricted",
            }
        ]

        audit = contract.validate_contract([pair], [], identity_rows)

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["identity_audit_row_count"], 1)

    def test_writes_machine_readable_schema_and_cli_audit(self) -> None:
        pair = canonical_row()
        membership = membership_row(pair)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical_csv = root / "canonical_pairs.csv"
            membership_csv = root / "candidate_memberships.csv"
            schema_json = root / "schema.json"
            audit_json = root / "audit.json"
            contract.write_csv(canonical_csv, [pair], contract.CANONICAL_PAIR_COLUMNS)
            contract.write_csv(membership_csv, [membership], contract.CANDIDATE_MEMBERSHIP_COLUMNS)

            exit_code = contract.main(
                [
                    "--canonical-pairs",
                    str(canonical_csv),
                    "--candidate-memberships",
                    str(membership_csv),
                    "--audit-json",
                    str(audit_json),
                    "--write-schema",
                    str(schema_json),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(schema_json.read_text(encoding="utf-8"))["contract_version"], contract.CONTRACT_VERSION)
            self.assertEqual(json.loads(audit_json.read_text(encoding="utf-8"))["status"], "PASS")

    def test_checked_in_schema_matches_contract_builder(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "pferi_v2" / "canonical_pair_contract_v1.json"

        self.assertEqual(json.loads(schema_path.read_text(encoding="utf-8")), contract.build_contract_schema())


if __name__ == "__main__":
    unittest.main()
