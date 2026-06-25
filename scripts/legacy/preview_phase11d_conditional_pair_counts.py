#!/usr/bin/env python3
"""Preview Phase 11D conditional rescue and soft-negative pair counts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv"
OUT = PROJECT_ROOT / (
    "outputs/czechlynx/phase11d/evidence_conditional_pair_weighting/"
    "phase11d_conditional_pair_count_preview.csv"
)
BASE_GROUP = "H3_pf_eri_quality_hybrid_matched_identity"


def pct(count: int, total: int) -> float:
    return float(count / total) if total else 0.0


def summarize_split(frame: pd.DataFrame, split_id: int) -> list[dict[str, object]]:
    split = frame[(frame["split_id"].astype(int) == split_id) & (frame["group_name"].astype(str) == BASE_GROUP)].copy()
    if split.empty:
        raise ValueError(f"no pair rows for split={split_id} group={BASE_GROUP}")
    split["same_identity_bool"] = split["same_identity"].astype(str).str.lower().isin(["true", "1", "yes"])
    positive = split[split["same_identity_bool"]].copy()
    negative = split[~split["same_identity_bool"]].copy()
    rows: list[dict[str, object]] = []
    for q in [0.75, 0.85]:
        threshold = float(positive["descriptor_similarity"].quantile(q))
        rescued = positive[
            (positive["pair_reliability_score"] < 0.40)
            & (positive["descriptor_similarity"] >= threshold)
            & (positive["pattern_pair_score"] >= 0.45)
        ].copy()
        rows.append(
            {
                "split_id": split_id,
                "condition_name": f"positive_rescue_q{int(q * 100)}_floor035",
                "base_group_name": BASE_GROUP,
                "total_positive_pairs": int(len(positive)),
                "rescued_positive_pairs": int(len(rescued)),
                "pct_rescued_positive_pairs": pct(len(rescued), len(positive)),
                "positive_similarity_threshold": threshold,
                "mean_r_rescued_positives": float(rescued["pair_reliability_score"].mean()) if len(rescued) else float("nan"),
                "mean_descriptor_similarity_rescued_positives": float(rescued["descriptor_similarity"].mean()) if len(rescued) else float("nan"),
                "mean_pattern_pair_score_rescued_positives": float(rescued["pattern_pair_score"].mean()) if len(rescued) else float("nan"),
                "total_negative_pairs": int(len(negative)),
                "soft_negative_pairs": 0,
                "pct_soft_negative_pairs": 0.0,
                "negative_similarity_threshold": float("nan"),
                "mean_r_soft_negatives": float("nan"),
                "mean_descriptor_similarity_soft_negatives": float("nan"),
            }
        )
    neg_threshold = float(negative["descriptor_similarity"].quantile(0.95))
    soft = negative[(negative["descriptor_similarity"] >= neg_threshold) & (negative["pair_reliability_score"] <= 0.40)].copy()
    rows.append(
        {
            "split_id": split_id,
            "condition_name": "soft_negative_q95_r_lte_040_w085",
            "base_group_name": BASE_GROUP,
            "total_positive_pairs": int(len(positive)),
            "rescued_positive_pairs": 0,
            "pct_rescued_positive_pairs": 0.0,
            "positive_similarity_threshold": float("nan"),
            "mean_r_rescued_positives": float("nan"),
            "mean_descriptor_similarity_rescued_positives": float("nan"),
            "mean_pattern_pair_score_rescued_positives": float("nan"),
            "total_negative_pairs": int(len(negative)),
            "soft_negative_pairs": int(len(soft)),
            "pct_soft_negative_pairs": pct(len(soft), len(negative)),
            "negative_similarity_threshold": neg_threshold,
            "mean_r_soft_negatives": float(soft["pair_reliability_score"].mean()) if len(soft) else float("nan"),
            "mean_descriptor_similarity_soft_negatives": float(soft["descriptor_similarity"].mean()) if len(soft) else float("nan"),
        }
    )
    return rows


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
        raise ValueError("pair table has missing/non-numeric conditional logic fields")
    rows: list[dict[str, object]] = []
    for split_id in [1, 3]:
        rows.extend(summarize_split(pair_table, split_id))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(PROJECT_ROOT)} rows={len(rows)}")


if __name__ == "__main__":
    main()
