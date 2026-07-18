from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import validate_v2_partition_constraints as contract


CANONICAL_FIELDS = list(contract.CANONICAL_PAIR_COLUMNS)
IMAGE_FIELDS = list(contract.IMAGE_PARTITION_COLUMNS)
PAIR_FIELDS = list(contract.PAIR_PARTITION_COLUMNS)
IDENTITY_FIELDS = list(contract.IDENTITY_MAP_COLUMNS)
SENSITIVITY_FIELDS = list(contract.IDENTITY_SENSITIVITY_COLUMNS)


def canonical(pair_id: str, endpoint_a: str, endpoint_b: str) -> dict[str, str]:
    return {
        "contract_version": "pferi_v2_canonical_pair_contract_v1",
        "canonical_pair_id": pair_id,
        "endpoint_a_image_id": endpoint_a,
        "endpoint_b_image_id": endpoint_b,
        "source_dataset": "synthetic_outcome_free_test",
        "pair_availability_status": "available",
        "pair_inclusion_status": "eligible",
        "exclusion_reason": "",
    }


def image(image_id: str, role: str) -> dict[str, str]:
    active = role in contract.ACTIVE_ROLES
    return {
        "partition_contract_version": contract.CONTRACT_VERSION,
        "image_id": image_id,
        "partition_role": role,
        "allocation_status": "assigned" if active else "unassigned",
        "exclusion_reason": "" if active else "not_selected_under_frozen_allocation",
    }


