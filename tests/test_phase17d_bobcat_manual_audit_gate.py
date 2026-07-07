import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.build_phase17d_bobcat_manual_audit_gate import (
    decide_freeze_state,
    enrich_audit_sheet,
    normalize_bool,
    run_phase17d_bobcat_manual_audit_gate,
)


def audit_rows(clean_allowed: int, clean_blocked: int, transfer_allowed: int, transfer_blocked: int) -> pd.DataFrame:
    rows = []
    idx = 0
    for role, allowed, blocked in [
        ("clean_backbone", clean_allowed, clean_blocked),
        ("transfer_sentinel", transfer_allowed, transfer_blocked),
    ]:
        for _ in range(allowed):
            idx += 1
            rows.append(row(idx, role, "yes"))
        for _ in range(blocked):
            idx += 1
            rows.append(row(idx, role, "no"))
    return pd.DataFrame(rows)


def blank_audit_rows() -> pd.DataFrame:
    rows = []
    for idx, role in enumerate(["clean_backbone"] * 20 + ["transfer_sentinel"] * 20, start=1):
        rows.append(
            {
                "candidate_id": f"p16e2_bobcat_{idx:05d}",
                "phase17c_selection_role": role,
                "phase17c_manual_audit_reason": f"selected_{role}",
                "source_tier": "1" if role == "clean_backbone" else "2",
                "phase17b_route": "high_confidence_review" if role == "clean_backbone" else "topup_stress_review",
                "is_bobcat_visible": "",
                "is_individual_review_usable": "",
                "selection_role_agreement": "",
                "algorithm_entry_allowed": "",
                "audit_notes": "",
            }
        )
    return pd.DataFrame(rows)


def row(idx: int, role: str, allowed: str) -> dict[str, object]:
    return {
        "candidate_id": f"p16e2_bobcat_{idx:05d}",
        "phase17c_selection_role": role,
        "phase17c_manual_audit_reason": f"selected_{role}",
        "source_tier": "1" if role == "clean_backbone" else "2",
        "phase17b_route": "high_confidence_review" if role == "clean_backbone" else "topup_stress_review",
        "is_bobcat_visible": "yes",
        "is_individual_review_usable": allowed,
        "selection_role_agreement": allowed,
        "algorithm_entry_allowed": allowed,
        "audit_notes": "",
    }


class Phase17DBobcatManualAuditGateTests(unittest.TestCase):
    def test_normalize_bool_accepts_common_values(self):
        self.assertTrue(normalize_bool("yes"))
        self.assertTrue(normalize_bool("allow"))
        self.assertFalse(normalize_bool("no"))
        self.assertFalse(normalize_bool("blocked"))
        self.assertIsNone(normalize_bool(""))

    def test_blank_audit_blocks_pending_completion(self):
        frame = blank_audit_rows()
        enriched = enrich_audit_sheet(frame)
        _decision, audit = decide_freeze_state(enriched, min_completed_per_role=20)

        self.assertEqual(audit["freeze_decision"], "BLOCKED_PENDING_AUDIT")

    def test_pass_when_clean_and_transfer_clear_gates(self):
        enriched = enrich_audit_sheet(audit_rows(38, 2, 32, 8))
        _decision, audit = decide_freeze_state(enriched, min_completed_per_role=20)

        self.assertEqual(audit["freeze_decision"], "PASS")

    def test_pass_with_split_when_transfer_fails(self):
        enriched = enrich_audit_sheet(audit_rows(38, 2, 20, 20))
        _decision, audit = decide_freeze_state(enriched, min_completed_per_role=20)

        self.assertEqual(audit["freeze_decision"], "PASS_WITH_SPLIT")

    def test_revise_when_clean_backbone_fails(self):
        enriched = enrich_audit_sheet(audit_rows(30, 10, 32, 8))
        _decision, audit = decide_freeze_state(enriched, min_completed_per_role=20)

        self.assertEqual(audit["freeze_decision"], "REVISE")

    def test_run_phase17d_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_sheet = root / "audit.csv"
            manifest = root / "manifest.csv"
            output_dir = root / "out"
            audit_rows(38, 2, 20, 20).to_csv(audit_sheet, index=False)
            pd.DataFrame([{"candidate_id": "p16e2_bobcat_00001"}]).to_csv(manifest, index=False)

            audit = run_phase17d_bobcat_manual_audit_gate(
                audit_sheet=audit_sheet,
                provisional_manifest=manifest,
                output_dir=output_dir,
                min_completed_per_role=20,
            )

            self.assertEqual(audit["freeze_decision"], "PASS_WITH_SPLIT")
            self.assertTrue((output_dir / "phase17d_bobcat_manual_audit_summary.csv").exists())
            self.assertTrue((output_dir / "phase17d_bobcat_algorithm_entry_decision.csv").exists())
            self.assertTrue((output_dir / "phase17d_bobcat_final_freeze_recommendation.md").exists())


if __name__ == "__main__":
    unittest.main()
