#!/usr/bin/env python3
"""Audit expanded CzechLynx 125x4 chat review batch folders."""

from __future__ import annotations

import re
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
REPORT_TXT = (
    PROJECT_ROOT
    / "outputs"
    / "czechlynx"
    / "qc"
    / "czechlynx_expanded_125x4_chat_batches_audit.txt"
)

EXPECTED_ROWS = 500
EXPECTED_BATCH_FOLDERS = 25
IMAGES_PER_BATCH = 20

FILENAME_PATTERN = re.compile(r"^czlx_expanded_\d{4}\.jpg$")
TEMPLATE_PATTERN = re.compile(r"^draft_labels_batch_\d{3}_\d{4}_\d{4}\.csv$")
LYNX_ID_PATTERN = re.compile(r"lynx_\d")

LEAKAGE_STRINGS = [
    "working_individual_id",
    "unique_name",
    "latitude",
    "longitude",
    "trap_id",
    "location",
    "cell_code",
    "/CzechLynx/",
    "data/raw/czechlynx",
    "second_review",
]

INDEX_REQUIRED_COLUMNS = [
    "batch_id",
    "image_start",
    "image_end",
    "batch_folder",
    "template_csv",
    "image_count",
]

TEMPLATE_REQUIRED_COLUMNS = [
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


def build_batch_folder_names() -> list[str]:
    names: list[str] = []
    for batch_number in range(1, EXPECTED_BATCH_FOLDERS + 1):
        start_index = (batch_number - 1) * IMAGES_PER_BATCH
        end_index = start_index + IMAGES_PER_BATCH - 1
        names.append(f"batch_{batch_number:03d}_{start_index:04d}_{end_index:04d}")
    return names


def add_result(condition: bool, passes: list[str], failures: list[str], message: str) -> None:
    if condition:
        passes.append(message)
    else:
        failures.append(message)


def check_leakage_text(
    path: Path,
    passes: list[str],
    failures: list[str],
) -> None:
    content = path.read_text(encoding="utf-8")
    relative_path = path.relative_to(PROJECT_ROOT)
    for needle in LEAKAGE_STRINGS:
        if needle in content:
            failures.append(f"Leakage string {needle!r} found in {relative_path}")
        else:
            passes.append(f"No leakage string {needle!r} in {path.name}")
    if LYNX_ID_PATTERN.search(content):
        failures.append(f"Identity-style lynx_### pattern found in {relative_path}")
    else:
        passes.append(f"No identity-style lynx_### pattern in {path.name}")


def format_report(passes: list[str], failures: list[str]) -> str:
    lines = [
        "CzechLynx expanded 125x4 chat batches audit",
        "============================================",
        f"Output directory: {OUTPUT_DIR}",
        f"Blinded CSV: {BLINDED_CSV}",
        f"Index CSV: {INDEX_CSV}",
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
    lines.append("RESULT: PASS" if not failures else "RESULT: FAIL")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    passes: list[str] = []
    failures: list[str] = []
    batch_folder_names = build_batch_folder_names()

    add_result(
        OUTPUT_DIR.exists(),
        passes,
        failures,
        f"Chat batch output directory exists: {OUTPUT_DIR}",
    )
    if not OUTPUT_DIR.exists():
        report = format_report(passes, failures)
        print(report, end="")
        REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
        REPORT_TXT.write_text(report, encoding="utf-8")
        print(f"Wrote: {REPORT_TXT}")
        return 1

    batch_dirs = [OUTPUT_DIR / name for name in batch_folder_names]
    present_batch_dirs = [path for path in batch_dirs if path.is_dir()]
    add_result(
        len(present_batch_dirs) == EXPECTED_BATCH_FOLDERS,
        passes,
        failures,
        f"Exactly {EXPECTED_BATCH_FOLDERS} batch folders exist.",
    )

    all_jpg_files: list[Path] = []
    for batch_dir in batch_dirs:
        if not batch_dir.is_dir():
            failures.append(f"Missing batch folder: {batch_dir.name}")
            continue

        jpg_files = sorted(batch_dir.glob("*.jpg"))
        all_jpg_files.extend(jpg_files)
        add_result(
            len(jpg_files) == IMAGES_PER_BATCH,
            passes,
            failures,
            f"{batch_dir.name} contains exactly {IMAGES_PER_BATCH} jpg files.",
        )

        readme_path = batch_dir / "README.txt"
        if readme_path.exists():
            passes.append(f"{batch_dir.name}/README.txt exists.")
            check_leakage_text(readme_path, passes, failures)
        else:
            failures.append(f"Missing README.txt in {batch_dir.name}")

        template_files = sorted(batch_dir.glob("draft_labels_*.csv"))
        if len(template_files) != 1:
            failures.append(
                f"{batch_dir.name} expected exactly 1 draft label template CSV; "
                f"found {len(template_files)}."
            )
        else:
            template_path = template_files[0]
            if not TEMPLATE_PATTERN.match(template_path.name):
                failures.append(
                    f"{batch_dir.name} template name does not match expected pattern: "
                    f"{template_path.name}"
                )
            else:
                passes.append(f"{batch_dir.name} has one draft label template CSV.")
                template_df = read_csv_clean(template_path)
                missing_template_columns = sorted(
                    set(TEMPLATE_REQUIRED_COLUMNS) - set(template_df.columns)
                )
                if missing_template_columns:
                    failures.append(
                        f"{template_path.name} missing required column(s): "
                        + ", ".join(missing_template_columns)
                    )
                else:
                    passes.append(f"{template_path.name} has required template columns.")
                if len(template_df) != IMAGES_PER_BATCH:
                    failures.append(
                        f"{template_path.name} has {len(template_df)} rows; "
                        f"expected {IMAGES_PER_BATCH}."
                    )
                else:
                    passes.append(f"{template_path.name} has {IMAGES_PER_BATCH} rows.")
                label_fields = [column for column in TEMPLATE_REQUIRED_COLUMNS if column != "expanded_image_id"]
                filled_label_cells = int(
                    (template_df[label_fields] != "").sum().sum()
                )
                if filled_label_cells:
                    failures.append(
                        f"{template_path.name} has {filled_label_cells} nonblank label field(s); "
                        "templates must leave label fields blank."
                    )
                else:
                    passes.append(f"{template_path.name} leaves label fields blank.")
                if (template_df["expanded_image_id"] == "").any():
                    failures.append(f"{template_path.name} has blank expanded_image_id value(s).")
                else:
                    passes.append(f"{template_path.name} has expanded_image_id values filled.")
                check_leakage_text(template_path, passes, failures)

        bad_filenames = [path.name for path in jpg_files if not FILENAME_PATTERN.match(path.name)]
        if bad_filenames:
            failures.append(
                f"{batch_dir.name} has {len(bad_filenames)} filename(s) not matching "
                "czlx_expanded_####.jpg."
            )
            for name in bad_filenames[:5]:
                failures.append(f"  invalid filename: {name}")
        else:
            passes.append(f"All filenames in {batch_dir.name} match czlx_expanded_####.jpg.")

    add_result(
        len(all_jpg_files) == EXPECTED_ROWS,
        passes,
        failures,
        f"Total jpg files across batch folders is exactly {EXPECTED_ROWS}.",
    )

    if BLINDED_CSV.exists():
        blinded = read_csv_clean(BLINDED_CSV)
        expected_filenames = {Path(path_text).name for path_text in blinded["image_path"]}
        actual_filenames = {path.name for path in all_jpg_files}
        missing_filenames = sorted(expected_filenames - actual_filenames)
        extra_filenames = sorted(actual_filenames - expected_filenames)
        duplicate_filenames = sorted(
            {
                name
                for name in actual_filenames
                if sum(1 for path in all_jpg_files if path.name == name) > 1
            }
        )

        add_result(
            not missing_filenames,
            passes,
            failures,
            "Every expanded image appears in chat batch folders.",
        )
        if missing_filenames:
            for name in missing_filenames[:10]:
                failures.append(f"  missing image: {name}")

        add_result(
            not extra_filenames,
            passes,
            failures,
            "No extra images exist in chat batch folders.",
        )
        if extra_filenames:
            for name in extra_filenames[:10]:
                failures.append(f"  extra image: {name}")

        add_result(
            not duplicate_filenames,
            passes,
            failures,
            "Each expanded image appears exactly once.",
        )
        if duplicate_filenames:
            for name in duplicate_filenames[:10]:
                failures.append(f"  duplicate image: {name}")
    else:
        failures.append(f"Blinded CSV not found: {BLINDED_CSV}")

    if INDEX_CSV.exists():
        passes.append("Chat batch index CSV exists.")
        index_df = read_csv_clean(INDEX_CSV)
        add_result(
            len(index_df) == EXPECTED_BATCH_FOLDERS,
            passes,
            failures,
            f"Chat batch index CSV has exactly {EXPECTED_BATCH_FOLDERS} rows.",
        )
        missing_index_columns = sorted(set(INDEX_REQUIRED_COLUMNS) - set(index_df.columns))
        if missing_index_columns:
            failures.append(
                "Chat batch index CSV missing required column(s): "
                + ", ".join(missing_index_columns)
            )
        else:
            passes.append("Chat batch index CSV has required columns.")
        check_leakage_text(INDEX_CSV, passes, failures)
    else:
        failures.append(f"Chat batch index CSV not found: {INDEX_CSV}")

    report = format_report(passes, failures)
    print(report, end="")

    REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_TXT.write_text(report, encoding="utf-8")
    print(f"Wrote: {REPORT_TXT}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
