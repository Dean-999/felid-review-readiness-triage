#!/usr/bin/env python3
"""Build Phase 16 laterality-aware pair comparability outputs.

Laterality is a data-governance diagnostic, not the core PF-ERI contribution.
This script makes side comparability explicit so downstream PF-ERI evidence
routing can report known-side and unknown-side behavior separately.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "outputs/phase14/phase14_algorithm_inputs/phase14_2x2_pair_comparability_table.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/laterality_aware_pair_audit"
OUTPUT_TABLE = OUTPUT_DIR / "phase16_laterality_aware_pair_table.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "phase16_laterality_aware_pair_summary.csv"
OUTPUT_AUDIT = OUTPUT_DIR / "phase16_laterality_aware_pair_audit.json"

KNOWN_LATERALITY = {"left", "right", "both", "frontal", "rear", "unknown"}
NON_LATERAL = {"frontal", "rear"}


def normalize_laterality(value: object) -> str:
    """Normalize raw laterality labels to the Phase 16 controlled vocabulary."""
    if value is None:
        return "unknown"
    if isinstance(value, float) and math.isnan(value):
        return "unknown"
    text = str(value).strip().lower()
    if text in KNOWN_LATERALITY:
        return text
    return "unknown"


def pair_side_relation(query_side: object, candidate_side: object) -> str:
    """Classify pair-level side comparability from two laterality labels."""
    query = normalize_laterality(query_side)
    candidate = normalize_laterality(candidate_side)
    if query == "unknown" or candidate == "unknown":
        return "one_or_both_unknown"
    if query in NON_LATERAL or candidate in NON_LATERAL:
        return "non_lateral"
    if query == "both" or candidate == "both":
        return "same_side_or_both"
    if query == candidate:
        return "same_side"
    return "opposite_side"


def relation_penalty(relation: str) -> float:
    """Small diagnostic penalty used only for laterality-aware reporting."""
    penalties = {
        "same_side": 0.00,
        "same_side_or_both": 0.03,
        "opposite_side": 0.18,
        "one_or_both_unknown": 0.08,
        "non_lateral": 0.22,
    }
    return penalties[relation]


def _normalized_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(["unknown"] * len(df), index=df.index)
    return df[column].map(normalize_laterality)


def build(input_path: Path = DEFAULT_INPUT) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    pairs = pd.read_csv(input_path, low_memory=False)
    required = {
        "phase14_pair_id",
        "pair_block",
        "environment_axis",
        "species_axis",
        "pair_comparability_score",
    }
    missing = sorted(required - set(pairs.columns))
    if missing:
        raise ValueError(f"Missing required columns in {input_path}: {missing}")

    pairs["phase16_query_laterality"] = _normalized_column(pairs, "query_side_raw")
    pairs["phase16_candidate_laterality"] = _normalized_column(pairs, "candidate_side_raw")
    pairs["phase16_pair_side_relation"] = [
        pair_side_relation(query, candidate)
        for query, candidate in zip(
            pairs["phase16_query_laterality"],
            pairs["phase16_candidate_laterality"],
        )
    ]
    pairs["phase16_laterality_penalty"] = pairs["phase16_pair_side_relation"].map(relation_penalty)
    base_score = pd.to_numeric(pairs["pair_comparability_score"], errors="coerce").fillna(0.0)
    pairs["phase16_laterality_adjusted_pair_score"] = (
        base_score - pairs["phase16_laterality_penalty"]
    ).clip(0.0, 1.0)
    pairs["phase16_laterality_known_pair"] = ~pairs["phase16_pair_side_relation"].eq(
        "one_or_both_unknown"
    )

    group_cols = [
        "environment_axis",
        "species_axis",
        "pair_block",
        "phase16_pair_side_relation",
    ]
    summary = (
        pairs.groupby(group_cols, dropna=False)
        .agg(
            pair_count=("phase14_pair_id", "count"),
            mean_original_pair_score=("pair_comparability_score", "mean"),
            mean_laterality_adjusted_pair_score=(
                "phase16_laterality_adjusted_pair_score",
                "mean",
            ),
            known_side_rate=("phase16_laterality_known_pair", "mean"),
        )
        .reset_index()
    )

    audit = {
        "input": str(input_path),
        "output_table": str(OUTPUT_TABLE),
        "output_summary": str(OUTPUT_SUMMARY),
        "rows": int(len(pairs)),
        "laterality_relation_counts": {
            str(key): int(value)
            for key, value in pairs["phase16_pair_side_relation"].value_counts(dropna=False).items()
        },
        "known_side_pair_rate": float(pairs["phase16_laterality_known_pair"].mean()),
        "claim_boundary": (
            "laterality is a sampling and pair-audit diagnostic around PF-ERI; "
            "it is not the core algorithmic contribution"
        ),
    }
    return pairs, summary, audit


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs, summary, audit = build()
    pairs.to_csv(OUTPUT_TABLE, index=False)
    summary.to_csv(OUTPUT_SUMMARY, index=False)
    OUTPUT_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"PASS phase16 laterality-aware pair audit rows={audit['rows']}")
    print(f"WROTE {OUTPUT_TABLE}")


if __name__ == "__main__":
    main()
