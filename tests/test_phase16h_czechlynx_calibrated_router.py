import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.build_phase16h_czechlynx_calibrated_router import (
    FEATURE_COLUMNS,
    build_model_frame,
    evaluate_rank_scores,
    run_phase16h_calibrated_router,
)


def fixture_scored_pairs() -> pd.DataFrame:
    rows = []
    for query_idx in range(12):
        query_id = f"q{query_idx}"
        split_group = f"query::id{query_idx}"
        for cand_idx in range(6):
            same = cand_idx == 0
            rows.append(
                {
                    "pair_id": f"{query_id}::c{cand_idx}",
                    "query_image_id": query_id,
                    "candidate_image_id": f"{query_id}_c{cand_idx}",
                    "split_group": split_group,
                    "phase16h_label": same,
                    "same_identity_label": same,
                    "label_allowed_for_modeling": True,
                    "source_leakage_pressure_flag": cand_idx == 5,
                    "score_descriptor_only": 0.90 - cand_idx * 0.08 + (0.01 * query_idx),
                    "score_quality_only": 0.80 if same else 0.35 + cand_idx * 0.02,
                    "score_evidence_only": 0.82 if same else 0.30 + cand_idx * 0.03,
                    "score_conflict_penalized_descriptor": 0.86 if same else 0.40 + cand_idx * 0.04,
                    "score_phase16h_diagnostic": 0.88 if same else 0.35 + cand_idx * 0.03,
                    "descriptor_similarity": 0.90 - cand_idx * 0.08,
                    "weakest_iqa_score": 0.80 if same else 0.35,
                    "query_side_probability": 0.85,
                    "candidate_side_probability": 0.80 if same else 0.30,
                    "descriptor_margin": 0.10 if same else 0.50,
                }
            )
    return pd.DataFrame(rows)


class Phase16HCalibratedRouterTest(unittest.TestCase):
    def test_build_model_frame_excludes_leakage_by_default(self):
        frame = build_model_frame(fixture_scored_pairs(), exclude_leakage=True)

        self.assertFalse(frame["source_leakage_pressure_flag"].astype(bool).any())
        self.assertTrue(set(FEATURE_COLUMNS).issubset(frame.columns))
        self.assertIn("phase16h_label", frame.columns)

    def test_evaluate_rank_scores_reports_descriptor_and_model(self):
        frame = build_model_frame(fixture_scored_pairs(), exclude_leakage=True)
        scored = frame.copy()
        scored["score_test_model"] = scored["score_phase16h_diagnostic"]
        metrics = evaluate_rank_scores(
            scored,
            score_columns={
                "descriptor_only": "score_descriptor_only",
                "test_model": "score_test_model",
            },
            k_values=[1, 3],
            split_id=0,
            subset_name="fixture",
        )

        self.assertEqual(set(metrics["policy_id"]), {"descriptor_only", "test_model"})
        self.assertEqual(set(metrics["k"]), {1, 3})

    def test_run_phase16h_calibrated_router_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_csv = root / "scored.csv"
            output_dir = root / "out"
            fixture_scored_pairs().to_csv(input_csv, index=False)

            audit = run_phase16h_calibrated_router(
                input_csv=input_csv,
                output_dir=output_dir,
                repeats=3,
                test_size=0.30,
                random_seed=13,
            )

            self.assertEqual(audit["status"], "PASS")
            self.assertIn(audit["claim_status"], {"NO_IMPROVEMENT_CLAIM", "CANDIDATE_SIGNAL_ONLY"})
            self.assertTrue((output_dir / "phase16h_calibrated_router_split_metrics.csv").exists())
            self.assertTrue((output_dir / "phase16h_calibrated_router_summary.csv").exists())
            self.assertTrue((output_dir / "phase16h_calibrated_router_audit.json").exists())
            self.assertTrue((output_dir / "phase16h_calibrated_router_report.md").exists())


if __name__ == "__main__":
    unittest.main()
