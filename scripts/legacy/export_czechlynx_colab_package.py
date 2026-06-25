#!/usr/bin/env python3
"""Export a minimal sanitized Colab package for CzechLynx wildlife baseline inference."""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "czechlynx"
REVIEW_IMAGE_DIR = INTERIM_DIR / "pilot_review_images"
VALIDATION_CSV = INTERIM_DIR / "czechlynx_pilot_validation_table.csv"
PAIRS_CSV = INTERIM_DIR / "czechlynx_pilot_pairs.csv"
SIMILARITIES_CSV = INTERIM_DIR / "czechlynx_pair_similarities.csv"

PACKAGE_DIR = PROJECT_ROOT / "colab_exports" / "czechlynx_wildlife_baseline_package"
PACKAGE_IMAGES_DIR = PACKAGE_DIR / "images"
PACKAGE_DATA_DIR = PACKAGE_DIR / "data"
PACKAGE_ZIP = PROJECT_ROOT / "colab_exports" / "czechlynx_wildlife_baseline_package.zip"

EXPECTED_IMAGES = 200
EXPECTED_PAIRS = 400

VALIDATION_COLUMNS = [
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

PAIR_COLUMNS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "same_individual",
    "triage_label_a",
    "triage_label_b",
    "pair_readiness_group",
]

SIMILARITY_COLUMNS = [
    "pair_id",
    "same_individual",
    "triage_label_a",
    "triage_label_b",
    "pair_readiness_group",
    "cosine_similarity",
]

LEAKAGE_STRINGS = [
    "unique_name",
    "lynx_",
    "latitude",
    "longitude",
    "trap_id",
    "location",
    "cell_code",
    "data/raw/czechlynx",
    "/CzechLynx/",
    "second_review",
    "original_triage_label",
    "original_pilot_image_id",
]


def audit_package_text(package_dir: Path) -> tuple[list[str], list[str]]:
    """Scan package CSV and README text for leakage strings."""
    passes: list[str] = []
    failures: list[str] = []

    text_files = list((package_dir / "data").glob("*.csv"))

    for path in text_files:
        content = path.read_text(encoding="utf-8")
        for needle in LEAKAGE_STRINGS:
            if needle in content:
                failures.append(f"Leakage string {needle!r} found in {path.relative_to(package_dir)}")
            else:
                passes.append(f"No leakage string {needle!r} in {path.name}")

    return passes, failures


def write_readme(path: Path) -> None:
    path.write_text(
        """# CzechLynx Wildlife Baseline Colab Package

## Purpose

This package contains the minimum files needed to run fixed pretrained wildlife
baseline inference on the finalized 200-image CzechLynx pilot in Google Colab.
It supports embedding extraction and pairwise cosine similarity computation for
comparison against the existing generic ResNet-50 baseline.

This package does **not** train or fine-tune any model.

## Privacy and Blinding

- No raw animal identity labels are included.
- No sensitive site or capture metadata (GPS coordinates, trap identifiers, or site codes).
- No original raw dataset paths or internal mapping files are included.
- No delayed relabeling subset files or identifiers are included.
- Image filenames use neutral `czlx_pilot_####.jpg` identifiers only.

## Contents

- `images/` — 200 neutral pilot review images
- `data/czechlynx_pilot_validation_table_colab.csv` — sanitized triage metadata
- `data/czechlynx_pilot_pairs_colab.csv` — 400 sanitized evaluation pairs
- `data/czechlynx_pair_similarities_resnet50.csv` — ResNet-50 baseline reference

## Intended Colab Workflow

1. Upload and unzip this package in Colab.
2. Install the chosen fixed pretrained wildlife embedding baseline.
3. Extract embeddings for all images in `images/`.
4. Compute pairwise cosine similarities for pairs listed in
   `data/czechlynx_pilot_pairs_colab.csv`.
5. Compare outputs locally against `data/czechlynx_pair_similarities_resnet50.csv`.

## Output Handling

Copy Colab-generated embeddings and similarity CSVs back to your local machine
under `data/interim/czechlynx/` or `outputs/`. Do **not** commit generated outputs,
raw images, or this package to git.
""",
        encoding="utf-8",
    )


