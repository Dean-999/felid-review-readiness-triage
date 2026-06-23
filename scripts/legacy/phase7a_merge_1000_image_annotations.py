#!/usr/bin/env python3
"""Merge Phase 4 and Phase 6 v2 image annotations into a Phase 7A table."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PHASE4_CSV = (
    PROJECT_ROOT / "data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated_v1.csv"
)
DEFAULT_PHASE6_CSV = (
    PROJECT_ROOT
    / "data/labels/czechlynx/czechlynx_phase6_unique_500_v2_balanced_image_annotation_v1.csv"
)
DEFAULT_OUTPUT_CSV = (
    PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_working.csv"
)

PHASE7_COLUMNS = [
    "phase7_image_id",
    "source_phase",
    "source_image_id",
    "expanded_image_id",
    "review_image_path_local",
    "batch_id",
    "quality_bucket",
    "selection_stratum",
    "pattern_visibility",
    "side_visibility",
    "side_evidence_quality",
    "body_fraction_visible",
    "partial_body",
    "frontal_or_rear_view",
    "silhouette_only",
    "blur_level",
    "occlusion_level",
    "lighting_condition",
    "night_ir_artifact",
    "contrast_level",
    "primary_limiting_factor",
    "uncertainty_flag",
    "annotation_status",
    "annotator_notes",
    "source_review_image_path_original",
    "source_blur_level_original",
    "source_occlusion_level_original",
    "source_side_visibility_original",
    "source_lighting_condition_original",
    "source_night_ir_artifact_original",
    "source_primary_limiting_factor_original",
    "mapping_notes",
]

PHASE4_REQUIRED = {
    "expanded_image_id",
    "review_image_path_local",
    "blur_level",
    "occlusion_level",
    "side_visibility",
    "side_evidence_quality",
    "lighting_condition",
    "night_ir_artifact",
    "pattern_visibility",
    "body_fraction_visible",
    "partial_body",
    "frontal_or_rear_view",
    "silhouette_only",
    "primary_limiting_factor",
    "uncertainty_flag",
    "notes",
    "annotation_status",
}

PHASE6_REQUIRED = {
    "expanded_image_id",
    "review_image_path_local",
    "selection_stratum",
    "quality_bucket",
    "batch_id",
    "pattern_visibility",
    "side_visibility",
    "side_evidence_quality",
    "body_fraction_visible",
    "partial_body",
    "frontal_or_rear_view",
    "silhouette_only",
    "blur_level",
    "occlusion_level",
    "lighting_condition",
    "night_ir_artifact",
    "contrast_level",
    "primary_limiting_factor",
    "uncertainty_flag",
    "annotation_status",
    "annotator_notes",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PHASE7_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def require_columns(path: Path, rows: list[dict[str, str]], required: set[str]) -> None:
    if not rows:
        raise ValueError(f"{path} has no rows")
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}")


def normalize_phase4_occlusion(value: str, notes: list[str]) -> str:
    mapping = {
        "none": "none",
        "mild": "partial",
        "moderate": "partial",
        "severe": "major",
        "unknown": "unknown",
        "": "unknown",
    }
    normalized = mapping.get(value, "unknown")
    if value in {"mild", "moderate", "severe"}:
        notes.append(f"phase4_occlusion_{value}_mapped_to_{normalized}")
    elif value not in mapping:
        notes.append(f"phase4_occlusion_unrecognized_{value}_mapped_to_unknown")
    return normalized


def normalize_phase4_lighting(value: str, notes: list[str]) -> str:
    mapping = {
        "daylight": "normal",
        "low_light": "low_light",
        "night_ir": "night_ir",
        "overexposed": "overexposed",
        "underexposed": "underexposed",
        "mixed": "mixed",
        "": "unknown",
    }
    normalized = mapping.get(value, "unknown")
    if value == "daylight":
        notes.append("phase4_lighting_daylight_mapped_to_normal")
    elif value in {"low_light", "night_ir"}:
        notes.append(f"phase4_lighting_{value}_preserved_as_phase7_specific_state")
    elif value not in mapping:
        notes.append(f"phase4_lighting_unrecognized_{value}_mapped_to_unknown")
    return normalized


def normalize_phase4_night_ir(value: str, notes: list[str]) -> str:
    if value in {"mild", "moderate", "severe"}:
        notes.append(f"phase4_night_ir_artifact_{value}_collapsed_to_yes")
        return "yes"
    if value in {"none", "not_applicable"}:
        if value == "not_applicable":
            notes.append("phase4_night_ir_artifact_not_applicable_collapsed_to_no")
        return "no"
    if value in {"unknown", ""}:
        notes.append("phase4_night_ir_artifact_unknown_preserved")
        return "unknown"
    notes.append(f"phase4_night_ir_artifact_unrecognized_{value}_mapped_to_unknown")
    return "unknown"


def normalize_phase4_primary_limiting_factor(value: str, notes: list[str]) -> str:
    mapping = {
        "none": "none",
        "blur": "blur",
        "occlusion": "occlusion",
        "frontal_or_rear_view": "frontal_or_rear_view",
        "low_contrast": "low_contrast",
        "night_ir_artifact": "night_ir_artifact",
        "overexposed": "overexposed",
        "underexposed": "underexposed",
        "partial_body": "partial_body",
        "pattern_not_visible": "pattern_not_visible",
        "side_unknown": "side_unknown",
        "side_non_comparable": "side_non_comparable",
        "silhouette": "silhouette",
        "other": "other",
        "unknown": "unknown",
        "": "unknown",
    }
    normalized = mapping.get(value, "other")
    if value not in mapping:
        notes.append(f"phase4_primary_limiting_factor_unrecognized_{value}_mapped_to_other")
    return normalized


def phase4_row(row: dict[str, str], index: int) -> dict[str, str]:
    notes: list[str] = ["phase4_quality_bucket_not_available"]
    occlusion = normalize_phase4_occlusion(row["occlusion_level"], notes)
    lighting = normalize_phase4_lighting(row["lighting_condition"], notes)
    night_ir = normalize_phase4_night_ir(row["night_ir_artifact"], notes)
    limiting = normalize_phase4_primary_limiting_factor(row["primary_limiting_factor"], notes)
    notes.append("phase4_contrast_level_not_available")
    notes.append("phase4_batch_id_assigned_phase4_original_500")
    notes.append("phase4_selection_stratum_assigned_phase4_original_500")

    return {
        "phase7_image_id": f"p7a_phase4_{index:04d}",
        "source_phase": "phase4_original_500",
        "source_image_id": row["expanded_image_id"],
        "expanded_image_id": row["expanded_image_id"],
        "review_image_path_local": row["review_image_path_local"],
        "batch_id": "phase4_original_500",
        "quality_bucket": "phase4_original_500",
        "selection_stratum": "phase4_original_500",
        "pattern_visibility": row["pattern_visibility"],
        "side_visibility": row["side_visibility"],
        "side_evidence_quality": row["side_evidence_quality"],
        "body_fraction_visible": row["body_fraction_visible"],
        "partial_body": row["partial_body"],
        "frontal_or_rear_view": row["frontal_or_rear_view"],
        "silhouette_only": row["silhouette_only"],
        "blur_level": row["blur_level"],
        "occlusion_level": occlusion,
        "lighting_condition": lighting,
        "night_ir_artifact": night_ir,
        "contrast_level": "not_available",
        "primary_limiting_factor": limiting,
        "uncertainty_flag": row["uncertainty_flag"],
        "annotation_status": row["annotation_status"],
        "annotator_notes": row.get("notes", ""),
        "source_review_image_path_original": row["review_image_path_local"],
        "source_blur_level_original": row["blur_level"],
        "source_occlusion_level_original": row["occlusion_level"],
        "source_side_visibility_original": row["side_visibility"],
        "source_lighting_condition_original": row["lighting_condition"],
        "source_night_ir_artifact_original": row["night_ir_artifact"],
        "source_primary_limiting_factor_original": row["primary_limiting_factor"],
        "mapping_notes": ";".join(notes),
    }


def phase6_row(row: dict[str, str], index: int) -> dict[str, str]:
    review_image_path = row["review_image_path_local"]
    mapping_notes = ["phase6_v2_values_directly_mapped"]
    if review_image_path.startswith("images/"):
        review_image_path = f"data/review_images/czechlynx/phase6_unique_500_v2_balanced/{Path(review_image_path).name}"
        mapping_notes.append("phase6_v2_stale_images_relative_path_normalized")

    return {
        "phase7_image_id": f"p7a_phase6_v2_{index:04d}",
        "source_phase": "phase6_v2_balanced_500",
        "source_image_id": row["expanded_image_id"],
        "expanded_image_id": row["expanded_image_id"],
        "review_image_path_local": review_image_path,
        "batch_id": row["batch_id"],
        "quality_bucket": row["quality_bucket"],
        "selection_stratum": row["selection_stratum"],
        "pattern_visibility": row["pattern_visibility"],
        "side_visibility": row["side_visibility"],
        "side_evidence_quality": row["side_evidence_quality"],
        "body_fraction_visible": row["body_fraction_visible"],
        "partial_body": row["partial_body"],
        "frontal_or_rear_view": row["frontal_or_rear_view"],
        "silhouette_only": row["silhouette_only"],
        "blur_level": row["blur_level"],
        "occlusion_level": row["occlusion_level"],
        "lighting_condition": row["lighting_condition"],
        "night_ir_artifact": row["night_ir_artifact"],
        "contrast_level": row["contrast_level"],
        "primary_limiting_factor": row["primary_limiting_factor"],
        "uncertainty_flag": row["uncertainty_flag"],
        "annotation_status": row["annotation_status"],
        "annotator_notes": row.get("annotator_notes", ""),
        "source_review_image_path_original": row["review_image_path_local"],
        "source_blur_level_original": row["blur_level"],
        "source_occlusion_level_original": row["occlusion_level"],
        "source_side_visibility_original": row["side_visibility"],
        "source_lighting_condition_original": row["lighting_condition"],
        "source_night_ir_artifact_original": row["night_ir_artifact"],
        "source_primary_limiting_factor_original": row["primary_limiting_factor"],
        "mapping_notes": ";".join(mapping_notes),
    }


def build_phase7_rows(phase4_rows: list[dict[str, str]], phase6_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    merged = [phase4_row(row, index) for index, row in enumerate(phase4_rows)]
    merged.extend(phase6_row(row, index) for index, row in enumerate(phase6_rows))
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase4-csv", type=Path, default=DEFAULT_PHASE4_CSV)
    parser.add_argument("--phase6-csv", type=Path, default=DEFAULT_PHASE6_CSV)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    phase4_csv = args.phase4_csv.resolve()
    phase6_csv = args.phase6_csv.resolve()
    output_csv = args.output_csv.resolve()

    phase4_rows = read_csv(phase4_csv)
    phase6_rows = read_csv(phase6_csv)
    require_columns(phase4_csv, phase4_rows, PHASE4_REQUIRED)
    require_columns(phase6_csv, phase6_rows, PHASE6_REQUIRED)

    merged_rows = build_phase7_rows(phase4_rows, phase6_rows)
    write_csv(output_csv, merged_rows)

    print("Phase 7A 1000-image annotation merge complete")
    print(f"phase4_input: {phase4_csv}")
    print(f"phase6_v2_input: {phase6_csv}")
    print(f"output: {output_csv}")
    print(f"phase4_rows: {len(phase4_rows)}")
    print(f"phase6_v2_rows: {len(phase6_rows)}")
    print(f"merged_rows: {len(merged_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
