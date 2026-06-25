#!/usr/bin/env python3
"""Preview Phase 11D-R2 target-rate positive rescue counts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv"
OUT = PROJECT_ROOT / (
    "outputs/czechlynx/phase11d/target_rate_positive_rescue/"
    "phase11dr2_target_rate_positive_rescue_count_preview.csv"
)
BASE_GROUP = "H3_pf_eri_quality_hybrid_matched_identity"

VARIANTS = [
    {"experiment_group": "P11DR2_target05_floor035", "target_fraction": 0.05, "reliability_max": 0.55, "floor": 0.35},
    {"experiment_group": "P11DR2_target10_floor035", "target_fraction": 0.10, "reliability_max": 0.55, "floor": 0.35},
    {"experiment_group": "P11DR2_target10_floor040", "target_fraction": 0.10, "reliability_max": 0.55, "floor": 0.40},
]


def pct(count: int, total: int) -> float:
    return float(count / total) if total else 0.0


def target_count(total_positive_pairs: int, fraction: float) -> int:
    if total_positive_pairs <= 0:
        return 0
    return max(1, int(round(float(fraction) * total_positive_pairs)))


def summarize_variant(positive: pd.DataFrame, split_id: int, variant: dict[str, float | str]) -> dict[str, object]:
    candidates = positive[positive["pair_reliability_score"] < float(variant["reliability_max"])].copy()
    candidates["rescue_score"] = candidates["descriptor_similarity"] * (1.0 - candidates["pair_reliability_score"])
    requested_k = target_count(len(positive), float(variant["target_fraction"]))
    rescued = candidates.sort_values(
        ["rescue_score", "descriptor_similarity", "pair_reliability_score"],
        ascending=[False, False, True],
    ).head(requested_k)
    actual = int(len(rescued))
    target_reached = actual == min(requested_k, len(candidates))
    if len(candidates) < requested_k:
        activation_status = "all_candidates_rescued_below_target"
    elif target_reached:
        activation_status = "target_reached"
    else:
        activation_status = "target_not_reached"
    return {
        "split_id": split_id,
        "experiment_group": variant["experiment_group"],
        "base_group_name": BASE_GROUP,
        "total_positive_pairs": int(len(positive)),
        "candidate_positive_pairs": int(len(candidates)),
        "target_rescue_fraction": float(variant["target_fraction"]),
        "target_rescue_count": int(requested_k),
        "actual_rescued_count": actual,
        "actual_rescued_fraction": pct(actual, len(positive)),
        "reliability_max": float(variant["reliability_max"]),
        "rescue_floor": float(variant["floor"]),
        "target_reached": bool(target_reached),
        "activation_status": activation_status,
        "mean_r_rescued_positives": float(rescued["pair_reliability_score"].mean()) if actual else float("nan"),
        "mean_descriptor_similarity_rescued_positives": float(rescued["descriptor_similarity"].mean()) if actual else float("nan"),
        "mean_rescue_score_rescued_positives": float(rescued["rescue_score"].mean()) if actual else float("nan"),
        "min_rescue_score_rescued_positives": float(rescued["rescue_score"].min()) if actual else float("nan"),
        "max_rescue_score_rescued_positives": float(rescued["rescue_score"].max()) if actual else float("nan"),
    }


def main() -> None:
    pair_table = pd.read_csv(PAIR_TABLE)
    required = {
        "split_id",
        "group_name",
        "same_identity",
        "descriptor_similarity",
        "pair_reliability_score",
    }
    missing = required - set(pair_table.columns)
    if missing:
        raise ValueError(f"pair table missing required columns: {sorted(missing)}")
    for column in ["descriptor_similarity", "pair_reliability_score"]:
        pair_table[column] = pd.to_numeric(pair_table[column], errors="coerce")
    if pair_table[["descriptor_similarity", "pair_reliability_score"]].isna().any().any():
        raise ValueError("pair table has missing/non-numeric target-rate rescue fields")

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
