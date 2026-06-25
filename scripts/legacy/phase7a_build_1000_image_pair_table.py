#!/usr/bin/env python3
"""Build a leakage-safe Phase 7A pair-level evidence table."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MASTER_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
PAIR_SOURCE_CSV = (
    PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_pair_level_mechanism_similarity_table.csv"
)
OUTPUT_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/pair_tables/phase7a_1000_image_pair_table_working.csv"

VISUAL_FACTORS = [
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
    "quality_bucket",
    "selection_stratum",
]

BASE_COLUMNS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "source_image_id_a",
    "source_image_id_b",
    "expanded_image_id_a",
    "expanded_image_id_b",
    "source_phase_a",
    "source_phase_b",
    "source_pair_origin",
    "same_identity",
    "pair_label_available",
    "resnet50_similarity",
    "megadescriptor_similarity",
    "descriptor_available",
]

DERIVED_COLUMNS = [
    "pair_source_phase_type",
    "pair_annotation_status",
    "pair_has_needs_review",
    "pair_has_uncertainty",
    "pair_has_missing_mapping",
    "pair_visual_completeness_class",
    "pair_pattern_min",
    "pair_pattern_max",
    "pair_side_model_class_a",
    "pair_side_model_class_b",
    "pair_view_model_class_a",
    "pair_view_model_class_b",
    "pair_side_compatible",
    "pair_has_side_unknown",
    "pair_has_frontal_or_rear",
    "pair_body_fraction_min",
    "pair_has_partial_body",
    "pair_blur_worst",
    "pair_occlusion_worst",
    "pair_lighting_worst",
    "pair_contrast_worst",
    "pair_has_night_ir_artifact",
    "pair_primary_limiting_factor_combined",
    "pair_modeling_eligible",
    "pair_exclusion_reason",
]

FIELDNAMES = (
    BASE_COLUMNS
    + [f"{factor}_a" for factor in VISUAL_FACTORS]
    + [f"{factor}_b" for factor in VISUAL_FACTORS]
    + DERIVED_COLUMNS
)

ORDERINGS = {
    "pattern_visibility": {"none": 0, "low": 1, "medium": 2, "high": 3, "unknown": -1},
    "body_fraction_visible": {"0_25": 0, "26_50": 1, "51_75": 2, "76_100": 3, "unknown": -1},
    "blur_level": {"none": 0, "mild": 1, "moderate": 2, "severe": 3, "unknown": 4},
    "occlusion_level": {"none": 0, "partial": 1, "major": 2, "unknown": 3},
    "lighting_condition": {
        "normal": 0,
        "mixed": 1,
        "low_light": 2,
        "overexposed": 3,
        "underexposed": 3,
        "night_ir": 4,
        "unknown": 5,
    },
    "contrast_level": {"good": 0, "low": 1, "not_available": 2, "unknown": 3},
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def side_model_class(side_visibility: str) -> str:
    if side_visibility in {"left", "right", "both"}:
        return side_visibility
    return "unknown_or_non_side"


def view_model_class(side_visibility: str) -> str:
    if side_visibility in {"left", "right", "both"}:
        return "side"
    if side_visibility in {"frontal", "rear"}:
        return "frontal_or_rear"
    return "unknown"


def side_compatible(side_a: str, side_b: str) -> str:
    if "unknown_or_non_side" in {side_a, side_b}:
        return "unknown"
    if side_a == side_b:
        return "yes"
    if side_a == "both" and side_b in {"left", "right", "both"}:
        return "yes"
    if side_b == "both" and side_a in {"left", "right", "both"}:
        return "yes"
    if {side_a, side_b} == {"left", "right"}:
        return "no"
    return "unknown"


def ordinal_min(value_a: str, value_b: str, ordering_name: str) -> str:
    ordering = ORDERINGS[ordering_name]
    return min([value_a, value_b], key=lambda value: ordering.get(value, -1))


def ordinal_max(value_a: str, value_b: str, ordering_name: str) -> str:
    ordering = ORDERINGS[ordering_name]
    return max([value_a, value_b], key=lambda value: ordering.get(value, -1))


def worst(value_a: str, value_b: str, ordering_name: str) -> str:
    return ordinal_max(value_a, value_b, ordering_name)


def pair_source_phase_type(source_a: str, source_b: str) -> str:
    if source_a == "phase4_original_500" and source_b == "phase4_original_500":
        return "phase4_phase4"
    if source_a == "phase6_v2_balanced_500" and source_b == "phase6_v2_balanced_500":
        return "phase6_phase6"
    return "cross_phase"


def pair_annotation_status(image_a: dict[str, str], image_b: dict[str, str]) -> str:
    statuses = {image_a["annotation_status"], image_b["annotation_status"]}
    if "needs_review" in statuses:
        return "needs_review"
    if statuses == {"complete"}:
        return "complete"
    return "mixed_or_unknown"


def has_mapping_caveat(image: dict[str, str]) -> bool:
    notes = image.get("mapping_notes", "")
    return any(
        token in notes
        for token in [
            "not_available",
            "mapped_to",
            "collapsed",
            "unrecognized",
            "preserved_as_phase7_specific_state",
        ]
    )


def visual_completeness(image_a: dict[str, str], image_b: dict[str, str]) -> str:
    if pair_annotation_status(image_a, image_b) == "needs_review":
        return "needs_review"
    core_fields = [
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
    ]
    if any(image[field] in {"", "unknown"} for image in [image_a, image_b] for field in core_fields):
        return "core_visual_fields_with_unknown"
    if has_mapping_caveat(image_a) or has_mapping_caveat(image_b):
        return "core_complete_with_mapping_caveat"
    return "core_complete"


def exclusion_reasons(image_a: dict[str, str], image_b: dict[str, str], source_row: dict[str, str]) -> list[str]:
    reasons: list[str] = []
    if source_row.get("pair_type") not in {"same", "different"}:
        reasons.append("missing_or_invalid_truth_label")
    for field in ["resnet50_similarity", "megadescriptor_similarity"]:
        if source_row.get(field, "") == "":
            reasons.append(f"missing_{field}")
    if pair_annotation_status(image_a, image_b) != "complete":
        reasons.append("annotation_needs_review")
    if visual_completeness(image_a, image_b) == "core_visual_fields_with_unknown":
        reasons.append("core_visual_field_unknown")
    return reasons


def build_pair_row(source_row: dict[str, str], image_a: dict[str, str], image_b: dict[str, str]) -> dict[str, str]:
    side_a = side_model_class(image_a["side_visibility"])
    side_b = side_model_class(image_b["side_visibility"])
    view_a = view_model_class(image_a["side_visibility"])
    view_b = view_model_class(image_b["side_visibility"])
    compatible = side_compatible(side_a, side_b)
    reasons = exclusion_reasons(image_a, image_b, source_row)
    descriptor_available = (
        "yes" if source_row.get("resnet50_similarity", "") != "" and source_row.get("megadescriptor_similarity", "") != "" else "no"
    )

    row: dict[str, str] = {
        "pair_id": source_row["pair_id"],
        "image_id_a": image_a["phase7_image_id"],
        "image_id_b": image_b["phase7_image_id"],
        "source_image_id_a": image_a["source_image_id"],
        "source_image_id_b": image_b["source_image_id"],
        "expanded_image_id_a": image_a["expanded_image_id"],
        "expanded_image_id_b": image_b["expanded_image_id"],
        "source_phase_a": image_a["source_phase"],
        "source_phase_b": image_b["source_phase"],
        "source_pair_origin": "phase4c_pair_level_mechanism_similarity_table",
        "same_identity": "yes" if source_row["pair_type"] == "same" else "no",
        "pair_label_available": "yes" if source_row["pair_type"] in {"same", "different"} else "no",
        "resnet50_similarity": source_row.get("resnet50_similarity", ""),
        "megadescriptor_similarity": source_row.get("megadescriptor_similarity", ""),
        "descriptor_available": descriptor_available,
    }
    for factor in VISUAL_FACTORS:
        row[f"{factor}_a"] = image_a[factor]
        row[f"{factor}_b"] = image_b[factor]
    row.update(
        {
            "pair_source_phase_type": pair_source_phase_type(image_a["source_phase"], image_b["source_phase"]),
            "pair_annotation_status": pair_annotation_status(image_a, image_b),
            "pair_has_needs_review": "yes" if pair_annotation_status(image_a, image_b) == "needs_review" else "no",
            "pair_has_uncertainty": "yes" if "yes" in {image_a["uncertainty_flag"], image_b["uncertainty_flag"]} else "no",
            "pair_has_missing_mapping": "yes" if has_mapping_caveat(image_a) or has_mapping_caveat(image_b) else "no",
            "pair_visual_completeness_class": visual_completeness(image_a, image_b),
            "pair_pattern_min": ordinal_min(image_a["pattern_visibility"], image_b["pattern_visibility"], "pattern_visibility"),
            "pair_pattern_max": ordinal_max(image_a["pattern_visibility"], image_b["pattern_visibility"], "pattern_visibility"),
            "pair_side_model_class_a": side_a,
            "pair_side_model_class_b": side_b,
            "pair_view_model_class_a": view_a,
            "pair_view_model_class_b": view_b,
            "pair_side_compatible": compatible,
            "pair_has_side_unknown": "yes" if "unknown_or_non_side" in {side_a, side_b} else "no",
            "pair_has_frontal_or_rear": "yes"
            if "frontal_or_rear" in {view_a, view_b}
            or "yes" in {image_a["frontal_or_rear_view"], image_b["frontal_or_rear_view"]}
            else "no",
            "pair_body_fraction_min": ordinal_min(
                image_a["body_fraction_visible"], image_b["body_fraction_visible"], "body_fraction_visible"
            ),
            "pair_has_partial_body": "yes" if "yes" in {image_a["partial_body"], image_b["partial_body"]} else "no",
            "pair_blur_worst": worst(image_a["blur_level"], image_b["blur_level"], "blur_level"),
            "pair_occlusion_worst": worst(image_a["occlusion_level"], image_b["occlusion_level"], "occlusion_level"),
            "pair_lighting_worst": worst(image_a["lighting_condition"], image_b["lighting_condition"], "lighting_condition"),
            "pair_contrast_worst": worst(image_a["contrast_level"], image_b["contrast_level"], "contrast_level"),
            "pair_has_night_ir_artifact": "yes"
            if "yes" in {image_a["night_ir_artifact"], image_b["night_ir_artifact"]}
            else "no",
            "pair_primary_limiting_factor_combined": "__".join(
                sorted({image_a["primary_limiting_factor"], image_b["primary_limiting_factor"]})
            ),
            "pair_modeling_eligible": "yes" if not reasons else "no",
            "pair_exclusion_reason": "none" if not reasons else ";".join(sorted(set(reasons))),
        }
    )
    return row


def build(master_csv: Path, pair_source_csv: Path, output_csv: Path) -> dict[str, int]:
    images = read_csv(master_csv)
    pairs = read_csv(pair_source_csv)
    image_by_expanded_id = {row["expanded_image_id"]: row for row in images}
    rows: list[dict[str, str]] = []
    skipped_missing = 0
    for pair in pairs:
        image_a = image_by_expanded_id.get(pair["image_a_expanded_id"])
        image_b = image_by_expanded_id.get(pair["image_b_expanded_id"])
        if image_a is None or image_b is None:
            skipped_missing += 1
            continue
        rows.append(build_pair_row(pair, image_a, image_b))
    write_csv(output_csv, rows)
    return {
        "input_image_count": len(images),
        "source_pair_count": len(pairs),
        "written_pair_count": len(rows),
        "skipped_missing_image_count": skipped_missing,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master-csv", type=Path, default=MASTER_CSV)
    parser.add_argument("--pair-source-csv", type=Path, default=PAIR_SOURCE_CSV)
    parser.add_argument("--output-csv", type=Path, default=OUTPUT_CSV)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build(args.master_csv.resolve(), args.pair_source_csv.resolve(), args.output_csv.resolve())
    print("Phase 7A 1000-image pair table build complete")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"output_csv: {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
