import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_phase16g_real_czechlynx_pair_table import (
    build_descriptor_pairs_for_selected,
    build_selected_image_table,
    normalize_czechlynx_key,
    run_real_czechlynx_pair_table,
)


class Phase16GRealCzechLynxPairTableTest(unittest.TestCase):
    def test_normalize_czechlynx_key_handles_absolute_and_relative_paths(self):
        absolute = "/Users/example/project/data/raw/czechlynx/CzechLynx/foe_bohemia/lynx_120/20356_lynx_120.jpg"
        relative = "CzechLynx/foe_bohemia/lynx_120/20356_lynx_120.jpg"

        self.assertEqual(
            normalize_czechlynx_key(absolute),
            "CzechLynx/foe_bohemia/lynx_120/20356_lynx_120.jpg",
        )
        self.assertEqual(
            normalize_czechlynx_key(relative),
            "CzechLynx/foe_bohemia/lynx_120/20356_lynx_120.jpg",
        )

    def test_build_selected_image_table_maps_real_phase16f_columns(self):
        selected = pd.DataFrame(
            [
                {
                    "candidate_id": "p16e_1",
                    "image_key": "CzechLynx/site/lynx_001/a.jpg",
                    "phase16f_selection_bucket": "strict_core",
                    "phase16f_balance_group": "lynx_001",
                    "iqa_quality_proxy_score": 0.9,
                    "clip_side_view_score": 0.8,
                    "clip_viewpoint_label": "left_side",
                    "source_name": "czechlynx_real_all",
                    "phase16f_selection_rank": 1,
                }
            ]
        )

        out = build_selected_image_table(selected)

        self.assertEqual(out.loc[0, "image_id"], "CzechLynx/site/lynx_001/a.jpg")
        self.assertEqual(out.loc[0, "identity_id"], "lynx_001")
        self.assertEqual(out.loc[0, "phase16f_tier"], "strict_core")
        self.assertAlmostEqual(out.loc[0, "iqa_score"], 0.9)
        self.assertAlmostEqual(out.loc[0, "side_probability"], 0.8)

    def test_build_descriptor_pairs_keeps_only_selected_selected_pairs_and_flags_metadata(self):
        selected_images = pd.DataFrame(
            [
                {"image_id": "CzechLynx/site/lynx_001/a.jpg"},
                {"image_id": "CzechLynx/site/lynx_001/b.jpg"},
                {"image_id": "CzechLynx/site/lynx_002/c.jpg"},
            ]
        )
        routing = pd.DataFrame(
            [
                {
                    "query_image_path": "/root/CzechLynx/site/lynx_001/a.jpg",
                    "candidate_image_path": "/root/CzechLynx/site/lynx_001/b.jpg",
                    "rank": 1,
                    "descriptor_similarity": 0.95,
                    "descriptor_evidence_conflict_score": 0.2,
                    "query_identity_label": "lynx_001",
                    "candidate_identity_label": "lynx_001",
                    "evidence_route_decision": "review",
                },
                {
                    "query_image_path": "/root/CzechLynx/site/lynx_001/a.jpg",
                    "candidate_image_path": "/root/CzechLynx/site/lynx_999/z.jpg",
                    "rank": 2,
                    "descriptor_similarity": 0.40,
                    "descriptor_evidence_conflict_score": 0.1,
                    "query_identity_label": "lynx_001",
                    "candidate_identity_label": "lynx_999",
                    "evidence_route_decision": "review",
                },
            ]
        )
        leakage = pd.DataFrame(
            [
                {
                    "query_image_path": "/root/CzechLynx/site/lynx_001/a.jpg",
                    "candidate_image_path": "/root/CzechLynx/site/lynx_001/b.jpg",
                    "phase16_site_leakage_pressure": True,
                }
            ]
        )
        laterality = pd.DataFrame(
            [
                {
                    "query_image_path": "/root/CzechLynx/site/lynx_001/a.jpg",
                    "candidate_image_path": "/root/CzechLynx/site/lynx_001/b.jpg",
                    "phase16_pair_side_relation": "same_side",
                    "side_direction_compatibility": 1.0,
                }
            ]
        )

        out = build_descriptor_pairs_for_selected(
            routing,
            selected_images,
            leakage=leakage,
            laterality=laterality,
        )

        self.assertEqual(len(out), 1)
        row = out.iloc[0]
        self.assertEqual(row["query_image_id"], "CzechLynx/site/lynx_001/a.jpg")
        self.assertEqual(row["candidate_image_id"], "CzechLynx/site/lynx_001/b.jpg")
        self.assertTrue(bool(row["source_leakage_pressure_flag"]))
        self.assertEqual(row["laterality_relation"], "same_side")
        self.assertEqual(row["split_group"], "query::lynx_001")

    def test_run_real_czechlynx_pair_table_writes_expected_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            selected_path = root / "selected.csv"
            routing_path = root / "routing.csv"
            output_dir = root / "out"

            pd.DataFrame(
                [
                    {
                        "candidate_id": "p16e_1",
                        "image_key": "CzechLynx/site/lynx_001/a.jpg",
                        "phase16f_selection_bucket": "strict_core",
                        "phase16f_balance_group": "lynx_001",
                        "iqa_quality_proxy_score": 0.9,
                        "clip_side_view_score": 0.8,
                        "clip_viewpoint_label": "left_side",
                    },
                    {
                        "candidate_id": "p16e_2",
                        "image_key": "CzechLynx/site/lynx_001/b.jpg",
                        "phase16f_selection_bucket": "strict_core",
                        "phase16f_balance_group": "lynx_001",
                        "iqa_quality_proxy_score": 0.85,
                        "clip_side_view_score": 0.7,
                        "clip_viewpoint_label": "left_side",
                    },
                ]
            ).to_csv(selected_path, index=False)
            pd.DataFrame(
                [
                    {
                        "query_image_path": "/root/CzechLynx/site/lynx_001/a.jpg",
                        "candidate_image_path": "/root/CzechLynx/site/lynx_001/b.jpg",
                        "rank": 1,
                        "descriptor_similarity": 0.95,
                        "descriptor_evidence_conflict_score": 0.2,
                        "query_identity_label": "lynx_001",
                        "candidate_identity_label": "lynx_001",
                        "evidence_route_decision": "review",
                    }
                ]
            ).to_csv(routing_path, index=False)

            summary = run_real_czechlynx_pair_table(
                selected_path=selected_path,
                routing_path=routing_path,
                output_dir=output_dir,
                leakage_path=None,
                laterality_path=None,
            )

            self.assertEqual(summary["audit_status"], "PASS")
            self.assertEqual(summary["pair_rows"], 1)
            self.assertTrue((output_dir / "phase16g_czechlynx_pair_table.csv").exists())
            self.assertTrue((output_dir / "phase16g_czechlynx_run_report.md").exists())


if __name__ == "__main__":
    unittest.main()
