#!/usr/bin/env python3
"""Prepare the expanded CzechLynx 125x4 blinded review package."""

from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "czechlynx"
LABEL_DIR = PROJECT_ROOT / "data" / "labels" / "czechlynx"
REVIEW_IMAGE_DIR = INTERIM_DIR / "expanded_125x4_review_images"

MANIFEST_CSV = INTERIM_DIR / "czechlynx_real_manifest.csv"
PILOT_INTERNAL_CSV = INTERIM_DIR / "czechlynx_pilot_internal_with_ids.csv"
INTERNAL_CSV = INTERIM_DIR / "czechlynx_expanded_125x4_internal_with_ids.csv"
BLINDED_CSV = LABEL_DIR / "czechlynx_expanded_125x4_triage_blinded.csv"
SUMMARY_TXT = INTERIM_DIR / "czechlynx_expanded_125x4_sampling_summary.txt"

SEED = 20260606
EXPANDED_IDS = 125
IMAGES_PER_ID = 4
EXPECTED_ROWS = EXPANDED_IDS * IMAGES_PER_ID
REVIEW_IMAGE_DIR_REL = "data/interim/czechlynx/expanded_125x4_review_images"

MANIFEST_REQUIRED_COLUMNS = [
    "source",
    "date",
    "encounter",
    "unique_name",
    "path",
    "local_image_path",
    "image_exists",
]
PILOT_REQUIRED_COLUMNS = ["pilot_image_id", "unique_name", "path", "local_image_path"]
BLINDED_COLUMNS = [
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


def truthy_image_exists(series: pd.Series) -> pd.Series:
    return series.map(clean_cell).str.lower().isin({"true", "1", "yes"})


def parse_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


def sorted_group(group: pd.DataFrame) -> pd.DataFrame:
    sort_frame = group.copy()
    sort_frame["_parsed_date"] = parse_dates(sort_frame["date"])
    sort_frame["_date_sort"] = sort_frame["_parsed_date"].fillna(pd.Timestamp.max)
    return sort_frame.sort_values(
        ["_date_sort", "source", "encounter", "path"], kind="mergesort"
    )


def spread_positions(length: int, count: int) -> list[int]:
    if count == 1:
        return [0]
    positions = [round(i * (length - 1) / (count - 1)) for i in range(count)]
    result: list[int] = []
    for pos in positions:
        if pos not in result:
            result.append(pos)
    candidate = 0
    while len(result) < count and candidate < length:
        if candidate not in result:
            result.append(candidate)
        candidate += 1
    return sorted(result[:count])


def select_rows_for_id(group: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    limitations: list[str] = []
    ordered = sorted_group(group)
    nonblank_encounters = ordered[ordered["encounter"] != ""]

    if nonblank_encounters["encounter"].nunique() >= IMAGES_PER_ID:
        encounter_order = (
            nonblank_encounters.groupby("encounter", sort=False)["_date_sort"]
            .min()
            .sort_values(kind="mergesort")
            .index.tolist()
        )
        selected_encounters = [
            encounter_order[pos]
            for pos in spread_positions(len(encounter_order), IMAGES_PER_ID)
        ]
        selected_rows = [
            ordered[ordered["encounter"] == encounter].iloc[0]
            for encounter in selected_encounters
        ]
        selected = pd.DataFrame(selected_rows)
    else:
        limitations.append("fewer_than_4_distinct_encounters")
        positions = spread_positions(len(ordered), IMAGES_PER_ID)
        selected = ordered.iloc[positions].copy()

    if selected["date"].nunique() < IMAGES_PER_ID:
        limitations.append("fewer_than_4_distinct_dates_selected")
    if ordered["source"].nunique() > 1 and selected["source"].nunique() == 1:
        replacement = ordered[~ordered["source"].isin(set(selected["source"]))]
        replacement = replacement[~replacement["path"].isin(set(selected["path"]))]
        if not replacement.empty:
            selected = pd.concat([selected.iloc[: IMAGES_PER_ID - 1], replacement.iloc[[0]]])
            selected = sorted_group(selected)
        else:
            limitations.append("source_diversity_available_but_not_selected")
    elif ordered["source"].nunique() < 2:
        limitations.append("single_source_available")

    selected = selected.drop(columns=["_parsed_date", "_date_sort"], errors="ignore")
    selected = selected.drop_duplicates(subset=["path"], keep="first")
    if len(selected) != IMAGES_PER_ID:
        raise ValueError(
            f"selected {len(selected)} image(s) for {group['unique_name'].iloc[0]}; "
            f"expected {IMAGES_PER_ID}"
        )
    return selected, sorted(set(limitations))


def validate_inputs(manifest: pd.DataFrame, pilot: pd.DataFrame) -> None:
    missing_columns = [
        *require_columns(manifest, MANIFEST_REQUIRED_COLUMNS, "manifest"),
        *require_columns(pilot, PILOT_REQUIRED_COLUMNS, "pilot_internal"),
    ]
    if missing_columns:
        raise ValueError("missing required column(s): " + ", ".join(missing_columns))

    if pilot["pilot_image_id"].duplicated().any():
        duplicate_count = int(pilot["pilot_image_id"].duplicated().sum())
        raise ValueError(
            f"pilot internal mapping has {duplicate_count} duplicate pilot_image_id value(s)"
        )


def copy_review_images(selected: pd.DataFrame) -> int:
    REVIEW_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    expected_names = set(selected["review_image_filename"])

    for existing_path in REVIEW_IMAGE_DIR.glob("czlx_expanded_*.jpg"):
        if existing_path.name not in expected_names:
            existing_path.unlink()

    for row in selected.itertuples(index=False):
        src = Path(row.local_image_path)
        dst = REVIEW_IMAGE_DIR / row.review_image_filename
        if not src.exists():
            raise FileNotFoundError(f"selected source image does not exist: {src}")
        shutil.copy2(src, dst)
        copied += 1
    return copied


def build_blinded_csv(selected: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "expanded_image_id": selected["expanded_image_id"],
            "dataset": "CzechLynx",
            "species_label": "Eurasian Lynx",
            "source_role": "quantitative_validation",
            "image_path": selected["review_image_path"],
            "triage_label": "",
            "blur_level": "",
            "occlusion_level": "",
            "lighting_condition": "",
            "night_ir_artifact": "",
            "visible_side": "",
            "side_comparability": "",
            "visible_region": "",
            "pattern_visibility": "",
            "body_fraction_visible": "",
            "distance_to_camera": "",
            "camera_angle": "",
            "metadata_completeness": "complete",
            "reviewer_confidence": "",
            "uncertainty_flag": "",
            "exclusion_reason": "",
            "notes": "",
        },
        columns=BLINDED_COLUMNS,
    )


def write_summary(
    selected: pd.DataFrame,
    selected_ids: list[str],
    eligible_id_count: int,
    current_pilot_path_overlap: int,
    current_pilot_local_path_overlap: int,
    copied_count: int,
    limitation_counts: dict[str, int],
) -> None:
    images_per_id = selected["working_individual_id"].value_counts()
    lines = [
        "CzechLynx expanded 125x4 sampling summary",
        "==========================================",
        "",
        f"random_seed: {SEED}",
        f"selected_working_ids: {len(selected_ids)}",
        f"images_per_id: {IMAGES_PER_ID}",
        f"rows_written: {len(selected)}",
        f"images_copied: {copied_count}",
        f"eligible_ids_with_at_least_4_additional_images: {eligible_id_count}",
        f"current_pilot_overlap_count_by_path: {current_pilot_path_overlap}",
        f"current_pilot_overlap_count_by_local_image_path: {current_pilot_local_path_overlap}",
        f"images_per_id_min: {int(images_per_id.min())}",
        f"images_per_id_max: {int(images_per_id.max())}",
        "",
        "selected_ids:",
    ]
    lines.extend(f"  {working_id}" for working_id in selected_ids)
    lines.extend(["", "diversity_limitations:"])
    if limitation_counts:
        for limitation, count in sorted(limitation_counts.items()):
            lines.append(f"  {limitation}: {count} selected ID(s)")
    else:
        lines.append("  none")
    lines.extend(
        [
            "",
            "outputs:",
            f"  internal_mapping: {INTERNAL_CSV}",
            f"  blinded_triage_csv: {BLINDED_CSV}",
            f"  review_image_dir: {REVIEW_IMAGE_DIR}",
            f"  summary: {SUMMARY_TXT}",
        ]
    )
    SUMMARY_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    try:
        for path in (MANIFEST_CSV, PILOT_INTERNAL_CSV):
            if not path.exists():
                return fail(f"required input not found: {path}")

        manifest = read_csv_clean(MANIFEST_CSV)
        pilot = read_csv_clean(PILOT_INTERNAL_CSV)
        validate_inputs(manifest, pilot)

        existing = manifest[truthy_image_exists(manifest["image_exists"])].copy()
        pilot_paths = set(pilot["path"])
        pilot_local_paths = set(pilot["local_image_path"])
        additional = existing[~existing["path"].isin(pilot_paths)].copy()
        current_pilot_path_overlap = int(additional["path"].isin(pilot_paths).sum())
        current_pilot_local_path_overlap = int(
            additional["local_image_path"].isin(pilot_local_paths).sum()
        )

        counts = additional["unique_name"].value_counts()
        eligible_ids = sorted(counts[counts >= IMAGES_PER_ID].index.tolist())
        if len(eligible_ids) < EXPANDED_IDS:
            raise ValueError(
                f"only {len(eligible_ids)} eligible IDs have at least {IMAGES_PER_ID} "
                f"additional images; need {EXPANDED_IDS}"
            )

        selected_ids = (
            pd.Series(eligible_ids)
            .sample(n=EXPANDED_IDS, random_state=SEED)
            .sort_values(kind="mergesort")
            .tolist()
        )

        selected_parts: list[pd.DataFrame] = []
        limitation_counts: dict[str, int] = {}
        for working_id in selected_ids:
            group = additional[additional["unique_name"] == working_id].copy()
            selected_for_id, limitations = select_rows_for_id(group)
            selected_parts.append(selected_for_id)
            for limitation in limitations:
                limitation_counts[limitation] = limitation_counts.get(limitation, 0) + 1

        selected = pd.concat(selected_parts, ignore_index=True)
        selected = selected.sample(frac=1, random_state=SEED + 1).reset_index(drop=True)
        selected["expanded_image_id"] = [
            f"czlx_expanded_{index:04d}" for index in range(len(selected))
        ]
        selected["review_image_filename"] = selected["expanded_image_id"] + ".jpg"
        selected["review_image_path"] = selected["review_image_filename"].map(
            lambda name: f"{REVIEW_IMAGE_DIR_REL}/{name}"
        )
        selected["working_individual_id"] = selected["unique_name"]

        if len(selected) != EXPECTED_ROWS:
            raise ValueError(f"selected {len(selected)} rows; expected {EXPECTED_ROWS}")
        if selected["path"].isin(pilot_paths).any():
            raise ValueError("selected rows include current pilot path overlap")
        if selected["local_image_path"].isin(pilot_local_paths).any():
            raise ValueError("selected rows include current pilot local_image_path overlap")

        copied_count = copy_review_images(selected)

        internal_columns = [
            "expanded_image_id",
            "review_image_filename",
            "review_image_path",
            "working_individual_id",
            "source",
            "date",
            "encounter",
            "path",
            "local_image_path",
            "image_exists",
        ]
        for optional_column in (
            "relative_age",
            "coat_pattern",
            "split-geo_aware",
            "split-time_open",
            "split-time_closed",
            "split-pose",
        ):
            if optional_column in selected.columns:
                internal_columns.append(optional_column)

        INTERIM_DIR.mkdir(parents=True, exist_ok=True)
        LABEL_DIR.mkdir(parents=True, exist_ok=True)
        selected[internal_columns].to_csv(INTERNAL_CSV, index=False)

        blinded = build_blinded_csv(selected)
        blinded.to_csv(BLINDED_CSV, index=False)

        write_summary(
            selected,
            selected_ids,
            len(eligible_ids),
            current_pilot_path_overlap,
            current_pilot_local_path_overlap,
            copied_count,
            limitation_counts,
        )

        images_per_id = selected["working_individual_id"].value_counts()
        print("CzechLynx expanded 125x4 package preparation")
        print(f"Selected IDs ({len(selected_ids)}):")
        print(", ".join(selected_ids))
        print()
        print(f"Rows written: {len(selected)}")
        print(f"Images copied: {copied_count}")
        print(f"Images per ID min: {int(images_per_id.min())}")
        print(f"Images per ID max: {int(images_per_id.max())}")
        print(f"Current pilot overlap count by path: {current_pilot_path_overlap}")
        print(
            "Current pilot overlap count by local_image_path: "
            f"{current_pilot_local_path_overlap}"
        )
        print("Diversity limitations:")
        if limitation_counts:
            for limitation, count in sorted(limitation_counts.items()):
                print(f"  {limitation}: {count} selected ID(s)")
        else:
            print("  none")
        print("Output paths:")
        print(f"  {INTERNAL_CSV}")
        print(f"  {BLINDED_CSV}")
        print(f"  {SUMMARY_TXT}")
        print(f"  {REVIEW_IMAGE_DIR}")
        print("RESULT: PASS")
        return 0
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
