#!/usr/bin/env python3
"""Prepare a blinded CzechLynx second-review subset."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINAL_CSV = PROJECT_ROOT / "data" / "labels" / "czechlynx" / "czechlynx_pilot_triage_final.csv"
LABEL_DIR = PROJECT_ROOT / "data" / "labels" / "czechlynx"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "czechlynx"
SECOND_REVIEW_IMAGE_DIR = INTERIM_DIR / "second_review_images"

BLINDED_CSV = LABEL_DIR / "czechlynx_second_review_blinded.csv"
INTERNAL_MAPPING_CSV = INTERIM_DIR / "czechlynx_second_review_internal_mapping.csv"

EXPECTED_LABELED_ROWS = 200
SAMPLE_PER_LABEL = 10
RANDOM_SEED = 20260604

TRIAGE_LABELS = ["review-ready", "review-limited", "unidentifiable"]

PILOT_COLUMNS = [
    "pilot_image_id",
    "dataset",
    "species_label",
    "source_role",
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
    "metadata_completeness",
    "reviewer_confidence",
    "uncertainty_flag",
    "exclusion_reason",
    "notes",
]

SECOND_REVIEW_COLUMNS = ["second_review_id", *PILOT_COLUMNS[1:]]
SECOND_REVIEW_LABEL_FIELDS = [
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
    "metadata_completeness",
    "reviewer_confidence",
    "uncertainty_flag",
    "exclusion_reason",
    "notes",
]

COMPARISON_FIELDS = [
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
    "metadata_completeness",
    "reviewer_confidence",
    "uncertainty_flag",
    "exclusion_reason",
    "notes",
]


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def resolve_project_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def main() -> int:
    if not FINAL_CSV.exists():
        return fail(f"final triage CSV not found: {FINAL_CSV}")

    df = pd.read_csv(FINAL_CSV, dtype=str, keep_default_na=False)
    missing_columns = [column for column in PILOT_COLUMNS if column not in df.columns]
    if missing_columns:
        return fail(f"missing required column(s): {', '.join(missing_columns)}")

    for column in PILOT_COLUMNS:
        df[column] = df[column].map(clean_cell)

    labeled = df[df["triage_label"] != ""].copy()
    if len(labeled) != EXPECTED_LABELED_ROWS:
        return fail(
            f"expected {EXPECTED_LABELED_ROWS} labeled rows, found {len(labeled)}"
        )

    invalid_labels = sorted(set(labeled["triage_label"]) - set(TRIAGE_LABELS))
    if invalid_labels:
        return fail(f"unexpected triage_label value(s): {', '.join(invalid_labels)}")

    sampled_parts: list[pd.DataFrame] = []
    for label in TRIAGE_LABELS:
        label_rows = labeled[labeled["triage_label"] == label]
        if len(label_rows) < SAMPLE_PER_LABEL:
            return fail(
                f"triage_label {label!r} has {len(label_rows)} row(s); "
                f"need at least {SAMPLE_PER_LABEL}"
            )
        sampled_parts.append(
            label_rows.sample(n=SAMPLE_PER_LABEL, random_state=RANDOM_SEED)
        )

    sample = (
        pd.concat(sampled_parts, ignore_index=True)
        .sample(frac=1, random_state=RANDOM_SEED + 1)
        .reset_index(drop=True)
    )
    sample["second_review_id"] = [
        f"czlx_second_{index:04d}" for index in range(len(sample))
    ]
    sample["second_review_filename"] = sample["second_review_id"] + ".jpg"
    sample["second_review_image_path"] = sample["second_review_filename"].map(
        lambda name: str(SECOND_REVIEW_IMAGE_DIR / name)
    )

    SECOND_REVIEW_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    LABEL_DIR.mkdir(parents=True, exist_ok=True)

    for _, row in sample.iterrows():
        src = resolve_project_path(row["image_path"])
        dst = Path(row["second_review_image_path"])
        if not src.exists():
            return fail(f"source review image not found: {src}")
        shutil.copy2(src, dst)

    mapping = pd.DataFrame(
        {
            "second_review_id": sample["second_review_id"],
            "second_review_image_path": sample["second_review_image_path"],
            "original_pilot_image_id": sample["pilot_image_id"],
            "original_triage_label": sample["triage_label"],
        }
    )
    for field in COMPARISON_FIELDS:
        if field == "triage_label":
            continue
        mapping[f"original_{field}"] = sample[field]
    mapping.to_csv(INTERNAL_MAPPING_CSV, index=False)

    blinded = sample[PILOT_COLUMNS].copy()
    blinded = blinded.rename(columns={"pilot_image_id": "second_review_id"})
    blinded["second_review_id"] = sample["second_review_id"]
    blinded["image_path"] = sample["second_review_image_path"]
    for field in SECOND_REVIEW_LABEL_FIELDS:
        blinded[field] = ""
    blinded = blinded[SECOND_REVIEW_COLUMNS]
    blinded.to_csv(BLINDED_CSV, index=False)

    print(f"Read final triage labels: {FINAL_CSV}")
    print(f"Selected {len(sample)} second-review rows:")
    for label in TRIAGE_LABELS:
        count = int((sample["triage_label"] == label).sum())
        print(f"  {label}: {count}")
    print(f"Wrote second-review images to: {SECOND_REVIEW_IMAGE_DIR}")
    print(f"Wrote internal mapping: {INTERNAL_MAPPING_CSV}")
    print(f"Wrote blinded label CSV: {BLINDED_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