def pair(source: dict[str, str], role: str, reason: str = "") -> dict[str, str]:
    return {
        "partition_contract_version": contract.CONTRACT_VERSION,
        "canonical_pair_id": source["canonical_pair_id"],
        "endpoint_a_image_id": source["endpoint_a_image_id"],
        "endpoint_b_image_id": source["endpoint_b_image_id"],
        "partition_role": role,
        "allocation_status": "assigned" if role in contract.ACTIVE_ROLES else "excluded",
        "exclusion_reason": reason,
    }


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class PartitionConstraintContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.p1 = canonical("p1", "a", "b")
        self.p2 = canonical("p2", "b", "c")
        self.p3 = canonical("p3", "c", "d")
        self.p4 = canonical("p4", "e", "f")
        self.canonical_rows = [self.p1, self.p2, self.p3, self.p4]
        self.image_rows = [
            image("a", "development"),
            image("b", "development"),
            image("c", "calibration"),
            image("d", "calibration"),
            image("e", "confirmation"),
            image("f", "confirmation"),
        ]
        self.pair_rows = [
            pair(self.p1, "development"),
            pair(self.p2, "excluded", "cross_partition_endpoints"),
            pair(self.p3, "calibration"),
            pair(self.p4, "confirmation"),
        ]

    def run_validation(
        self,
        root: Path,
        *,
        canonical_rows: list[dict[str, str]] | None = None,
        image_rows: list[dict[str, str]] | None = None,
        pair_rows: list[dict[str, str]] | None = None,
        image_fields: list[str] | None = None,
        identity_rows: list[dict[str, str]] | None = None,
        sensitivity_rows: list[dict[str, str]] | None = None,
    ) -> tuple[dict[str, object], list[dict[str, str]]]:
        canonical_path = root / "canonical.csv"
        image_path = root / "images.csv"
        pair_path = root / "pairs.csv"
        write_rows(canonical_path, CANONICAL_FIELDS, canonical_rows or self.canonical_rows)
        write_rows(image_path, image_fields or IMAGE_FIELDS, image_rows or self.image_rows)
        write_rows(pair_path, PAIR_FIELDS, pair_rows or self.pair_rows)
        identity_path = None
        sensitivity_path = None
        if identity_rows is not None:
            identity_path = root / "identity.csv"
            write_rows(identity_path, IDENTITY_FIELDS, identity_rows)
        if sensitivity_rows is not None:
            sensitivity_path = root / "sensitivity.csv"
            write_rows(sensitivity_path, SENSITIVITY_FIELDS, sensitivity_rows)
        return contract.validate_partitions(
            canonical_path,
            image_path,
            pair_path,
            identity_map_path=identity_path,
            identity_sensitivity_path=sensitivity_path,
        )

    def test_valid_complete_partition_passes_but_is_not_lock_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            audit, issues = self.run_validation(Path(temporary))
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["identity_sensitivity_status"], "NOT_EVALUATED")
        self.assertEqual(audit["partition_lock_eligibility"], "PENDING_IDENTITY_AND_FREEZE_GATES")
        self.assertEqual(audit["counts"]["cross_role_candidate_pair_count"], 1)
        self.assertEqual(audit["counts"]["cross_role_pair_not_excluded_count"], 0)
        self.assertEqual(issues, [])

    def test_missing_candidate_pair_fails_complete_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            audit, issues = self.run_validation(Path(temporary), pair_rows=self.pair_rows[:-1])
        self.assertEqual(audit["status"], "FAIL")
        self.assertEqual(audit["counts"]["missing_candidate_pair_count"], 1)
        self.assertIn("missing_candidate_pair", {issue["code"] for issue in issues})

    def test_cross_role_pair_cannot_be_assigned(self) -> None:
        invalid_pairs = list(self.pair_rows)
        invalid_pairs[1] = pair(self.p2, "development")
        with tempfile.TemporaryDirectory() as temporary:
            audit, issues = self.run_validation(Path(temporary), pair_rows=invalid_pairs)
        self.assertEqual(audit["status"], "FAIL")
        self.assertEqual(audit["counts"]["cross_role_pair_not_excluded_count"], 1)
        self.assertIn("active_pair_endpoint_role_mismatch", {issue["code"] for issue in issues})

    def test_outcome_bearing_extension_column_is_rejected(self) -> None:
        fields = IMAGE_FIELDS + ["review_outcome_label"]
        rows = [{**row, "review_outcome_label": ""} for row in self.image_rows]
        with tempfile.TemporaryDirectory() as temporary:
            audit, issues = self.run_validation(Path(temporary), image_fields=fields, image_rows=rows)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_public_column", {issue["code"] for issue in issues})

    def test_identity_sensitivity_passes_when_confirmation_identities_are_unseen(self) -> None:
        identities = [
            {
                "partition_contract_version": contract.CONTRACT_VERSION,
                "image_id": image_id,
                "identity_id": identity_id,
                "access_class": "restricted",
            }
            for image_id, identity_id in {
                "a": "id_1",
                "b": "id_2",
                "c": "id_3",
                "d": "id_4",
                "e": "id_5",
                "f": "id_6",
            }.items()
        ]
        sensitivity = [
            {
                "partition_contract_version": contract.CONTRACT_VERSION,
                "canonical_pair_id": "p4",
                "sensitivity_set_id": "confirmation_identity_disjoint_v1",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            audit, issues = self.run_validation(
                Path(temporary), identity_rows=identities, sensitivity_rows=sensitivity
            )
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["identity_sensitivity_status"], "PASS")
        self.assertEqual(audit["counts"]["sensitivity_identity_overlap_count"], 0)
        self.assertEqual(issues, [])

    def test_identity_sensitivity_fails_when_identity_leaks_from_development(self) -> None:
        identities = [
            {
                "partition_contract_version": contract.CONTRACT_VERSION,
                "image_id": image_id,
                "identity_id": "shared" if image_id in {"a", "e"} else f"id_{image_id}",
                "access_class": "restricted",
            }
            for image_id in "abcdef"
        ]
        sensitivity = [
            {
                "partition_contract_version": contract.CONTRACT_VERSION,
                "canonical_pair_id": "p4",
                "sensitivity_set_id": "confirmation_identity_disjoint_v1",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            audit, issues = self.run_validation(
                Path(temporary), identity_rows=identities, sensitivity_rows=sensitivity
            )
        self.assertEqual(audit["status"], "FAIL")
        self.assertEqual(audit["identity_sensitivity_status"], "FAIL")
        self.assertEqual(audit["counts"]["sensitivity_identity_overlap_count"], 1)
        self.assertIn("sensitivity_identity_overlap", {issue["code"] for issue in issues})

    def test_identity_interface_cannot_pass_with_empty_sensitivity_manifest(self) -> None:
        identities = [
            {
                "partition_contract_version": contract.CONTRACT_VERSION,
                "image_id": image_id,
                "identity_id": f"id_{image_id}",
                "access_class": "restricted",
            }
            for image_id in "abcdef"
        ]
        with tempfile.TemporaryDirectory() as temporary:
            audit, issues = self.run_validation(
                Path(temporary), identity_rows=identities, sensitivity_rows=[]
            )
        self.assertEqual(audit["status"], "FAIL")
        self.assertEqual(audit["identity_sensitivity_status"], "FAIL")
        self.assertIn("empty_identity_sensitivity_manifest", {issue["code"] for issue in issues})

    def test_checked_in_schema_matches_executable_contract(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schemas/pferi_v2/partition_constraint_contract_v1.json"
        self.assertEqual(json.loads(schema_path.read_text(encoding="utf-8")), contract.build_contract_schema())

    def test_cli_writes_audit_issue_table_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical_path = root / "canonical.csv"
            image_path = root / "images.csv"
            pair_path = root / "pairs.csv"
            audit_path = root / "audit.json"
            issues_path = root / "issues.csv"
            schema_path = root / "schema.json"
            write_rows(canonical_path, CANONICAL_FIELDS, self.canonical_rows)
            write_rows(image_path, IMAGE_FIELDS, self.image_rows)
            write_rows(pair_path, PAIR_FIELDS, self.pair_rows)
            exit_code = contract.main(
                [
                    "--canonical-pairs",
                    str(canonical_path),
                    "--image-partitions",
                    str(image_path),
                    "--pair-partitions",
                    str(pair_path),
                    "--audit-json",
                    str(audit_path),
                    "--issue-csv",
                    str(issues_path),
                    "--write-schema",
                    str(schema_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["status"], "PASS")
            self.assertEqual(json.loads(schema_path.read_text(encoding="utf-8")), contract.build_contract_schema())
            self.assertEqual(issues_path.read_text(encoding="utf-8").splitlines()[0], ",".join(contract.ISSUE_COLUMNS))


if __name__ == "__main__":
    unittest.main()
