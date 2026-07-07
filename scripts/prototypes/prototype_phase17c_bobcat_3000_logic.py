#!/usr/bin/env python3
"""PROTOTYPE - throwaway Phase17C Bobcat 3000 selection logic explorer.

Question: does a clean-backbone plus transfer-sentinel state model feel sane
before we freeze Bobcat algorithm-prep inputs?

One command:
python3 scripts/prototypes/prototype_phase17c_bobcat_3000_logic.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_phase17b_bobcat_transfer_stress import prepare_bobcat_frame
from scripts.build_phase17c_bobcat_provisional_3000 import (
    DEFAULT_INPUT,
    assign_selection_buckets,
    build_provisional_selection,
    compute_selection_scores,
)


def scenario(frame: pd.DataFrame, transfer_count: int, group_cap: int) -> None:
    selected, _rejected, audit = build_provisional_selection(
        frame,
        target_count=3000,
        transfer_sentinel_count=transfer_count,
        max_per_balance_group=group_cap,
    )
    print("=" * 72)
    print(f"transfer_sentinel_count={transfer_count} max_per_balance_group={group_cap}")
    print(
        {
            "status": audit["selection_status"],
            "selected_rows": audit["selected_rows"],
            "role_counts": audit["selected_role_counts"],
            "bucket_counts": audit["selected_bucket_counts"],
            "balance_groups": audit["selected_balance_group_count"],
            "largest_group": audit["selected_max_balance_group_count"],
        }
    )
    print("route counts")
    print(selected.groupby(["phase17c_selection_role", "phase17b_route"]).size().to_string())
    print("score medians")
    print(
        selected.groupby("phase17c_selection_role")[
            ["final_candidate_score", "iqa_quality_proxy_score", "md_geometry_score"]
        ]
        .median()
        .to_string()
    )


def main() -> None:
    input_csv = Path(DEFAULT_INPUT)
    raw = pd.read_csv(input_csv, low_memory=False)
    frame = assign_selection_buckets(compute_selection_scores(prepare_bobcat_frame(raw)))
    print("PROTOTYPE - throwaway Phase17C selection logic explorer")
    print(f"input={input_csv}")
    print(f"rows={len(frame):,}")
    print("available buckets")
    print(frame["phase17c_selection_bucket"].value_counts().to_string())
    for transfer_count in [0, 150, 300, 600]:
        scenario(frame, transfer_count=transfer_count, group_cap=80)


if __name__ == "__main__":
    main()
