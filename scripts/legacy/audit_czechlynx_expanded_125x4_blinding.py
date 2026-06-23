#!/usr/bin/env python3
"""Audit the expanded CzechLynx 125x4 blinded review package."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "czechlynx"
LABEL_DIR = PROJECT_ROOT / "data" / "labels" / "czechlynx"
QC_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "qc"

BLINDED_CSV = LABEL_DIR / "czechlynx_expanded_125x4_triage_blinded.csv"
INTERNAL_CSV = INTERIM_DIR / "czechlynx_expanded_125x4_internal_with_ids.csv"
PILOT_INTERNAL_CSV = INTERIM_DIR / "czechlynx_pilot_internal_with_ids.csv"
REPORT_TXT = QC_DIR / "czechlynx_expanded_125x4_blinding_audit.txt"

EXPECTED_ROWS = 500
EXPECTED_IDS = 125
EXPECTED_IMAGES_PER_ID = 4
REVIEW_IMAGE_DIR = "data/interim/czechlynx/expanded_125x4_review_images/"
REVIEW_FILENAME_PATTERN = re.compile(r"^czlx_expanded_\d{4}\.jpg$")
EXPECTED_ID_PATTERN = re.compile(r"^czlx_expanded_\d{4}$")

BLINDED_REQUIRED_COLUMNS = [
    "expanded_image_id",
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
INTERNAL_REQUIRED_COLUMNS = [
    "expanded_image_id",
    "review_image_filename",
    "review_image_path",
    "working_individual_id",
    "path",
    "local_image_path",
]
PILOT_REQUIRED_COLUMNS = ["path", "local_image_path"]

LEAKAGE_STRINGS = [
    "working_individual_id",
    "unique_name",
    "lynx_",
    "latitude",
    "longitude",
    "trap_id",
    "location",
    "cell_code",
    "/CzechLynx/",
    "data/raw/czechlynx",
    "second_review",
    "original_triage_label",
    "original_pilot_image_id",
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


def add_result(condition: bool, passes: list[str], failures: list[str], message: str) -> None:
    if condition:
        passes.append(message)
    else:
        failures.append(message)


def write_report(passes: list[str], failures: list[str]) -> None:
    lines = [
        "CzechLynx expanded 125x4 blinding audit",
        "=========================================",
        f"Blinded CSV: {BLINDED_CSV}",
        f"Internal mapping: {INTERNAL_CSV}",
        "",
    ]
    if passes:
        lines.append("PASS checks:")
        lines.extend(f"  [PASS] {item}" for item in passes)
        lines.append("")
    if failures:
        lines.append("FAIL checks:")
        lines.extend(f"  [FAIL] {item}" for item in failures)
        lines.append("")
        lines.append("RESULT: FAIL")
    else:
        lines.append("RESULT: PASS")

    QC_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> int:
    passes: list[str] = []
    failures: list[str] = []

    missing_files = [
        path
        for path in (BLINDED_CSV, INTERNAL_CSV, PILOT_INTERNAL_CSV)
        if not path.exists()
    ]
    if missing_files:
        failures.extend(f"required file not found: {path}" for path in missing_files)
        write_report(passes, failures)
        return 1

    blinded = read_csv_clean(BLINDED_CSV)
    internal = read_csv_clean(INTERNAL_CSV)
    pilot = read_csv_clean(PILOT_INTERNAL_CSV)

    missing_blinded = [c for c in BLINDED_REQUIRED_COLUMNS if c not in blinded.columns]
    missing_internal = [c for c in INTERNAL_REQUIRED_COLUMNS if c not in internal.columns]
    missing_pilot = [c for c in PILOT_REQUIRED_COLUMNS if c not in pilot.columns]
    add_result(
        not missing_blinded,
        passes,
        failures,
        "Blinded CSV has all required columns."
        if not missing_blinded
        else "Blinded CSV missing required column(s): " + ", ".join(missing_blinded),
    )
    add_result(
        not missing_internal,
        passes,
        failures,
        "Internal mapping has all required columns."
        if not missing_internal
        else "Internal mapping missing required column(s): " + ", ".join(missing_internal),
    )
    add_result(
        not missing_pilot,
        passes,
        failures,
        "Current pilot internal map has required overlap-audit columns."
        if not missing_pilot
        else "Current pilot map missing required column(s): " + ", ".join(missing_pilot),
    )
    if missing_blinded or missing_internal or missing_pilot:
        write_report(passes, failures)
        return 1

    add_result(
        len(blinded) == EXPECTED_ROWS,
        passes,
        failures,
        f"Blinded CSV row count is {len(blinded)}; expected {EXPECTED_ROWS}.",
    )
    add_result(
        len(internal) == EXPECTED_ROWS,
        passes,
        failures,
        f"Internal mapping row count is {len(internal)}; expected {EXPECTED_ROWS}.",
    )

    unique_id_count = int(internal["working_individual_id"].nunique())
    add_result(
        unique_id_count == EXPECTED_IDS,
        passes,
        failures,
        f"Internal mapping has {unique_id_count} working IDs; expected {EXPECTED_IDS}.",
    )
    images_per_id = internal["working_individual_id"].value_counts()
    bad_id_counts = images_per_id[images_per_id != EXPECTED_IMAGES_PER_ID]
    add_result(
        bad_id_counts.empty,
        passes,
        failures,
        f"All working IDs have exactly {EXPECTED_IMAGES_PER_ID} image(s)."
        if bad_id_counts.empty
        else f"{len(bad_id_counts)} working ID(s) do not have exactly {EXPECTED_IMAGES_PER_ID} images.",
    )

    add_result(
        not blinded["expanded_image_id"].duplicated().any(),
        passes,
        failures,
        "Blinded expanded_image_id values are unique.",
    )
    add_result(
        not internal["expanded_image_id"].duplicated().any(),
        passes,
        failures,
        "Internal expanded_image_id values are unique.",
    )
    add_result(
        set(blinded["expanded_image_id"]) == set(internal["expanded_image_id"]),
        passes,
        failures,
        "Blinded and internal expanded_image_id sets match.",
    )

    bad_ids = [
        image_id
        for image_id in blinded["expanded_image_id"]
        if not EXPECTED_ID_PATTERN.match(image_id)
    ]
    add_result(
        not bad_ids,
        passes,
        failures,
        "All expanded_image_id values match czlx_expanded_####."
        if not bad_ids
        else f"{len(bad_ids)} expanded_image_id value(s) have invalid format.",
    )

    bad_path_prefix: list[str] = []
    missing_images: list[str] = []
    bad_filenames: list[str] = []
    for image_path in blinded["image_path"]:
        normalized = image_path.replace("\\", "/")
        if not normalized.startswith(REVIEW_IMAGE_DIR):
            bad_path_prefix.append(image_path)
            continue

        resolved = resolve_project_path(image_path)
        if not resolved.exists():
            missing_images.append(str(resolved))
        if not REVIEW_FILENAME_PATTERN.match(resolved.name):
            bad_filenames.append(resolved.name)

    add_result(
        not bad_path_prefix,
        passes,
        failures,
        f"All blinded image paths point to {REVIEW_IMAGE_DIR}."
        if not bad_path_prefix
        else f"{len(bad_path_prefix)} blinded image path(s) do not point to {REVIEW_IMAGE_DIR}.",
    )
    add_result(
        not missing_images,
        passes,
        failures,
        "All referenced expanded review images exist."
        if not missing_images
        else f"{len(missing_images)} referenced expanded review image(s) are missing.",
    )
    add_result(
        not bad_filenames,
        passes,
        failures,
        "All review image filenames match czlx_expanded_####.jpg."
        if not bad_filenames
        else f"{len(bad_filenames)} review image filename(s) have invalid format.",
    )

    pilot_paths = set(pilot["path"])
    pilot_local_paths = set(pilot["local_image_path"])
    path_overlap = int(internal["path"].isin(pilot_paths).sum())
    local_path_overlap = int(internal["local_image_path"].isin(pilot_local_paths).sum())
    add_result(
        path_overlap == 0,
        passes,
        failures,
        f"Current 200 pilot path overlap count is {path_overlap}.",
    )
    add_result(
        local_path_overlap == 0,
        passes,
        failures,
        f"Current 200 pilot local_image_path overlap count is {local_path_overlap}.",
    )

    csv_text = BLINDED_CSV.read_text(encoding="utf-8")
    for needle in LEAKAGE_STRINGS:
        found = needle in csv_text
        add_result(
            not found,
            passes,
            failures,
            f"No leakage string in blinded CSV: {needle!r}"
            if not found
            else f"Leakage string found in blinded CSV: {needle!r}",
        )

    write_report(passes, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
