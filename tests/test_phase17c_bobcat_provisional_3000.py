import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.build_phase17c_bobcat_provisional_3000 import (
    assign_selection_buckets,
    balance_group_hash,
    build_provisional_selection,
    compute_selection_scores,
    manual_audit_expansion_sheet,
    run_phase17c_bobcat_provisional_3000,
)


def fixture_rows() -> pd.DataFrame:
    rows = []
    for idx in range(1, 21):
        tier = "1" if idx <= 12 else "2"
        strict = idx <= 8 or 13 <= idx <= 16
        balanced = idx <= 10 or 13 <= idx <= 18
        broad = idx <= 11 or 13 <= idx <= 19
        rows.append(
            {
                "candidate_id": f"p16e2_bobcat_{idx:05d}",
                "source_tier": tier,
                "source_role": "fcf_high_geometry_primary" if tier == "1" else "fcf_next_best_topup",
                "source_dataset": "Felidae Conservation Fund 2020-2025",
                "topup_reason": "primary" if tier == "1" else "topup",
                "target_quadrant": "urban_bobcat_high_confidence",
                "species_label": "bobcat",
                "scientific_name": "Lynx rufus",
                "source_mode": "url",
                "image_uri": f"https://example.test/{idx // 3}/2024-01/{idx}.jpg",
                "original_source_key": f"{idx // 3}/2024-01/{idx}.jpg",
                "image_load_success": True,
                "scoring_valid_for_selection": True,
                "model_fallback_mode": False,
                "pose_fallback_scoring_used": False,
                "strict_recalibrated_eligible": strict,
                "balanced_recalibrated_eligible": balanced,
                "broad_recalibrated_eligible": broad,
                "final_candidate_score": 0.60 - idx * 0.01 if tier == "1" else 0.40 - idx * 0.005,
                "iqa_quality_proxy_score": 0.50 + idx * 0.005,
                "clip_side_view_score": 0.01 + idx * 0.001,
                "clip_viewpoint_label": "partial_or_occluded",
                "clip_viewpoint_confidence": 0.90,
                "clip_viewpoint_prob_partial_or_occluded": 0.50,
                "clip_viewpoint_prob_unclear": 0.05,
                "md_geometry_score": 0.30 if tier == "1" else 0.0,
                "image_width": 100,
                "image_height": 100,
                "crop_width": 100,
                "crop_height": 100,
            }
        )
    return pd.DataFrame(rows)


class Phase17CBobcatProvisional3000Tests(unittest.TestCase):
    def test_balance_group_hash_does_not_expose_source_key(self):
        hashed = balance_group_hash(pd.Series({"original_source_key": "68/2022-10/file.jpg"}))

        self.assertTrue(hashed.startswith("bg_"))
        self.assertNotIn("68", hashed)

    def test_assign_selection_buckets_separates_clean_and_transfer(self):
        frame = assign_selection_buckets(compute_selection_scores(fixture_rows()))

        self.assertIn("tier1_strict_clean_core", set(frame["phase17c_selection_bucket"]))
        self.assertIn("tier2_strict_transfer_sentinel", set(frame["phase17c_selection_bucket"]))

    def test_build_selection_uses_clean_backbone_and_transfer_sentinel(self):
        frame = assign_selection_buckets(compute_selection_scores(fixture_rows()))
        selected, rejected, audit = build_provisional_selection(
            frame,
            target_count=10,
            transfer_sentinel_count=2,
            max_per_balance_group=3,
        )

        self.assertEqual(len(selected), 10)
        self.assertEqual(audit["selection_status"], "PASS")
        self.assertEqual(int((selected["phase17c_selection_role"] == "transfer_sentinel").sum()), 2)
        self.assertTrue(selected["candidate_id"].is_unique)
        self.assertGreater(len(rejected), 0)

    def test_manual_audit_expansion_sheet_has_blank_audit_fields(self):
        frame = assign_selection_buckets(compute_selection_scores(fixture_rows()))
        selected, _rejected, _audit = build_provisional_selection(
            frame,
            target_count=10,
            transfer_sentinel_count=2,
            max_per_balance_group=3,
        )
        sheet = manual_audit_expansion_sheet(frame, selected, per_bucket=2)

        self.assertIn("algorithm_entry_allowed", sheet.columns)
        self.assertIn("claim_boundary", sheet.columns)
        self.assertGreaterEqual(len(sheet), 4)

    def test_run_phase17c_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_csv = root / "bobcat.csv"
            output_dir = root / "out"
            fixture_rows().to_csv(input_csv, index=False)

            audit = run_phase17c_bobcat_provisional_3000(
                input_csv=input_csv,
                output_dir=output_dir,
                target_count=10,
                transfer_sentinel_count=2,
                max_per_balance_group=3,
                manual_audit_per_bucket=2,
            )

            self.assertEqual(audit["selection_status"], "PASS")
            self.assertEqual(audit["claim_status"], "PROVISIONAL_REVIEW_READINESS_FOUNDATION_ONLY")
            self.assertTrue((output_dir / "phase17c_bobcat_provisional_3000_manifest.csv").exists())
            self.assertTrue((output_dir / "phase17c_bobcat_manual_audit_expansion_sheet.csv").exists())
            self.assertTrue((output_dir / "phase17c_bobcat_provisional_3000_report.md").exists())


if __name__ == "__main__":
    unittest.main()
