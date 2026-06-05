#!/usr/bin/env python3
"""Audit CzechLynx expanded 125x4 triage labeling progress and consistency."""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LABEL_DIR = PROJECT_ROOT / "data" / "labels" / "czechlynx"
WORKING_CSV = LABEL_DIR / "czechlynx_expanded_125x4_triage_working.csv"
BLINDED_CSV = LABEL_DIR / "czechlynx_expanded_125x4_triage_blinded.csv"
REPORT_TXT = (
    PROJECT_ROOT
    / "outputs"
    / "czechlynx"
    / "qc"
    / "czechlynx_expanded_125x4_triage_consistency_report.txt"
)

EXPECTED_ROWS = 500

REQUIRED_COLUMNS = [
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
    "metadata_completeness",
    "reviewer_confidence",
    "uncertainty_flag",
    "exclusion_reason",
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
    "metadata_completeness": {"complete", "partial", "missing", "unknown"},
    "reviewer_confidence": {"high", "medium", "low"},
    "uncertainty_flag": {"yes", "no"},
    "exclusion_reason": {
        "none",
        "severe_blur",
        "moderate_blur",
        "too_far",
        "too_small",
        "major_occlusion",
        "pattern_not_visible",
        "side_unknown",
        "body_fragment_only",
        "night_ir_artifact",
        "silhouette_only",
        "non_target_species",
        "overexposed",
        "low_contrast",
        "partial_body",
        "frontal_or_rear_view",
        "other",
    },
}

FRAGMENT_REGIONS = {"head", "tail", "legs", "body_fragment", "partial_body"}
PARTIAL_OCCLUSION_LEVELS = {"partial", "mild", "moderate"}
MAJOR_OCCLUSION_LEVELS = {"major", "severe"}

RULES: list[tuple[str, str, list[str], Callable[[pd.Series], bool]]] = [
    (
        "Rule 1",
        "triage_label == review-ready and uncertainty_flag == yes",
        ["triage_label", "uncertainty_flag"],
        lambda row: row["triage_label"] == "review-ready" and row["uncertainty_flag"] == "yes",
    ),
    (
        "Rule 2",
        "triage_label == review-ready and exclusion_reason != none",
        ["triage_label", "exclusion_reason"],
        lambda row: row["triage_label"] == "review-ready"
        and row["exclusion_reason"] != "none",
    ),
    (
        "Rule 3",
        "triage_label == review-ready and pattern_visibility in none/low",
        ["triage_label", "pattern_visibility"],
        lambda row: row["triage_label"] == "review-ready"
        and row["pattern_visibility"] in {"low", "none"},
    ),
    (
        "Rule 4",
        "triage_label == review-ready and blur_level == severe",
        ["triage_label", "blur_level"],
        lambda row: row["triage_label"] == "review-ready" and row["blur_level"] == "severe",
    ),
    (
        "Rule 5",
        "triage_label == review-ready and occlusion_level == major",
        ["triage_label", "occlusion_level"],
        lambda row: row["triage_label"] == "review-ready"
        and row["occlusion_level"] in MAJOR_OCCLUSION_LEVELS,
    ),
    (
        "Rule 6",
        "triage_label == review-ready and visible_region in head/tail/legs/body_fragment",
        ["triage_label", "visible_region"],
        lambda row: row["triage_label"] == "review-ready"
        and row["visible_region"] in FRAGMENT_REGIONS,
    ),
    (
        "Rule 7",
        "triage_label == unidentifiable and exclusion_reason == none",
        ["triage_label", "exclusion_reason"],
        lambda row: row["triage_label"] == "unidentifiable"
        and row["exclusion_reason"] == "none",
    ),
    (
        "Rule 8",
        "triage_label == unidentifiable and pattern_visibility == high",
        ["triage_label", "pattern_visibility"],
        lambda row: row["triage_label"] == "unidentifiable"
        and row["pattern_visibility"] == "high",
    ),
    (
        "Rule 9",
        "triage_label == review-limited and exclusion_reason == none",
        ["triage_label", "exclusion_reason"],
        lambda row: row["triage_label"] == "review-limited"
        and row["exclusion_reason"] == "none",
    ),
    (
        "Rule 10",
        "exclusion_reason == severe_blur but blur_level is none/mild",
        ["exclusion_reason", "blur_level"],
        lambda row: row["exclusion_reason"] == "severe_blur"
        and row["blur_level"] in {"none", "mild"},
    ),
    (
        "Rule 11",
        "exclusion_reason == major_occlusion but occlusion_level is none/partial",
        ["exclusion_reason", "occlusion_level"],
        lambda row: row["exclusion_reason"] == "major_occlusion"
        and row["occlusion_level"] in {"none", "partial", *PARTIAL_OCCLUSION_LEVELS},
    ),
    (
        "Rule 12",
        "exclusion_reason == pattern_not_visible but pattern_visibility != none",
        ["exclusion_reason", "pattern_visibility"],
        lambda row: row["exclusion_reason"] == "pattern_not_visible"
        and row["pattern_visibility"] != "none",
    ),
    (
        "Rule 13",
        "visible_region == full_body and body_fraction_visible == 0-25",
        ["visible_region", "body_fraction_visible"],
        lambda row: row["visible_region"] == "full_body"
        and row["body_fraction_visible"] == "0-25",
    ),
    (
        "Rule 14",
        "body_fraction_visible == 75-100 and visible_region in head/tail/legs/body_fragment",
        ["body_fraction_visible", "visible_region"],
        lambda row: row["body_fraction_visible"] == "75-100"
        and row["visible_region"] in FRAGMENT_REGIONS,
    ),
]

