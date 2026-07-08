from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import analyze_blind_reliability_reviews as analyze
from scripts import build_blind_reliability_packet as packet


class BlindReliabilityPacketTests(unittest.TestCase):
    def test_review_template_hides_original_labels(self) -> None:
        source = {
            "source_packet": "feature_varied",
            "source_row_id": "fv1",
            "query_image_path": "q.jpg",
            "candidate_image_path": "c.jpg",
            "original_target_review_ready": "yes",
            "original_primary_reason": "",
            "original_secondary_reason": "",
            "selection_stratum": "yes",
        }

        row = packet.blind_row(source, 1)
        template = {
            "blind_pair_id": row["blind_pair_id"],
            "source_packet": row["source_packet"],
            "query_image_path": row["query_image_path"],
            "candidate_image_path": row["candidate_image_path"],
            "reviewer_id": "",
            "review_ready": "",
            "primary_reason": "",
            "secondary_reason": "",
            "body_region_visible": "",
            "reviewer_confidence": "",
            "reviewer_notes": "",
        }

        self.assertIn("original_target_review_ready", row)
        self.assertNotIn("original_target_review_ready", template)
        self.assertNotIn("original_primary_reason", template)

    def test_cohen_kappa_perfect_and_none(self) -> None:
        self.assertEqual(analyze.cohen_kappa(["yes", "no"], ["yes", "no"]), 1.0)
        self.assertLessEqual(analyze.cohen_kappa(["yes", "yes", "no", "no"], ["no", "no", "yes", "yes"]), 0.0)

    def test_claim_gate_thresholds(self) -> None:
        strong = {
            "pair_count": 280,
            "binary_cohen_kappa": 0.72,
            "primary_reason_agreement_on_nonready": 0.70,
        }
        moderate = {
            "pair_count": 280,
            "binary_cohen_kappa": 0.60,
            "primary_reason_agreement_on_nonready": 0.50,
        }

        self.assertEqual(analyze.claim_gate(strong), "BLIND_RELIABILITY_STRONG_SUPPORT")
        self.assertEqual(analyze.claim_gate(moderate), "BLIND_RELIABILITY_MODERATE_SUPPORT")

    def test_build_detail_uses_hidden_master_labels(self) -> None:
        master = [
            {
                "blind_pair_id": "blind_pair_0001",
                "source_packet": "feature_varied",
                "original_target_review_ready": "uncertain",
                "original_primary_reason": "low_image_evidence",
            }
        ]
        reviews = [
            {
                "blind_pair_id": "blind_pair_0001",
                "reviewer_id": "r1",
                "review_ready": "no",
                "primary_reason": "low_image_evidence",
                "reviewer_confidence": "high",
            }
        ]

        detail = analyze.build_detail(master, reviews)

        self.assertEqual(detail[0]["original_review_ready"], "uncertain")
        self.assertEqual(detail[0]["original_binary_ready"], "no")
        self.assertEqual(detail[0]["binary_ready_match"], "yes")
        self.assertEqual(detail[0]["primary_reason_match"], "yes")
        self.assertEqual(detail[0]["original_reason_family"], "image_evidence_deficit")
        self.assertEqual(detail[0]["reason_family_match"], "yes")

    def test_reason_family_maps_fine_labels_to_claim_families(self) -> None:
        self.assertEqual(analyze.reason_family("low_image_evidence"), "image_evidence_deficit")
        self.assertEqual(analyze.reason_family("subject_too_small"), "image_evidence_deficit")
        self.assertEqual(analyze.reason_family("non_comparable_viewpoint"), "pair_non_comparability")
        self.assertEqual(analyze.reason_family("descriptor_evidence_conflict"), "descriptor_evidence_conflict")
        self.assertEqual(analyze.reason_family("source_domain_stress"), "source_domain_stress")

    def test_disagreement_appendix_and_reason_family_summary(self) -> None:
        detail = [
            {
                "blind_pair_id": "blind_pair_0001",
                "source_packet": "feature_varied",
                "reviewer_id": "r1",
                "original_review_ready": "no",
                "reviewer_review_ready": "yes",
                "original_binary_ready": "no",
                "reviewer_binary_ready": "yes",
                "review_ready_exact_match": "no",
                "binary_ready_match": "no",
                "original_primary_reason": "low_image_evidence",
                "reviewer_primary_reason": "",
                "primary_reason_match": "no",
                "original_reason_family": "image_evidence_deficit",
                "reviewer_reason_family": "",
                "reason_family_match": "no",
                "reviewer_confidence": "medium",
            },
            {
                "blind_pair_id": "blind_pair_0002",
                "source_packet": "feature_varied",
                "reviewer_id": "r1",
                "original_review_ready": "no",
                "reviewer_review_ready": "no",
                "original_binary_ready": "no",
                "reviewer_binary_ready": "no",
                "review_ready_exact_match": "yes",
                "binary_ready_match": "yes",
                "original_primary_reason": "subject_too_small",
                "reviewer_primary_reason": "partial_body",
                "primary_reason_match": "no",
                "original_reason_family": "image_evidence_deficit",
                "reviewer_reason_family": "image_evidence_deficit",
                "reason_family_match": "yes",
                "reviewer_confidence": "high",
            },
        ]

        appendix = analyze.build_disagreement_appendix(detail)
        summary = analyze.build_reason_family_summary(detail)
        overall_image = next(
            row
            for row in summary
            if row["scope"] == "overall" and row["reason_family"] == "image_evidence_deficit"
        )

        self.assertEqual(len(appendix), 2)
        self.assertEqual(appendix[0]["disagreement_type"], "binary_ready+primary_reason+reason_family")
        self.assertEqual(appendix[1]["disagreement_type"], "primary_reason")
        self.assertEqual(overall_image["original_nonready_count"], 2)
        self.assertEqual(overall_image["matched_count"], 1)
        self.assertEqual(overall_image["family_agreement_rate_on_original_nonready"], 0.5)

    def test_build_reviewer_working_packet_hides_master_labels(self) -> None:
        master_rows = [
            {
                "blind_pair_id": "blind_pair_0001",
                "source_packet": "feature_varied",
                "source_row_id": "fv1",
                "query_image_path": "q.jpg",
                "candidate_image_path": "c.jpg",
                "original_target_review_ready": "no",
                "original_primary_reason": "low_image_evidence",
                "original_secondary_reason": "",
                "selection_stratum": "no",
                "selection_basis": "test",
                "claim_boundary": "hidden",
            }
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            master_csv = tmp / "master.csv"
            output_dir = tmp / "external-reviews"
            with master_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=packet.MASTER_COLUMNS)
                writer.writeheader()
                writer.writerows(master_rows)

            with patch.object(packet, "MASTER_PACKET_CSV", master_csv), patch.object(
                packet, "EXTERNAL_REVIEWS_DIR", output_dir
            ):
                audit = packet.build_reviewer_working_packet("external_reviewer_2")

            with (tmp / audit["working_csv"]).open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(rows[0]["reviewer_id"], "external_reviewer_2")
        self.assertEqual(rows[0]["review_ready"], "")
        self.assertNotIn("original_target_review_ready", rows[0])
        self.assertNotIn("original_primary_reason", rows[0])

    def test_corrected_reviewer_copy_preserves_labels_and_replaces_stale_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            output_dir = tmp / "external-reviews"
            reviewer_dir = output_dir / "external_reviewer_2"
            reviewer_dir.mkdir(parents=True)
            working_csv = reviewer_dir / "blind_reliability_review_working.csv"
            rows = [
                {
                    "blind_pair_id": "blind_pair_0001",
                    "source_packet": "feature_varied",
                    "query_image_path": "q.jpg",
                    "candidate_image_path": "c.jpg",
                    "reviewer_id": "external_reviewer_2",
                    "review_ready": "no",
                    "primary_reason": "low_image_evidence",
                    "secondary_reason": "",
                    "body_region_visible": "flank",
                    "reviewer_confidence": "high",
                    "reviewer_notes": "synthetic calibration labels for private threshold comparison only; not independent blind evidence; generated 2026-07-08",
                    "reviewed_at_utc": "2026-07-08T00:00:00Z",
                }
            ]
            with working_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            (reviewer_dir / "provenance_correction.md").write_text("confirmed", encoding="utf-8")
            (reviewer_dir / "provenance_correction.json").write_text("{}", encoding="utf-8")

            with patch.object(packet, "EXTERNAL_REVIEWS_DIR", output_dir):
                audit = packet.build_corrected_reviewer_copy("external_reviewer_2")

            corrected_path = tmp / audit["corrected_csv"]
            with corrected_path.open(newline="", encoding="utf-8") as handle:
                corrected = list(csv.DictReader(handle))

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["row_count"], 1)
        self.assertEqual(audit["stale_not_independent_note_rows"], 1)
        self.assertEqual(corrected[0]["review_ready"], "no")
        self.assertEqual(corrected[0]["primary_reason"], "low_image_evidence")
        self.assertIn("independent external blind review confirmed", corrected[0]["reviewer_notes"])
        self.assertNotIn("original_target_review_ready", corrected[0])


if __name__ == "__main__":
    unittest.main()
