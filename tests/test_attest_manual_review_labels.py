from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import attest_manual_review_labels as attest


class AttestManualReviewLabelsTests(unittest.TestCase):
    def write_rows(self, path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def read_rows(self, path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_attestation_preserves_label_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "feature.csv"
            self.write_rows(
                path,
                [
                    {
                        "feature_varied_id": "fv1",
                        "target_review_ready": "yes",
                        "target_not_ready_reason": "",
                        "target_secondary_reason": "",
                        "target_notes": "Comparable individual evidence present across both images.",
                    },
                    {
                        "feature_varied_id": "fv2",
                        "target_review_ready": "no",
                        "target_not_ready_reason": "low_image_evidence",
                        "target_secondary_reason": "",
                        "target_notes": "Not review-ready under feature-varied evidence criteria.",
                    },
                ],
            )
            config = {
                "path": path,
                "id_column": "feature_varied_id",
                "status_column": "target_review_ready",
                "complete_values": {"yes", "no", "uncertain"},
                "label_columns": ["target_review_ready", "target_not_ready_reason", "target_secondary_reason"],
            }

            result = attest.attest_table("feature_varied", config, "2026-07-08T00:00:00+00:00")
            rows = self.read_rows(path)

            self.assertFalse(result["label_values_changed"])
            self.assertEqual([row["target_review_ready"] for row in rows], ["yes", "no"])
            self.assertTrue(all(row["manual_review_attested"] == "yes" for row in rows))

    def test_internal_reason_proxy_note_is_cleaned_without_label_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "internal.csv"
            self.write_rows(
                path,
                [
                    {
                        "enrichment_id": "r1",
                        "reason_label_review_status": "complete",
                        "target_primary_reason": "motion_or_blur",
                        "target_secondary_reason": "",
                        "target_body_region_visible": "full_body_or_most_body",
                        "target_notes": "Primary reason assigned from risk-decomposition proxy.",
                    }
                ],
            )
            config = {
                "path": path,
                "id_column": "enrichment_id",
                "status_column": "reason_label_review_status",
                "complete_values": {"complete"},
                "label_columns": ["target_primary_reason", "target_secondary_reason", "target_body_region_visible"],
            }

            result = attest.attest_table("internal_reason", config, "2026-07-08T00:00:00+00:00")
            row = self.read_rows(path)[0]

            self.assertFalse(result["label_values_changed"])
            self.assertEqual(row["target_primary_reason"], "motion_or_blur")
            self.assertIn("Human reviewer assigned", row["target_notes"])

    def test_build_reports_failure_if_any_table_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = {}
            for name in ["feature", "internal", "online"]:
                paths[name] = Path(tmp) / f"{name}.csv"
            self.write_rows(
                paths["feature"],
                [
                    {
                        "feature_varied_id": "fv1",
                        "target_review_ready": "",
                        "target_not_ready_reason": "",
                        "target_secondary_reason": "",
                        "target_notes": "",
                    }
                ],
            )
            self.write_rows(
                paths["internal"],
                [
                    {
                        "enrichment_id": "r1",
                        "reason_label_review_status": "complete",
                        "target_primary_reason": "low_image_evidence",
                        "target_secondary_reason": "",
                        "target_body_region_visible": "not_visible_or_unclear",
                        "target_notes": "",
                    }
                ],
            )
            self.write_rows(
                paths["online"],
                [
                    {
                        "online_enrichment_id": "o1",
                        "online_reason_label_review_status": "complete",
                        "target_review_ready": "no",
                        "target_primary_reason": "subject_too_small",
                        "target_secondary_reason": "",
                        "target_notes": "",
                    }
                ],
            )
            tables = {
                "feature_varied": {
                    "path": paths["feature"],
                    "id_column": "feature_varied_id",
                    "status_column": "target_review_ready",
                    "complete_values": {"yes", "no", "uncertain"},
                    "label_columns": ["target_review_ready", "target_not_ready_reason", "target_secondary_reason"],
                },
                "internal_reason": {
                    "path": paths["internal"],
                    "id_column": "enrichment_id",
                    "status_column": "reason_label_review_status",
                    "complete_values": {"complete"},
                    "label_columns": ["target_primary_reason", "target_secondary_reason", "target_body_region_visible"],
                },
                "online_supplement": {
                    "path": paths["online"],
                    "id_column": "online_enrichment_id",
                    "status_column": "online_reason_label_review_status",
                    "complete_values": {"complete"},
                    "label_columns": ["target_review_ready", "target_primary_reason", "target_secondary_reason"],
                },
            }
            with patch.object(attest, "TABLES", tables):
                with patch.object(attest, "OUTPUT_DIR", Path(tmp)):
                    with patch.object(attest, "AUDIT_JSON", Path(tmp) / "audit.json"):
                        with patch.object(attest, "AUDIT_MD", Path(tmp) / "audit.md"):
                            result = attest.build()

            self.assertEqual(result["status"], "FAIL")
            self.assertIn("feature_varied: incomplete rows remain", result["failures"])


if __name__ == "__main__":
    unittest.main()
