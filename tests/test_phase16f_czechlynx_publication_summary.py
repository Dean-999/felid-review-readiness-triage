import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.summarize_phase16f_czechlynx_publication_selection import (
    build_metric_summary,
    build_publication_summary,
    build_viewpoint_summary,
)


class Phase16FCzechLynxPublicationSummaryTests(unittest.TestCase):
    def test_metric_summary_groups_selected_rows_by_bucket(self):
        df = pd.DataFrame(
            [
                {
                    "phase16f_selection_bucket": "strict_core",
                    "final_candidate_score": 0.9,
                    "iqa_quality_proxy_score": 0.8,
                    "clip_side_view_score": 0.7,
                },
                {
                    "phase16f_selection_bucket": "strict_core",
                    "final_candidate_score": 0.7,
                    "iqa_quality_proxy_score": 0.6,
                    "clip_side_view_score": 0.5,
                },
                {
                    "phase16f_selection_bucket": "balanced_only",
                    "final_candidate_score": 0.5,
                    "iqa_quality_proxy_score": 0.4,
                    "clip_side_view_score": 0.3,
                },
            ]
        )

        summary = build_metric_summary(df)
        strict = summary[summary["phase16f_selection_bucket"] == "strict_core"].iloc[0]

        self.assertEqual(int(strict["count"]), 2)
        self.assertAlmostEqual(float(strict["final_candidate_score_p50"]), 0.8)

    def test_viewpoint_summary_reports_bucket_rates(self):
        df = pd.DataFrame(
            [
                {"phase16f_selection_bucket": "strict_core", "clip_viewpoint_label": "left_side"},
                {"phase16f_selection_bucket": "strict_core", "clip_viewpoint_label": "left_side"},
                {"phase16f_selection_bucket": "strict_core", "clip_viewpoint_label": "unclear"},
            ]
        )

        summary = build_viewpoint_summary(df)
        left = summary[summary["clip_viewpoint_label"] == "left_side"].iloc[0]

        self.assertEqual(int(left["count"]), 2)
        self.assertAlmostEqual(float(left["rate_within_bucket"]), 2 / 3)

    def test_build_publication_summary_writes_report_and_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            selected = root / "selected.csv"
            output = root / "out"
            pd.DataFrame(
                [
                    {
                        "candidate_id": "a",
                        "phase16f_selection_bucket": "strict_core",
                        "phase16f_balance_group": "lynx_001",
                        "final_candidate_score": 0.9,
                        "iqa_quality_proxy_score": 0.8,
                        "clip_side_view_score": 0.7,
                        "clip_viewpoint_label": "left_side",
                        "already_in_current_high_final": "true",
                    }
                ]
            ).to_csv(selected, index=False)

            audit = build_publication_summary(selected, output)

            self.assertEqual(audit["selected_rows"], 1)
            self.assertTrue((output / "phase16f_czechlynx_publication_summary.md").exists())
            self.assertTrue((output / "phase16f_czechlynx_publication_metric_summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
