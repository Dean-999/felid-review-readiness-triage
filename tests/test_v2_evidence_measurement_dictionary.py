from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import validate_v2_evidence_measurement_dictionary as dictionary


class V2EvidenceMeasurementDictionaryTests(unittest.TestCase):
    def test_checked_in_dictionary_passes_validation(self) -> None:
        payload = dictionary.load_dictionary(dictionary.DEFAULT_DICTIONARY_PATH)
        audit = dictionary.validate_dictionary(payload)

        self.assertEqual(audit["status"], "PASS")
        self.assertGreaterEqual(audit["feature_count"], 10)
        self.assertEqual(audit["outcome_leakage_feature_count"], 0)

    def test_every_feature_declares_missingness_and_failure_taxonomy(self) -> None:
        payload = dictionary.load_dictionary(dictionary.DEFAULT_DICTIONARY_PATH)

        for feature in payload["features"]:
            self.assertTrue(feature["allowed_value_statuses"])
            self.assertTrue(feature["allowed_failure_codes"])
            self.assertIn("not_missing", feature["allowed_value_statuses"])

    def test_rejects_outcome_like_feature_name(self) -> None:
        payload = dictionary.build_default_dictionary()
        payload["features"][0]["feature_name"] = "review_ready_score"

        audit = dictionary.validate_dictionary(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("forbidden_feature_name_token:review_ready_score", audit["error_codes"])

    def test_rejects_manual_feature_claimed_as_automatic_primary_candidate(self) -> None:
        payload = dictionary.build_default_dictionary()
        feature = next(item for item in payload["features"] if item["role"] == "automatic_core_candidate")
        feature["inference_time_availability"] = "manual_only"

        audit = dictionary.validate_dictionary(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn(
            f"automatic_candidate_not_automatic:{feature['feature_name']}",
            audit["error_codes"],
        )

    def test_rejects_oracle_feature_as_primary_model_input(self) -> None:
        payload = dictionary.build_default_dictionary()
        feature = next(item for item in payload["features"] if item["role"] == "oracle_measurement")
        feature["primary_model_eligibility"] = "pending_workstream_02"

        audit = dictionary.validate_dictionary(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn(
            f"oracle_feature_not_blocked_from_primary_model:{feature['feature_name']}",
            audit["error_codes"],
        )

    def test_rejects_metadata_as_model_input(self) -> None:
        payload = dictionary.build_default_dictionary()
        feature = next(item for item in payload["features"] if item["role"] == "metadata_stratification_only")
        feature["primary_model_eligibility"] = "pending_workstream_02"

        audit = dictionary.validate_dictionary(payload)

        self.assertEqual(audit["status"], "FAIL")
        self.assertIn(
            f"metadata_feature_not_blocked_from_primary_model:{feature['feature_name']}",
            audit["error_codes"],
        )

    def test_cli_writes_audit_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "dictionary.json"
            audit_path = root / "audit.json"
            schema_path = root / "schema.json"
            input_path.write_text(json.dumps(dictionary.build_default_dictionary()), encoding="utf-8")

            exit_code = dictionary.main(
                [
                    "--dictionary",
                    str(input_path),
                    "--audit-json",
                    str(audit_path),
                    "--write-schema",
                    str(schema_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(audit_path.read_text(encoding="utf-8"))["status"], "PASS")
            self.assertEqual(json.loads(schema_path.read_text(encoding="utf-8"))["dictionary_version"], dictionary.DICTIONARY_VERSION)

    def test_checked_in_dictionary_has_all_three_measurement_roles(self) -> None:
        payload = dictionary.load_dictionary(dictionary.DEFAULT_DICTIONARY_PATH)
        roles = {feature["role"] for feature in payload["features"]}

        self.assertEqual(
            roles,
            {"automatic_core_candidate", "oracle_measurement", "metadata_stratification_only"},
        )


if __name__ == "__main__":
    unittest.main()
