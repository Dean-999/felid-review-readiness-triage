#!/usr/bin/env python3
"""Audit CzechLynx pilot triage CSV for blinding compliance."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BLINDED_CSV = PROJECT_ROOT / "data" / "labels" / "czechlynx" / "czechlynx_pilot_triage_blinded.csv"
EXPECTED_ROW_COUNT = 200
REVIEW_IMAGE_DIR = "data/interim/czechlynx/pilot_review_images/"
REVIEW_FILENAME_PATTERN = re.compile(r"^czlx_pilot_\d{4}\.jpg$")

LEAKAGE_STRINGS = [
    "lynx_",
    "unique_name",
    "latitude",
    "longitude",
    "trap_id",
    "location",
    "cell_code",
    "/CzechLynx/",
    "data/raw/czechlynx",
]


def main() -> int:
    failures: list[str] = []
    passes: list[str] = []

    if not BLINDED_CSV.exists():
        print(f"FAIL: blinded CSV not found: {BLINDED_CSV}")
        return 1

    df = pd.read_csv(BLINDED_CSV)
    row_count = len(df)
    if row_count == EXPECTED_ROW_COUNT:
        passes.append(f"Row count is exactly {EXPECTED_ROW_COUNT}.")
    else:
        failures.append(
            f"Row count is {row_count}; expected exactly {EXPECTED_ROW_COUNT}."
        )

    csv_text = BLINDED_CSV.read_text(encoding="utf-8")
    for needle in LEAKAGE_STRINGS:
        if needle in csv_text:
            failures.append(f"Leakage string found in CSV: {needle!r}")
        else:
            passes.append(f"No leakage string: {needle!r}")

    if "image_path" not in df.columns:
        failures.append("Missing required column: image_path")
        image_paths: list[str] = []
    else:
        image_paths = df["image_path"].astype(str).tolist()

    bad_path_prefix: list[str] = []
    missing_images: list[str] = []
    bad_filenames: list[str] = []

    for image_path in image_paths:
        normalized = image_path.replace("\\", "/")
        if REVIEW_IMAGE_DIR not in normalized:
            bad_path_prefix.append(image_path)
            continue

        resolved = Path(image_path)
        if not resolved.is_absolute():
            resolved = PROJECT_ROOT / image_path

        if not resolved.exists():
            missing_images.append(str(resolved))

        filename = resolved.name
        if not REVIEW_FILENAME_PATTERN.match(filename):
            bad_filenames.append(filename)

    if bad_path_prefix:
        failures.append(
            f"{len(bad_path_prefix)} image_path value(s) do not point to "
            f"{REVIEW_IMAGE_DIR!r}."
        )
    else:
        passes.append(f"All image_path values point to {REVIEW_IMAGE_DIR!r}.")

    if missing_images:
        failures.append(f"{len(missing_images)} referenced image(s) are missing.")
        for path in missing_images[:5]:
            failures.append(f"  missing: {path}")
        if len(missing_images) > 5:
            failures.append(f"  ... and {len(missing_images) - 5} more")
    else:
        passes.append("All referenced review images exist.")

    if bad_filenames:
        failures.append(
            f"{len(bad_filenames)} review image filename(s) do not match "
            "czlx_pilot_####.jpg."
        )
        for name in bad_filenames[:5]:
            failures.append(f"  invalid filename: {name}")
        if len(bad_filenames) > 5:
            failures.append(f"  ... and {len(bad_filenames) - 5} more")
    else:
        passes.append("All review image filenames match czlx_pilot_####.jpg.")

    print("CzechLynx pilot blinding audit")
    print(f"CSV: {BLINDED_CSV}")
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
