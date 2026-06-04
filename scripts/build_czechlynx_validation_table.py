#!/usr/bin/env python3
"""Build the finalized CzechLynx pilot validation table."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINAL_TRIAGE_CSV = (
    PROJECT_ROOT / "data" / "labels" / "czechlynx" / "czechlynx_pilot_triage_final.csv"
)
INTERNAL_MAPPING_CSV = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_pilot_internal_with_ids.csv"
)
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_pilot_validation_table.csv"
)

EXPECTED_ROWS = 200
NEUTRAL_IMAGE_DIR = "data/interim/czechlynx/pilot_review_images/"

FINAL_REQUIRED_COLUMNS = [
    "pilot_image_id",
    "image_path",
    "triage_label",
    "blur_level",
    "occlusion_level",
    "lighting_condition",
    "night_ir_artifact",
    "visible_side",
    "side_comparability",
    "visible_region",
    "pattern_visibility",
    "body_fraction_visible",
    "distance_to_camera",
    "camera_angle",
    "reviewer_confidence",
    "uncertainty_flag",
    "exclusion_reason",
]

INTERNAL_REQUIRED_COLUMNS = [
    "pilot_image_id",
    "review_image_path",
    "unique_name",
    "date",
    "encounter",
    "source",
    "split-geo_aware",
    "split-time_open",
    "split-time_closed",
]

OUTPUT_COLUMNS = [
    "pilot_image_id",
    "image_path",
    "unique_name",
    "triage_label",
    "blur_level",
    "occlusion_level",
    "lighting_condition",
    "night_ir_artifact",
    "visible_side",
    "side_comparability",
    "visible_region",
    "pattern_visibility",
    "body_fraction_visible",
    "distance_to_camera",
    "camera_angle",
    "reviewer_confidence",
    "uncertainty_flag",
    "exclusion_reason",
    "date",
    "encounter",
    "source",
    "split-geo_aware",
    "split-time_open",
    "split-time_closed",
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


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def require_columns(df: pd.DataFrame, columns: list[str], source_name: str) -> list[str]:
    return [f"{source_name}:{column}" for column in columns if column not in df.columns]


def require_non_empty(df: pd.DataFrame, columns: list[str]) -> list[str]:
    missing: list[str] = []
    for column in columns:
        blanks = int((df[column] == "").sum())
        if blanks:
            missing.append(f"{column}: {blanks} blank value(s)")
    return missing


def path_points_to_neutral_image(path_text: str) -> bool:
    return NEUTRAL_IMAGE_DIR in path_text.replace("\\", "/")


def main() -> int:
    if not FINAL_TRIAGE_CSV.exists():
        return fail(f"final triage CSV not found: {FINAL_TRIAGE_CSV}")
    if not INTERNAL_MAPPING_CSV.exists():
        return fail(f"internal mapping CSV not found: {INTERNAL_MAPPING_CSV}")

    final = read_csv_clean(FINAL_TRIAGE_CSV)
    internal = read_csv_clean(INTERNAL_MAPPING_CSV)

    missing_columns = [
        *require_columns(final, FINAL_REQUIRED_COLUMNS, "final_triage"),
        *require_columns(internal, INTERNAL_REQUIRED_COLUMNS, "internal_mapping"),
    ]
    if missing_columns:
        return fail("missing required column(s): " + ", ".join(missing_columns))

    if final["pilot_image_id"].duplicated().any():
        return fail("final triage CSV contains duplicate pilot_image_id values")
    if internal["pilot_image_id"].duplicated().any():
        return fail("internal mapping CSV contains duplicate pilot_image_id values")

    labeled_rows = int((final["triage_label"] != "").sum())
    if labeled_rows != EXPECTED_ROWS:
        return fail(f"expected {EXPECTED_ROWS} finalized labels, found {labeled_rows}")

    joined = final.merge(
        internal[INTERNAL_REQUIRED_COLUMNS],
        on="pilot_image_id",
        how="inner",
        validate="one_to_one",
    )
    if len(joined) != EXPECTED_ROWS:
        return fail(f"join produced {len(joined)} rows; expected {EXPECTED_ROWS}")

    non_empty_required = [
        "pilot_image_id",
        "triage_label",
        "image_path",
        "unique_name",
        "review_image_path",
    ]
    missing_values = require_non_empty(joined, non_empty_required)
    if missing_values:
        return fail("required fields have missing values: " + "; ".join(missing_values))

    bad_paths = joined[
        ~joined["image_path"].map(path_points_to_neutral_image)
        | ~joined["review_image_path"].map(path_points_to_neutral_image)
    ]
    if not bad_paths.empty:
        return fail(
            f"{len(bad_paths)} row(s) do not use neutral pilot review image paths"
        )

    mismatched_paths = joined[joined["image_path"] != joined["review_image_path"]]
    if not mismatched_paths.empty:
        return fail(
            f"{len(mismatched_paths)} row(s) have image_path != review_image_path"
        )

    validation = joined[OUTPUT_COLUMNS].copy()
    VALIDATION_TABLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    validation.to_csv(VALIDATION_TABLE_CSV, index=False)

    images_per_id = validation["unique_name"].value_counts().sort_index()
    missing_output_values = {
        column: int((validation[column] == "").sum())
        for column in OUTPUT_COLUMNS
        if int((validation[column] == "").sum()) > 0
    }

    print("CzechLynx pilot validation table")
    print(f"Final triage CSV: {FINAL_TRIAGE_CSV}")
    print(f"Internal mapping CSV: {INTERNAL_MAPPING_CSV}")
    print(f"Wrote validation table: {VALIDATION_TABLE_CSV}")
    print()
    print("Summary")
    print("-------")
    print(f"Rows: {len(validation)}")
    print(f"Unique IDs: {validation['unique_name'].nunique()}")
    print("unique_name is used only after joining finalized triage labels.")
    print()
    print("Triage label counts:")
    for label, count in validation["triage_label"].value_counts().sort_index().items():
        print(f"  {label}: {count}")
    print()
    print("Images per ID summary:")
    print(f"  min: {int(images_per_id.min())}")
    print(f"  max: {int(images_per_id.max())}")
    print(f"  mean: {images_per_id.mean():.2f}")
    print("  distribution:")
    for image_count, id_count in images_per_id.value_counts().sort_index().items():
        print(f"    {image_count} image(s): {id_count} ID(s)")
    print()
    print("Missing values in output columns:")
    if missing_output_values:
        for column, count in missing_output_values.items():
            print(f"  {column}: {count}")
    else:
        print("  none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