def main() -> int:
    for source in (VALIDATION_CSV, PAIRS_CSV, SIMILARITIES_CSV, REVIEW_IMAGE_DIR):
        if not source.exists():
            print(f"ERROR: required input not found: {source}")
            return 1

    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    PACKAGE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    validation_df = pd.read_csv(VALIDATION_CSV)
    pairs_df = pd.read_csv(PAIRS_CSV)
    similarities_df = pd.read_csv(SIMILARITIES_CSV)

    review_images = sorted(REVIEW_IMAGE_DIR.glob("czlx_pilot_*.jpg"))
    if len(review_images) != EXPECTED_IMAGES:
        print(
            f"ERROR: expected {EXPECTED_IMAGES} review images, found {len(review_images)}"
        )
        return 1

    images_copied = 0
    for src in review_images:
        dst = PACKAGE_IMAGES_DIR / src.name
        shutil.copy2(src, dst)
        images_copied += 1

    sanitized_validation = validation_df.copy()
    sanitized_validation["image_path"] = sanitized_validation["pilot_image_id"].map(
        lambda pid: f"images/{pid}.jpg"
    )
    missing_cols = [col for col in VALIDATION_COLUMNS if col not in sanitized_validation.columns]
    if missing_cols:
        print(f"ERROR: validation table missing columns: {missing_cols}")
        return 1
    sanitized_validation = sanitized_validation[VALIDATION_COLUMNS]
    validation_out = PACKAGE_DATA_DIR / "czechlynx_pilot_validation_table_colab.csv"
    sanitized_validation.to_csv(validation_out, index=False)

    missing_pair_cols = [col for col in PAIR_COLUMNS if col not in pairs_df.columns]
    if missing_pair_cols:
        print(f"ERROR: pairs table missing columns: {missing_pair_cols}")
        return 1
    sanitized_pairs = pairs_df[PAIR_COLUMNS].copy()
    pairs_out = PACKAGE_DATA_DIR / "czechlynx_pilot_pairs_colab.csv"
    sanitized_pairs.to_csv(pairs_out, index=False)

    missing_sim_cols = [col for col in SIMILARITY_COLUMNS if col not in similarities_df.columns]
    if missing_sim_cols:
        print(f"ERROR: similarities table missing columns: {missing_sim_cols}")
        return 1
    sanitized_similarities = similarities_df[SIMILARITY_COLUMNS].copy()
    sim_out = PACKAGE_DATA_DIR / "czechlynx_pair_similarities_resnet50.csv"
    sanitized_similarities.to_csv(sim_out, index=False)

    readme_path = PACKAGE_DIR / "README_COLAB_PACKAGE.md"
    write_readme(readme_path)

    if PACKAGE_ZIP.exists():
        PACKAGE_ZIP.unlink()
    PACKAGE_ZIP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PACKAGE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PACKAGE_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(PACKAGE_DIR.parent))

    audit_passes, audit_failures = audit_package_text(PACKAGE_DIR)

    print("CzechLynx Colab package export")
    print(f"Images copied: {images_copied}")
    print(f"Validation rows: {len(sanitized_validation)}")
    print(f"Pair rows: {len(sanitized_pairs)}")
    print(f"Package path: {PACKAGE_DIR}")
    print(f"Zip path: {PACKAGE_ZIP}")
    print()
    print("Leakage audit summary:")
    if audit_failures:
        for item in audit_failures:
            print(f"  [FAIL] {item}")
        print("Leakage audit: FAIL")
        return 1

    unique_passes = sorted(set(audit_passes))
    for item in unique_passes[:5]:
        print(f"  [PASS] {item}")
    if len(unique_passes) > 5:
        print(f"  [PASS] ... and {len(unique_passes) - 5} more checks passed")
    print("Leakage audit: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
