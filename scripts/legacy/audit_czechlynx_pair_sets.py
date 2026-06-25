#!/usr/bin/env python3
"""Audit CzechLynx pilot validation pair sets."""

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

VALIDATION_REQUIRED_COLUMNS = ["pilot_image_id", "image_path", "unique_name"]
PAIR_REQUIRED_COLUMNS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "image_path_a",
    "image_path_b",
    "unique_name_a",
    "unique_name_b",
    "same_individual",
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

    if failures:
        print_report(passes, failures)
        return 1

    validation_by_id = validation.set_index("pilot_image_id")
    valid_ids = set(validation_by_id.index)
    pair_ids = set(pairs["image_id_a"]) | set(pairs["image_id_b"])
    missing_ids = sorted(pair_ids - valid_ids)
    if missing_ids:
        failures.append(f"{len(missing_ids)} pair image ID(s) missing from validation table.")
        for image_id in missing_ids[:10]:
            failures.append(f"  missing image ID: {image_id}")
    else:
        passes.append("All pair image IDs exist in the validation table.")

    bad_same_values = sorted(set(pairs["same_individual"]) - {"True", "False"})
    if bad_same_values:
        failures.append(
            "same_individual has invalid value(s): " + ", ".join(bad_same_values)
        )
    else:
        passes.append("same_individual values are True/False.")

    same_logic_failures: list[str] = []
    different_logic_failures: list[str] = []
    path_failures: list[str] = []
    validation_path_mismatches: list[str] = []

    for _, row in pairs.iterrows():
        pair_id = row["pair_id"]
        same_flag = row["same_individual"]
        same_names = row["unique_name_a"] == row["unique_name_b"]

        if same_flag == "True" and not same_names:
            same_logic_failures.append(
                f"{pair_id}: same_individual=True but unique names differ"
            )
        if same_flag == "False" and same_names:
            different_logic_failures.append(
                f"{pair_id}: same_individual=False but unique names match"
            )

        for side in ("a", "b"):
            image_id = row[f"image_id_{side}"]
            image_path = row[f"image_path_{side}"]
            if image_id in valid_ids:
                expected_path = validation_by_id.loc[image_id, "image_path"]
                expected_name = validation_by_id.loc[image_id, "unique_name"]
                if image_path != expected_path:
                    validation_path_mismatches.append(
                        f"{pair_id}: image_path_{side} does not match validation table"
                    )
                if row[f"unique_name_{side}"] != expected_name:
                    validation_path_mismatches.append(
                        f"{pair_id}: unique_name_{side} does not match validation table"
                    )
            if not resolve_project_path(image_path).exists():
                path_failures.append(f"{pair_id}: missing image_path_{side}: {image_path}")

    if same_logic_failures:
        failures.append(
            f"{len(same_logic_failures)} same-individual pair(s) have mismatched IDs."
        )
        failures.extend(f"  {item}" for item in same_logic_failures[:10])
    else:
        passes.append("same_individual=True only when unique_name_a == unique_name_b.")

    if different_logic_failures:
        failures.append(
            f"{len(different_logic_failures)} different-individual pair(s) have matching IDs."
        )
        failures.extend(f"  {item}" for item in different_logic_failures[:10])
    else:
        passes.append("same_individual=False only when unique_name_a != unique_name_b.")

    unordered_keys = pairs.apply(
        lambda row: tuple(sorted((row["image_id_a"], row["image_id_b"]))),
        axis=1,
    )
    duplicate_count = int(unordered_keys.duplicated().sum())
    self_pair_count = int((pairs["image_id_a"] == pairs["image_id_b"]).sum())
    if duplicate_count:
        failures.append(f"{duplicate_count} duplicate unordered pair(s) found.")
    else:
        passes.append("No duplicate unordered pairs found.")
    if self_pair_count:
        failures.append(f"{self_pair_count} self-pair(s) found.")
    else:
        passes.append("No self-pairs found.")

    if path_failures:
        failures.append(f"{len(path_failures)} pair image path(s) do not exist.")
        failures.extend(f"  {item}" for item in path_failures[:10])
    else:
        passes.append("All pair image paths exist.")

    if validation_path_mismatches:
        failures.append(
            f"{len(validation_path_mismatches)} pair field(s) do not match validation table."
        )
        failures.extend(f"  {item}" for item in validation_path_mismatches[:10])
    else:
        passes.append("Pair image paths and unique names match the validation table.")

    print_report(passes, failures)
    return 1 if failures else 0


def print_report(passes: list[str], failures: list[str]) -> None:
    print("CzechLynx pilot pair-set audit")
    print(f"Validation table: {VALIDATION_TABLE_CSV}")
    print(f"Pair file: {PAIR_CSV}")
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
    else:
        print("RESULT: PASS")


if __name__ == "__main__":
    sys.exit(main())
