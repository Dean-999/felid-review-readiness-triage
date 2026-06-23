#!/usr/bin/env python3
"""Preview Phase 11D-R revised positive-rescue activation counts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv"
OUT = PROJECT_ROOT / (
    "outputs/czechlynx/phase11d/revised_positive_rescue/"
    "phase11dr_revised_positive_rescue_count_preview.csv"
)
BASE_GROUP = "H3_pf_eri_quality_hybrid_matched_identity"

VARIANTS = [
    {
        "experiment_group": "P11DR_rescue_desc_q80_R045_floor035",
        "reliability_max": 0.45,
        "similarity_quantile": 0.80,
        "pattern_required": False,
        "pattern_min": 0.0,
        "floor": 0.35,
    },
    {
        "experiment_group": "P11DR_rescue_pattern030_q75_R045_floor035",
        "reliability_max": 0.45,
        "similarity_quantile": 0.75,
        "pattern_required": True,
        "pattern_min": 0.30,
        "floor": 0.35,
    },
    {
        "experiment_group": "P11DR_rescue_desc_q85_R050_floor030",
        "reliability_max": 0.50,
        "similarity_quantile": 0.85,
        "pattern_required": False,
        "pattern_min": 0.0,
        "floor": 0.30,
    },
]

TARGETS = {
    1: (10, 35),
    3: (18, 45),
}


def pct(count: int, total: int) -> float:
    return float(count / total) if total else 0.0


def summarize_variant(positive: pd.DataFrame, split_id: int, variant: dict[str, object]) -> dict[str, object]:
    threshold = float(positive["descriptor_similarity"].quantile(float(variant["similarity_quantile"])))
    r_below = positive[positive["pair_reliability_score"] < float(variant["reliability_max"])].copy()
    rescued_mask = (
        (positive["pair_reliability_score"] < float(variant["reliability_max"]))
        & (positive["descriptor_similarity"] >= threshold)
    )
    if bool(variant["pattern_required"]):
        rescued_mask &= positive["pattern_pair_score"] >= float(variant["pattern_min"])
    rescued = positive[rescued_mask].copy()
    target_min, target_max = TARGETS[split_id]
    count = int(len(rescued))
    if count == 0:
        activation_status = "zero_fail"
    elif target_min <= count <= target_max:
        activation_status = "target_reached"
    else:
        activation_status = "nonzero_below_target" if count < target_min else "above_target"
    return {
        "split_id": split_id,
        "experiment_group": variant["experiment_group"],
        "base_group_name": BASE_GROUP,
        "total_positive_pairs": int(len(positive)),
        "rescued_positive_pairs": count,
        "pct_rescued_positive_pairs": pct(count, len(positive)),
        "target_min_rescued_pairs": target_min,
        "target_max_rescued_pairs": target_max,
        "activation_status": activation_status,
        "target_reached": bool(target_min <= count <= target_max),
        "nonzero_rescue": bool(count > 0),
        "total_positives_below_r_threshold": int(len(r_below)),
        "reliability_max": float(variant["reliability_max"]),
        "descriptor_similarity_quantile": float(variant["similarity_quantile"]),
        "descriptor_similarity_threshold": threshold,
        "pattern_required": bool(variant["pattern_required"]),
        "pattern_min": float(variant["pattern_min"]),
        "positive_rescue_floor": float(variant["floor"]),
        "mean_r_rescued_positives": float(rescued["pair_reliability_score"].mean()) if len(rescued) else float("nan"),
        "mean_descriptor_similarity_rescued_positives": float(rescued["descriptor_similarity"].mean()) if len(rescued) else float("nan"),
        "mean_pattern_pair_score_rescued_positives": float(rescued["pattern_pair_score"].mean()) if len(rescued) else float("nan"),
    }


def main() -> None:
    pair_table = pd.read_csv(PAIR_TABLE)
    required = {
        "split_id",
        "group_name",
        "same_identity",
        "descriptor_similarity",
        "pair_reliability_score",
        "pattern_pair_score",
    }
    missing = required - set(pair_table.columns)
    if missing:
        raise ValueError(f"pair table missing required columns: {sorted(missing)}")
    for column in ["descriptor_similarity", "pair_reliability_score", "pattern_pair_score"]:
        pair_table[column] = pd.to_numeric(pair_table[column], errors="coerce")
    if pair_table[["descriptor_similarity", "pair_reliability_score", "pattern_pair_score"]].isna().any().any():
        raise ValueError("pair table has missing/non-numeric revised rescue fields")

    rows: list[dict[str, object]] = []
    for split_id in [1, 3]:
        split = pair_table[
            (pair_table["split_id"].astype(int) == split_id)
            & (pair_table["group_name"].astype(str) == BASE_GROUP)
        ].copy()
        if split.empty:
            raise ValueError(f"no pair rows for split={split_id} group={BASE_GROUP}")
        same = split["same_identity"].astype(str).str.lower().isin(["true", "1", "yes"])
        positive = split[same].copy()
        for variant in VARIANTS:
            rows.append(summarize_variant(positive, split_id, variant))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(PROJECT_ROOT)} rows={len(rows)}")


if __name__ == "__main__":
    main()
