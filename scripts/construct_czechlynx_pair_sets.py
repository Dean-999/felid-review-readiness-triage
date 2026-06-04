#!/usr/bin/env python3
"""Construct CzechLynx pilot same/different individual pair sets."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_pilot_validation_table.csv"
)
PAIR_CSV = PROJECT_ROOT / "data" / "interim" / "czechlynx" / "czechlynx_pilot_pairs.csv"

DIFFERENT_PAIR_SAMPLE_SIZE = 300
RANDOM_SEED = 20260604

REQUIRED_COLUMNS = [
    "pilot_image_id",
    "image_path",
    "unique_name",
    "triage_label",
    "visible_side",
    "side_comparability",
    "pattern_visibility",
]

READINESS_GROUPS = {
    frozenset(("review-ready", "review-ready")): "ready_ready",
    frozenset(("review-ready", "review-limited")): "ready_limited",
    frozenset(("review-ready", "unidentifiable")): "ready_unidentifiable",
    frozenset(("review-limited", "review-limited")): "limited_limited",
    frozenset(("review-limited", "unidentifiable")): "limited_unidentifiable",
    frozenset(("unidentifiable", "unidentifiable")): "unidentifiable_unidentifiable",
}


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_csv_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in df.columns:
        df[column] = df[column].map(clean_cell)
    return df


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def pair_readiness_group(label_a: str, label_b: str) -> str:
    labels = frozenset((label_a, label_b))
    if labels not in READINESS_GROUPS:
        raise ValueError(f"Unexpected triage_label pair: {label_a!r}, {label_b!r}")
    return READINESS_GROUPS[labels]


def build_pair(row_a: pd.Series, row_b: pd.Series, same_individual: bool) -> dict[str, object]:
    return {
        "image_id_a": row_a["pilot_image_id"],
        "image_id_b": row_b["pilot_image_id"],
        "image_path_a": row_a["image_path"],
        "image_path_b": row_b["image_path"],
        "unique_name_a": row_a["unique_name"],
        "unique_name_b": row_b["unique_name"],
        "same_individual": same_individual,
        "triage_label_a": row_a["triage_label"],
        "triage_label_b": row_b["triage_label"],
        "pair_readiness_group": pair_readiness_group(
            row_a["triage_label"], row_b["triage_label"]
        ),
        "visible_side_a": row_a["visible_side"],
        "visible_side_b": row_b["visible_side"],
        "side_comparability_a": row_a["side_comparability"],
        "side_comparability_b": row_b["side_comparability"],
        "pattern_visibility_a": row_a["pattern_visibility"],
        "pattern_visibility_b": row_b["pattern_visibility"],
    }


def main() -> int:
    if not VALIDATION_TABLE_CSV.exists():
        return fail(f"validation table not found: {VALIDATION_TABLE_CSV}")

    df = read_csv_clean(VALIDATION_TABLE_CSV)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        return fail("missing required column(s): " + ", ".join(missing_columns))

    if df["pilot_image_id"].duplicated().any():
        return fail("validation table contains duplicate pilot_image_id values")

    same_pairs: list[dict[str, object]] = []
    for _, group in df.groupby("unique_name", sort=True):
        rows = list(group.sort_values("pilot_image_id").iterrows())
        for (_, row_a), (_, row_b) in itertools.combinations(rows, 2):
            same_pairs.append(build_pair(row_a, row_b, same_individual=True))

    different_pairs: list[dict[str, object]] = []
    rows = list(df.sort_values("pilot_image_id").iterrows())
    for (_, row_a), (_, row_b) in itertools.combinations(rows, 2):
        if row_a["unique_name"] == row_b["unique_name"]:
            continue
        different_pairs.append(build_pair(row_a, row_b, same_individual=False))

    different = pd.DataFrame(different_pairs)
    sample_size = min(DIFFERENT_PAIR_SAMPLE_SIZE, len(different))
    sampled_different = different.sample(
        n=sample_size,
        random_state=RANDOM_SEED,
    )

    pairs = pd.concat([pd.DataFrame(same_pairs), sampled_different], ignore_index=True)
    pairs = pairs.sample(frac=1, random_state=RANDOM_SEED + 1).reset_index(drop=True)
    pairs.insert(0, "pair_id", [f"czlx_pair_{index:05d}" for index in range(len(pairs))])
    pairs.to_csv(PAIR_CSV, index=False)

    same_count = int((pairs["same_individual"] == True).sum())
    different_count = int((pairs["same_individual"] == False).sum())

    print("CzechLynx pilot pair set")
    print(f"Validation table: {VALIDATION_TABLE_CSV}")
    print(f"Wrote pair file: {PAIR_CSV}")
    print()
    print("Summary")
    print("-------")
    print(f"Total pairs: {len(pairs)}")
    print(f"Same-individual pairs: {same_count}")
    print(f"Different-individual pairs: {different_count}")
    print(f"Available different-individual pairs: {len(different)}")
    print(f"Sampled different-individual pairs: {sample_size}")
    print()
    print("Pair readiness group counts:")
    for group, count in pairs["pair_readiness_group"].value_counts().sort_index().items():
        print(f"  {group}: {count}")
    print()
    print("Same/different counts by readiness group:")
    summary = pd.crosstab(
        pairs["pair_readiness_group"],
        pairs["same_individual"].map({True: "same", False: "different"}),
    )
    for group in sorted(pairs["pair_readiness_group"].unique()):
        same = int(summary.loc[group].get("same", 0)) if group in summary.index else 0
        different_count_for_group = (
            int(summary.loc[group].get("different", 0)) if group in summary.index else 0
        )
        print(f"  {group}: same={same}, different={different_count_for_group}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