COUNT_FIELDS = [
    "triage_label",
    "pattern_visibility",
    "side_comparability",
    "exclusion_reason",
    "uncertainty_flag",
]


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def row_id(row: pd.Series) -> str:
    image_id = clean_cell(row.get("expanded_image_id", ""))
    if image_id:
        return image_id
    return f"csv_row_{int(row.name) + 2}"


def format_fields(row: pd.Series, fields: Iterable[str]) -> str:
    return ", ".join(f"{field}={clean_cell(row.get(field, ''))!r}" for field in fields)


def resolve_input_csv() -> Path | None:
    if WORKING_CSV.exists():
        return WORKING_CSV
    if BLINDED_CSV.exists():
        return BLINDED_CSV
    return None


def print_count_section(title: str, counts: Counter[str]) -> list[str]:
    lines = [title, "-" * len(title)]
    if counts:
        for label, count in sorted(counts.items()):
            lines.append(f"  {label}: {count}")
    else:
        lines.append("  (none)")
    return lines


def run_audit() -> tuple[int, list[str]]:
    lines: list[str] = []
    input_csv = resolve_input_csv()

    lines.append("CzechLynx expanded 125x4 triage consistency audit")
    if input_csv is None:
        lines.append("FAIL: neither working nor blinded CSV found.")
        lines.append(f"  working: {WORKING_CSV}")
        lines.append(f"  blinded: {BLINDED_CSV}")
        lines.append("")
        lines.append("RESULT: FAIL")
        return 1, lines

    lines.append(f"CSV: {input_csv}")
    if input_csv == BLINDED_CSV:
        lines.append("Note: working CSV not found; using blinded CSV fallback.")

    df = pd.read_csv(input_csv, dtype=str, keep_default_na=False)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]

    if missing_columns:
        lines.append("")
        lines.append("Required Columns")
        lines.append("----------------")
        for column in missing_columns:
            lines.append(f"  [VIOLATION] missing column: {column}")
        lines.append("")
        lines.append("RESULT: FAIL")
        return 1, lines

    for column in REQUIRED_COLUMNS:
        df[column] = df[column].map(clean_cell)

    if len(df) != EXPECTED_ROWS:
        lines.append("")
        lines.append("Row Count")
        lines.append("---------")
        lines.append(
            f"  [VIOLATION] total rows is {len(df)}; expected {EXPECTED_ROWS}."
        )
        lines.append("")
        lines.append("RESULT: FAIL")
        return 1, lines

    labeled = df[df["triage_label"] != ""].copy()
    unlabeled_count = len(df) - len(labeled)

    lines.append("")
    lines.append("Summary")
    lines.append("-------")
    lines.append(f"Total rows: {len(df)}")
    lines.append(f"Labeled rows: {len(labeled)}")
    lines.append(f"Unlabeled rows: {unlabeled_count}")

    for field in COUNT_FIELDS:
        lines.append("")
        lines.extend(print_count_section(f"{field} counts", Counter(labeled[field])))

    missing_required_fields: list[tuple[str, str]] = []
    for _, row in labeled.iterrows():
        for field in REQUIRED_LABELED_FIELDS:
            if row[field] == "":
                missing_required_fields.append((row_id(row), field))

    allowed_value_violations: list[tuple[str, str, str, str]] = []
    for _, row in labeled.iterrows():
        for field, allowed in ALLOWED_VALUES.items():
            value = row[field]
            if value == "":
                continue
            if value not in allowed:
                allowed_text = ", ".join(sorted(allowed))
                allowed_value_violations.append((row_id(row), field, value, allowed_text))

    lines.append("")
    lines.append("Required Field Completeness")
    lines.append("---------------------------")
    if missing_required_fields:
        for image_id, field in missing_required_fields:
            lines.append(f"  [VIOLATION] {image_id}: {field} is blank")
    else:
        lines.append("  [PASS] Required fields are non-empty for all labeled rows.")

    lines.append("")
    lines.append("Allowed-Value Violations")
    lines.append("------------------------")
    if allowed_value_violations:
        for image_id, field, value, allowed_text in allowed_value_violations:
            lines.append(
                f"  [VIOLATION] {image_id}: {field}={value!r}; "
                f"allowed values: {allowed_text}"
            )
    else:
        lines.append("  [PASS] All labeled values are in the allowed sets.")

    warnings_by_rule: dict[str, list[str]] = defaultdict(list)
    for _, row in labeled.iterrows():
        for rule_id, description, fields, predicate in RULES:
            if predicate(row):
                warnings_by_rule[f"{rule_id}: {description}"].append(
                    f"{row_id(row)} ({format_fields(row, fields)})"
                )

    lines.append("")
    lines.append("Logical Warnings")
    lines.append("----------------")
    if warnings_by_rule:
        for rule, warnings in warnings_by_rule.items():
            lines.append(f"  [WARNING] {rule}")
            for warning in warnings:
                lines.append(f"    - {warning}")
    else:
        lines.append("  [PASS] No logical warnings found.")

    has_failures = bool(missing_required_fields or allowed_value_violations)
    has_warnings = bool(warnings_by_rule)

    lines.append("")
    if has_failures:
        lines.append("RESULT: FAIL")
        return 1, lines
    if has_warnings:
        lines.append("RESULT: WARNINGS FOUND")
        return 0, lines

    lines.append("RESULT: PASS")
    return 0, lines


def main() -> int:
    exit_code, report_lines = run_audit()
    report_text = "\n".join(report_lines) + "\n"

    print(report_text, end="")

    REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_TXT.write_text(report_text, encoding="utf-8")
    print(f"Wrote: {REPORT_TXT}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
