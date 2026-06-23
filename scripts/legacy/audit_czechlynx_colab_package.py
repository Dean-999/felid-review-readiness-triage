#!/usr/bin/env python3
"""Audit CzechLynx Colab package for completeness and blinding compliance."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "colab_exports" / "czechlynx_wildlife_baseline_package"
IMAGES_DIR = PACKAGE_DIR / "images"
VALIDATION_CSV = PACKAGE_DIR / "data" / "czechlynx_pilot_validation_table_colab.csv"
PAIRS_CSV = PACKAGE_DIR / "data" / "czechlynx_pilot_pairs_colab.csv"

EXPECTED_IMAGES = 200
EXPECTED_VALIDATION_ROWS = 200
EXPECTED_PAIR_ROWS = 400

IMAGE_FILENAME_PATTERN = re.compile(r"^czlx_pilot_\d{4}\.jpg$")

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

    if not PACKAGE_DIR.exists():
        print(f"FAIL: package directory not found: {PACKAGE_DIR}")
        print("RESULT: FAIL")
        return 1

    images = sorted(IMAGES_DIR.glob("*.jpg")) if IMAGES_DIR.exists() else []
    add_count_check(
        passes,
        failures,
        "Image count",
        len(images),
        EXPECTED_IMAGES,
    )

    bad_filenames = [img.name for img in images if not IMAGE_FILENAME_PATTERN.match(img.name)]
    if bad_filenames:
        failures.append(
            f"{len(bad_filenames)} image filename(s) do not match czlx_pilot_####.jpg."
        )
        for name in bad_filenames[:5]:
            failures.append(f"  invalid filename: {name}")
    else:
        passes.append("All image filenames match czlx_pilot_####.jpg.")

    if not VALIDATION_CSV.exists():
        failures.append(f"Validation CSV not found: {VALIDATION_CSV}")
        validation_df = pd.DataFrame()
    else:
        validation_df = pd.read_csv(VALIDATION_CSV)
        add_count_check(
            passes,
            failures,
            "Validation row count",
            len(validation_df),
            EXPECTED_VALIDATION_ROWS,
        )

    if not PAIRS_CSV.exists():
        failures.append(f"Pairs CSV not found: {PAIRS_CSV}")
    else:
        pairs_df = pd.read_csv(PAIRS_CSV)
        add_count_check(
            passes,
            failures,
            "Pair row count",
            len(pairs_df),
            EXPECTED_PAIR_ROWS,
        )

    if not validation_df.empty and "image_path" in validation_df.columns:
        missing_paths: list[str] = []
        bad_path_prefix: list[str] = []
        for image_path in validation_df["image_path"].astype(str):
            normalized = image_path.replace("\\", "/")
            if not normalized.startswith("images/"):
                bad_path_prefix.append(image_path)
                continue
            resolved = PACKAGE_DIR / normalized
            if not resolved.exists():
                missing_paths.append(image_path)

        if bad_path_prefix:
            failures.append(
                f"{len(bad_path_prefix)} validation image_path value(s) are not "
                "relative to images/."
            )
        else:
            passes.append("All validation image_path values are relative to images/.")

        if missing_paths:
            failures.append(f"{len(missing_paths)} validation image_path(s) are missing.")
            for path in missing_paths[:5]:
                failures.append(f"  missing: {path}")
        else:
            passes.append("All validation image paths exist in the package.")

    csv_files = list((PACKAGE_DIR / "data").glob("*.csv")) if (PACKAGE_DIR / "data").exists() else []

    for csv_path in csv_files:
        content = csv_path.read_text(encoding="utf-8")
        for needle in LEAKAGE_STRINGS:
            if needle in content:
                failures.append(
                    f"Leakage string {needle!r} found in {csv_path.relative_to(PACKAGE_DIR)}"
                )
            else:
                passes.append(
                    f"No leakage string {needle!r} in {csv_path.name}"
                )

    print("CzechLynx Colab package audit")
    print(f"Package: {PACKAGE_DIR}")
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
