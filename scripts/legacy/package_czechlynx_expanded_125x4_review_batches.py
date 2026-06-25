#!/usr/bin/env python3
"""Package expanded CzechLynx 125x4 review images into local batch folders."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BLINDED_CSV = (
    PROJECT_ROOT
    / "data"
    / "labels"
    / "czechlynx"
    / "czechlynx_expanded_125x4_triage_blinded.csv"
)
WORKING_CSV = (
    PROJECT_ROOT
    / "data"
    / "labels"
    / "czechlynx"
    / "czechlynx_expanded_125x4_triage_working.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "expanded_125x4_review_batches"
INDEX_CSV = OUTPUT_DIR / "expanded_125x4_batch_index.csv"
AUDIT_COMMAND = "python3 scripts/audit_czechlynx_expanded_125x4_triage_consistency.py"

EXPECTED_ROWS = 500
IMAGES_PER_BATCH = 100

BATCHES = [
    {
        "batch_id": "batch_01_0000_0099",
        "start_index": 0,
        "end_index": 99,
        "contact_sheets": "01-04",
    },
    {
        "batch_id": "batch_02_0100_0199",
        "start_index": 100,
        "end_index": 199,
        "contact_sheets": "05-08",
    },
    {
        "batch_id": "batch_03_0200_0299",
        "start_index": 200,
        "end_index": 299,
        "contact_sheets": "09-12",
    },
    {
        "batch_id": "batch_04_0300_0399",
        "start_index": 300,
        "end_index": 399,
        "contact_sheets": "13-16",
    },
    {
        "batch_id": "batch_05_0400_0499",
        "start_index": 400,
        "end_index": 499,
        "contact_sheets": "17-20",
    },
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


def resolve_image_path(image_path: str) -> Path:
    path = Path(image_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def build_readme(batch: dict[str, object]) -> str:
    start_id = f"czlx_expanded_{int(batch['start_index']):04d}"
    end_id = f"czlx_expanded_{int(batch['end_index']):04d}"
    working_csv_rel = WORKING_CSV.relative_to(PROJECT_ROOT)
    return "\n".join(
        [
            "CzechLynx expanded 125x4 review batch folder",
            "============================================",
            "",
            f"Batch folder: {batch['batch_id']}",
            f"Image range: {start_id} to {end_id}",
            f"Contact sheets: {batch['contact_sheets']}",
            "",
            "Working CSV:",
            str(working_csv_rel),
            "",
            "After labeling this batch, run:",
            AUDIT_COMMAND,
            "",
            "Notes:",
            "- Use neutral filenames only.",
            "- Do not edit the original blinded CSV directly.",
            "- This folder is a local review aid and should not be committed.",
            "",
        ]
    )


def main() -> int:
    if not BLINDED_CSV.exists():
        return fail(f"blinded CSV not found: {BLINDED_CSV}")

    df = read_csv_clean(BLINDED_CSV)
    required_columns = {"expanded_image_id", "image_path"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        return fail("blinded CSV missing required column(s): " + ", ".join(missing_columns))

    if len(df) != EXPECTED_ROWS:
        return fail(f"blinded CSV row count is {len(df)}; expected {EXPECTED_ROWS}")

    df = df.sort_values("expanded_image_id", kind="mergesort").reset_index(drop=True)
    expected_ids = [f"czlx_expanded_{index:04d}" for index in range(EXPECTED_ROWS)]
    actual_ids = df["expanded_image_id"].tolist()
    if actual_ids != expected_ids:
        return fail("blinded CSV expanded_image_id sequence does not match czlx_expanded_0000-0499")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str]] = []
    copied_count = 0
    working_csv_rel = str(WORKING_CSV.relative_to(PROJECT_ROOT))

    for batch in BATCHES:
        batch_dir = OUTPUT_DIR / str(batch["batch_id"])
        batch_dir.mkdir(parents=True, exist_ok=True)
        readme_path = batch_dir / "README.txt"
        readme_path.write_text(build_readme(batch), encoding="utf-8")

        batch_rows = df.iloc[int(batch["start_index"]) : int(batch["end_index"]) + 1]
        if len(batch_rows) != IMAGES_PER_BATCH:
            return fail(
                f"{batch['batch_id']} expected {IMAGES_PER_BATCH} rows; got {len(batch_rows)}"
            )

        for _, row in batch_rows.iterrows():
            source_path = resolve_image_path(row["image_path"])
            if not source_path.exists():
                return fail(f"source image not found: {source_path}")

            image_filename = source_path.name
            destination_path = batch_dir / image_filename
            shutil.copy2(source_path, destination_path)
            copied_count += 1

            index_rows.append(
                {
                    "batch_id": str(batch["batch_id"]),
                    "expanded_image_id": row["expanded_image_id"],
                    "image_filename": image_filename,
                    "batch_relative_path": f"{batch['batch_id']}/{image_filename}",
                    "working_csv": working_csv_rel,
                }
            )

    index_df = pd.DataFrame(index_rows)
    index_df.to_csv(INDEX_CSV, index=False)

    print("CzechLynx expanded 125x4 review batch packaging")
    print(f"Blinded CSV: {BLINDED_CSV}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Total images copied: {copied_count}")
    print(f"Batch folders created: {len(BATCHES)}")
    for batch in BATCHES:
        batch_dir = OUTPUT_DIR / str(batch["batch_id"])
        jpg_count = len(list(batch_dir.glob("*.jpg")))
        print(f"  {batch['batch_id']}: {jpg_count} files")
    print(f"Wrote index: {INDEX_CSV}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
