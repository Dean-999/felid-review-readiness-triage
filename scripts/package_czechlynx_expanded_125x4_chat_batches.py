#!/usr/bin/env python3
"""Package expanded CzechLynx 125x4 images into 20-image chat review batches."""

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
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "expanded_125x4_chat_batches"
INDEX_CSV = OUTPUT_DIR / "expanded_125x4_chat_batch_index.csv"

EXPECTED_ROWS = 500
BATCH_COUNT = 25
IMAGES_PER_BATCH = 20

TEMPLATE_COLUMNS = [
    "expanded_image_id",
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


def build_batch_definitions() -> list[dict[str, object]]:
    batches: list[dict[str, object]] = []
    for batch_number in range(1, BATCH_COUNT + 1):
        start_index = (batch_number - 1) * IMAGES_PER_BATCH
        end_index = start_index + IMAGES_PER_BATCH - 1
        batch_id = f"batch_{batch_number:03d}_{start_index:04d}_{end_index:04d}"
        template_csv = f"draft_labels_{batch_id}.csv"
        batches.append(
            {
                "batch_number": batch_number,
                "batch_id": batch_id,
                "start_index": start_index,
                "end_index": end_index,
                "template_csv": template_csv,
            }
        )
    return batches


def build_readme(batch: dict[str, object]) -> str:
    start_id = f"czlx_expanded_{int(batch['start_index']):04d}"
    end_id = f"czlx_expanded_{int(batch['end_index']):04d}"
    template_csv = str(batch["template_csv"])
    return "\n".join(
        [
            "CzechLynx expanded 125x4 chat review batch",
            "========================================",
            "",
            f"Batch folder: {batch['batch_id']}",
            f"Image range: {start_id} to {end_id}",
            f"Draft label template: {template_csv}",
            "",
            "Purpose",
            "-------",
            "This batch is for AI-assisted draft triage followed by human adjudication.",
            "Upload the 20 neutral review images to ChatGPT for draft suggestions only.",
            "",
            "Required cautions",
            "-----------------",
            "- Do not treat AI draft labels as final scientific labels.",
            "- Do not describe this workflow as fully manual labeling.",
            "- Final labels must be manually reviewed and corrected before entering the working CSV.",
            "- Do not use internal identity mapping during review.",
            "- This folder is a local review aid and should not be committed.",
            "",
        ]
    )


def build_template_rows(batch_rows: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for _, row in batch_rows.iterrows():
        template_row = {column: "" for column in TEMPLATE_COLUMNS}
        template_row["expanded_image_id"] = row["expanded_image_id"]
        rows.append(template_row)
    return pd.DataFrame(rows, columns=TEMPLATE_COLUMNS)


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
    if df["expanded_image_id"].tolist() != expected_ids:
        return fail("blinded CSV expanded_image_id sequence does not match czlx_expanded_0000-0499")

    batches = build_batch_definitions()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str | int]] = []
    copied_count = 0

    for batch in batches:
        batch_dir = OUTPUT_DIR / str(batch["batch_id"])
        batch_dir.mkdir(parents=True, exist_ok=True)
        (batch_dir / "README.txt").write_text(build_readme(batch), encoding="utf-8")

        batch_rows = df.iloc[int(batch["start_index"]) : int(batch["end_index"]) + 1]
        if len(batch_rows) != IMAGES_PER_BATCH:
            return fail(
                f"{batch['batch_id']} expected {IMAGES_PER_BATCH} rows; got {len(batch_rows)}"
            )

        for _, row in batch_rows.iterrows():
            source_path = resolve_image_path(row["image_path"])
            if not source_path.exists():
                return fail(f"source image not found: {source_path}")
            shutil.copy2(source_path, batch_dir / source_path.name)
            copied_count += 1

        template_path = batch_dir / str(batch["template_csv"])
        build_template_rows(batch_rows).to_csv(template_path, index=False)

        index_rows.append(
            {
                "batch_id": str(batch["batch_id"]),
                "image_start": int(batch["start_index"]),
                "image_end": int(batch["end_index"]),
                "batch_folder": str(batch["batch_id"]),
                "template_csv": f"{batch['batch_id']}/{batch['template_csv']}",
                "image_count": IMAGES_PER_BATCH,
            }
        )

    pd.DataFrame(index_rows).to_csv(INDEX_CSV, index=False)

    print("CzechLynx expanded 125x4 chat batch packaging")
    print(f"Blinded CSV: {BLINDED_CSV}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Total images copied: {copied_count}")
    print(f"Batch folders created: {len(batches)}")
    for batch in batches:
        batch_dir = OUTPUT_DIR / str(batch["batch_id"])
        jpg_count = len(list(batch_dir.glob("*.jpg")))
        print(f"  {batch['batch_id']}: {jpg_count} images, template {batch['template_csv']}")
    print(f"Wrote index: {INDEX_CSV}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
