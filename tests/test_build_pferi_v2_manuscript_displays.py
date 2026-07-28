import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_pferi_v2_manuscript_displays import build


class ManuscriptDisplayBuildTests(unittest.TestCase):
    def test_builds_all_editable_tables_without_refitting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = build(root / "tables", root / "figures", render=False)
            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["main_table_count"], 6)
            self.assertEqual(audit["supplementary_table_count"], 16)
            self.assertEqual(audit["table_count"], 22)
            self.assertFalse(audit["models_refit"])
            self.assertFalse(audit["task15l_parameters_recomputed"])
            self.assertEqual(len(list((root / "tables").glob("table*.csv"))), 22)
            self.assertEqual(len(list((root / "tables").glob("table*.md"))), 22)

    def test_headline_results_and_boundaries_are_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root / "tables", root / "figures", render=False)
            with (root / "tables/table5_stage_results.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["p3_minus_p5"], "0.005863")
            self.assertEqual(rows[-1]["p3_minus_p5"], "-0.201870")
            self.assertEqual(rows[-1]["frozen_result"], "FAIL_PRIMARY_CONFIRMATION")
            with (root / "tables/table3_pair_inventories.csv").open(newline="") as handle:
                inventory = list(csv.DictReader(handle))
            self.assertEqual(inventory[2]["descriptor_supported_n_percent"], "252 (28.3%)")
            self.assertEqual(inventory[2]["descriptor_unsupported_n_percent"], "637 (71.7%)")

    def test_agreement_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root / "tables", root / "figures", render=False)
            with (root / "tables/table_s4_reviewer_agreement.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["three_category_exact_agreement"], "661 (41.3%)")
            self.assertEqual(rows[0]["binary_agreement"], "855 (53.4%)")
            self.assertEqual(rows[0]["cohen_kappa_binary"], "0.0787")
            self.assertEqual(rows[1]["binary_agreement"], "413 (92.2%)")


if __name__ == "__main__":
    unittest.main()
