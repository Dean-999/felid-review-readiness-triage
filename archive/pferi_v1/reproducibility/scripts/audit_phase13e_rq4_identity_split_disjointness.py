#!/usr/bin/env python3
"""Audit whether Phase 13 RQ4 calibration/evaluation splits are identity-disjoint."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE12_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase12/phase12_pair_candidate_analysis_table.csv"
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/rq4_split_diagnostics"
OUT = OUT_DIR / "phase13e_rq4_identity_split_disjointness_audit.csv"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(
        PHASE12_TABLE,
        usecols=[
            "split_id",
            "descriptor",
            "calibration_or_evaluation",
            "query_identity_token",
            "candidate_identity_token",
        ],
    )
    rows: list[dict[str, object]] = []
    for (split_id, descriptor), frame in table.groupby(["split_id", "descriptor"], sort=True):
        calibration = frame[frame["calibration_or_evaluation"].eq("calibration")]
        evaluation = frame[frame["calibration_or_evaluation"].eq("evaluation")]
        calibration_ids = set(calibration["query_identity_token"].astype(str)) | set(
            calibration["candidate_identity_token"].astype(str)
        )
        evaluation_ids = set(evaluation["query_identity_token"].astype(str)) | set(
            evaluation["candidate_identity_token"].astype(str)
        )
        overlap = calibration_ids & evaluation_ids
        rows.append(
            {
                "split_id": int(split_id),
                "descriptor": descriptor,
                "calibration_identity_count": int(len(calibration_ids)),
                "evaluation_identity_count": int(len(evaluation_ids)),
                "overlap_identity_count": int(len(overlap)),
                "overlap_fraction_of_evaluation": float(len(overlap) / max(len(evaluation_ids), 1)),
                "identity_disjoint": "yes" if not overlap else "no",
                "claim_boundary": "held_out_identity_ok" if not overlap else "candidate_split_only",
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    fail_count = int(out["identity_disjoint"].eq("no").sum())
    print(
        "Phase 13E identity split audit: "
        f"identity_disjoint_pass={len(out) - fail_count} "
        f"candidate_split_only={fail_count} "
        f"output={OUT.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
