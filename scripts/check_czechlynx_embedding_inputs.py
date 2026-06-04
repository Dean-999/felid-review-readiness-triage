#!/usr/bin/env python3
"""Check CzechLynx Phase 2 inputs before any embedding execution."""

from __future__ import annotations

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

EXPECTED_VALIDATION_ROWS = 200
EXPECTED_PAIR_ROWS = 400
EXPECTED_SAME_PAIRS = 100
EXPECTED_DIFFERENT_PAIRS = 300

VALIDATION_REQUIRED_COLUMNS = [
    "pilot_image_id",
    "image_path",
    "triage_label",
]
PAIR_REQUIRED_COLUMNS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "image_path_a",
    "image_path_b",
    "same_individual",
    "pair_readiness_group",
]


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_csv_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in df.columns:
        df[column] = df[column].map(clean_cell)
    return df


def resolve_project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def add_count_check(
    passes: list[str],
    failures: list[str],
    label: str,
    actual: int,
    expected: int,
) -> None:
    if actual == expected:
        passes.append(f"{label} is exactly {expected}.")
    else:
        failures.append(f"{label} is {actual}; expected {expected}.")


def main() -> int:
    failures: list[str] = []
    passes: list[str] = []

    if not VALIDATION_TABLE_CSV.exists():
        print(f"FAIL: validation table not found: {VALIDATION_TABLE_CSV}")
        return 1
    if not PAIR_CSV.exists():
        print(f"FAIL: pair file not found: {PAIR_CSV}")
        return 1

    validation = read_csv_clean(VALIDATION_TABLE_CSV)
    pairs = read_csv_clean(PAIR_CSV)

    missing_validation_columns = [
        column for column in VALIDATION_REQUIRED_COLUMNS if column not in validation.columns
    ]
    missing_pair_columns = [
        column for column in PAIR_REQUIRED_COLUMNS if column not in pairs.columns
    ]

    if missing_validation_columns:
        failures.append(
            "Validation table missing required column(s): "
            + ", ".join(missing_validation_columns)
        )
    else:
        passes.append("Validation table has required columns.")

    if missing_pair_columns:
        failures.append(
            "Pair file missing required column(s): " + ", ".join(missing_pair_columns)
        )
    else:
        passes.append("Pair file has required columns.")

    if not failures:
        add_count_check(
            passes,
            failures,
            "Validation table row count",
            len(validation),
            EXPECTED_VALIDATION_ROWS,
        )
        add_count_check(
            passes,
            failures,
            "Pair file row count",
            len(pairs),
            EXPECTED_PAIR_ROWS,
        )

        same_count = int((pairs["same_individual"] == "True").sum())
        different_count = int((pairs["same_individual"] == "False").sum())
        add_count_check(
            passes,
            failures,
            "Same-individual pair count",
            same_count,
            EXPECTED_SAME_PAIRS,
        )
        add_count_check(
            passes,
            failures,
            "Different-individual pair count",
            different_count,
            EXPECTED_DIFFERENT_PAIRS,
        )

        validation_ids = set(validation["pilot_image_id"])
        pair_ids = set(pairs["image_id_a"]) | set(pairs["image_id_b"])
        missing_ids = sorted(pair_ids - validation_ids)
        if missing_ids:
            failures.append(
                f"{len(missing_ids)} pair image ID(s) missing from validation table."
            )
            for image_id in missing_ids[:10]:
                failures.append(f"  missing image ID: {image_id}")
        else:
            passes.append("All pair image IDs exist in the validation table.")

        image_paths = set(validation["image_path"]) | set(pairs["image_path_a"]) | set(
            pairs["image_path_b"]
        )
        missing_paths = sorted(
            path_text for path_text in image_paths if not resolve_project_path(path_text).exists()
        )
        if missing_paths:
            failures.append(f"{len(missing_paths)} referenced image path(s) are missing.")
            for path_text in missing_paths[:10]:
                failures.append(f"  missing image path: {path_text}")
        else:
            passes.append("All referenced image paths exist.")

    print("CzechLynx embedding input audit")
    print(f"Validation table: {VALIDATION_TABLE_CSV}")
    print(f"Pair file: {PAIR_CSV}")
    print()
    print("Label counts:")
    if "triage_label" in validation.columns:
        for label, count in validation["triage_label"].value_counts().sort_index().items():
            print(f"  {label}: {count}")
    else:
        print("  unavailable; triage_label column missing")
    print()
    print("Pair readiness group counts:")
    if "pair_readiness_group" in pairs.columns:
        for group, count in pairs["pair_readiness_group"].value_counts().sort_index().items():
            print(f"  {group}: {count}")
    else:
        print("  unavailable; pair_readiness_group column missing")
    print()

    if passes:
        print("PASS checks:")
        for item in passes:
            print(f"  [PASS] {item}")
        print()

    if failures:
        print("FAIL checks:")
        for item in failures:
            print(f"  [FAIL] {item}")
        print()
        print("RESULT: FAIL")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
