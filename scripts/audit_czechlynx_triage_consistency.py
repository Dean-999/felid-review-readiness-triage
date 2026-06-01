#!/usr/bin/env python3
"""Audit CzechLynx pilot triage working labels for consistency."""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKING_CSV = (
    PROJECT_ROOT / "data" / "labels" / "czechlynx" / "czechlynx_pilot_triage_working.csv"
)

REQUIRED_COLUMNS = [
    "pilot_image_id",
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

REQUIRED_LABELED_FIELDS = [
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
]

ALLOWED_VALUES = {
    "triage_label": {"review-ready", "review-limited", "unidentifiable"},
    "blur_level": {"none", "mild", "moderate", "severe"},
    "occlusion_level": {"none", "mild", "moderate", "severe"},
    "lighting_condition": {"daylight", "twilight", "night_ir", "low_light", "unknown"},
    "night_ir_artifact": {"none", "mild", "moderate", "severe", "not_applicable"},
    "visible_side": {"left", "right", "frontal", "rear", "mixed", "unknown"},
    "side_comparability": {"high", "medium", "low", "none"},
    "visible_region": {
        "full_body",
        "flank",
        "torso",
        "shoulder",
        "hip",
        "head",
        "tail",
        "legs",
        "partial_body",
        "unknown",
    },
    "pattern_visibility": {"high", "medium", "low", "none"},
    "body_fraction_visible": {"0-25", "25-50", "50-75", "75-100"},
    "distance_to_camera": {"close", "medium", "far", "unknown"},
    "camera_angle": {"side", "oblique", "frontal", "rear", "unknown"},
    "reviewer_confidence": {"high", "medium", "low"},
    "uncertainty_flag": {"yes", "no"},
    "exclusion_reason": {
        "",
        "severe_blur",
        "too_far",
        "too_small",
        "major_occlusion",
        "pattern_not_visible",
        "side_unknown",
        "body_fragment_only",
        "night_ir_artifact",
        "silhouette_only",
        "non_target_species",
        "other",
    },
}

RULES = [
    (
        "Rule 4",
        "triage_label == review-ready and exclusion_reason is not blank",
        ["triage_label", "exclusion_reason"],
        lambda row: row["triage_label"] == "review-ready" and row["exclusion_reason"] != "",
    ),
    (
        "Rule 5",
        "triage_label == review-ready and uncertainty_flag == yes",
        ["triage_label", "uncertainty_flag"],
        lambda row: row["triage_label"] == "review-ready" and row["uncertainty_flag"] == "yes",
    ),
    (
        "Rule 6",
        "triage_label == review-ready and pattern_visibility is low or none",
        ["triage_label", "pattern_visibility"],
        lambda row: row["triage_label"] == "review-ready"
        and row["pattern_visibility"] in {"low", "none"},
    ),
    (
        "Rule 7",
        "triage_label == review-ready and side_comparability is low or none",
        ["triage_label", "side_comparability"],
        lambda row: row["triage_label"] == "review-ready"
        and row["side_comparability"] in {"low", "none"},
    ),
    (
        "Rule 8",
        "triage_label == unidentifiable and exclusion_reason is blank",
        ["triage_label", "exclusion_reason"],
        lambda row: row["triage_label"] == "unidentifiable" and row["exclusion_reason"] == "",
    ),
    (
        "Rule 9",
        "visible_region == full_body and body_fraction_visible is 0-25",
        ["visible_region", "body_fraction_visible"],
        lambda row: row["visible_region"] == "full_body"
        and row["body_fraction_visible"] == "0-25",
    ),
    (
        "Rule 10",
        "visible_region in head, tail, legs and body_fraction_visible is 75-100",
        ["visible_region", "body_fraction_visible"],
        lambda row: row["visible_region"] in {"head", "tail", "legs"}
        and row["body_fraction_visible"] == "75-100",
    ),
    (
        "Rule 11",
        "pattern_visibility == none and triage_label == review-ready",
        ["pattern_visibility", "triage_label"],
        lambda row: row["pattern_visibility"] == "none" and row["triage_label"] == "review-ready",
    ),
    (
        "Rule 12",
        "blur_level == severe and triage_label == review-ready",
        ["blur_level", "triage_label"],
        lambda row: row["blur_level"] == "severe" and row["triage_label"] == "review-ready",
    ),
    (
        "Rule 13",
        "night_ir_artifact != not_applicable when lighting_condition is not night_ir",
        ["night_ir_artifact", "lighting_condition"],
        lambda row: row["lighting_condition"] != "night_ir"
        and row["night_ir_artifact"] != "not_applicable",
    ),
    (
        "Rule 14",
        "night_ir_artifact == not_applicable when lighting_condition == night_ir",
        ["night_ir_artifact", "lighting_condition"],
        lambda row: row["lighting_condition"] == "night_ir"
        and row["night_ir_artifact"] == "not_applicable",
    ),
    (
        "Rule 15",
        "exclusion_reason == severe_blur but blur_level is none or mild",
        ["exclusion_reason", "blur_level"],
        lambda row: row["exclusion_reason"] == "severe_blur"
        and row["blur_level"] in {"none", "mild"},
    ),
    (
        "Rule 16",
        "exclusion_reason == body_fragment_only but visible_region == full_body",
        ["exclusion_reason", "visible_region"],
        lambda row: row["exclusion_reason"] == "body_fragment_only"
        and row["visible_region"] == "full_body",
    ),
    (
        "Rule 17",
        "notes are blank where uncertainty_flag == yes",
        ["uncertainty_flag", "notes"],
        lambda row: row["uncertainty_flag"] == "yes" and row["notes"] == "",
    ),
    (
        "Rule 18",
        "notes are blank for review-limited rows",
        ["triage_label", "notes"],
        lambda row: row["triage_label"] == "review-limited" and row["notes"] == "",
    ),
    (
        "Rule 19",
        "notes are blank for unidentifiable rows",
        ["triage_label", "notes"],
        lambda row: row["triage_label"] == "unidentifiable" and row["notes"] == "",
    ),
]


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def row_id(row: pd.Series) -> str:
    pilot_id = clean_cell(row.get("pilot_image_id", ""))
    if pilot_id:
        return pilot_id
    return f"csv_row_{int(row.name) + 2}"


def format_fields(row: pd.Series, fields: Iterable[str]) -> str:
    return ", ".join(f"{field}={clean_cell(row.get(field, ''))!r}" for field in fields)


def print_section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> int:
    if not WORKING_CSV.exists():
        print(f"FAIL: working CSV not found: {WORKING_CSV}")
        return 1

    df = pd.read_csv(WORKING_CSV, dtype=str, keep_default_na=False)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]

    print("CzechLynx pilot triage consistency audit")
    print(f"CSV: {WORKING_CSV}")

    if missing_columns:
        print_section("Required Columns")
        print("Missing required columns:")
        for column in missing_columns:
            print(f"  [VIOLATION] {column}")
        print()
        print("RESULT: WARNINGS FOUND")
        return 1

    for column in REQUIRED_COLUMNS:
        df[column] = df[column].map(clean_cell)

    labeled = df[df["triage_label"] != ""].copy()

    print_section("Summary")
    print(f"Total rows: {len(df)}")
    print(f"Total labeled rows: {len(labeled)}")

    print()
    print("Label counts:")
    label_counts = Counter(labeled["triage_label"])
    if label_counts:
        for label, count in sorted(label_counts.items()):
            print(f"  {label}: {count}")
    else:
        print("  (none)")

    missing_required_fields: list[tuple[str, str]] = []
    for _, row in labeled.iterrows():
        for field in REQUIRED_LABELED_FIELDS:
            if row[field] == "":
                missing_required_fields.append((row_id(row), field))

    allowed_value_violations: list[tuple[str, str, str, str]] = []
    for _, row in labeled.iterrows():
        for field, allowed in ALLOWED_VALUES.items():
            value = row[field]
            if value == "" and field != "exclusion_reason":
                continue
            if value not in allowed:
                allowed_text = ", ".join("'blank'" if item == "" else item for item in sorted(allowed))
                allowed_value_violations.append((row_id(row), field, value, allowed_text))

    print_section("Required Field Completeness")
    if missing_required_fields:
        for pilot_id, field in missing_required_fields:
            print(f"  [VIOLATION] {pilot_id}: {field} is blank")
    else:
        print("  [PASS] Required fields are non-empty for all labeled rows.")

    print_section("Allowed-Value Violations")
    if allowed_value_violations:
        for pilot_id, field, value, allowed_text in allowed_value_violations:
            print(
                f"  [VIOLATION] {pilot_id}: {field}={value!r}; "
                f"allowed values: {allowed_text}"
            )
    else:
        print("  [PASS] All labeled values are in the allowed sets.")

    warnings_by_rule: dict[str, list[str]] = defaultdict(list)
    for _, row in labeled.iterrows():
        for rule_id, description, fields, predicate in RULES:
            if predicate(row):
                warnings_by_rule[f"{rule_id}: {description}"].append(
                    f"{row_id(row)} ({format_fields(row, fields)})"
                )

    print_section("Logical Warnings")
    if warnings_by_rule:
        for rule, warnings in warnings_by_rule.items():
            print(f"  [WARNING] {rule}")
            for warning in warnings:
                print(f"    - {warning}")
    else:
        print("  [PASS] No logical warnings found.")

    has_findings = bool(
        missing_required_fields or allowed_value_violations or warnings_by_rule
    )
    print()
    if has_findings:
        print("RESULT: WARNINGS FOUND")
        return 0

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
