#!/usr/bin/env python3
"""Estimate feasibility for an expanded CzechLynx pilot sample.

This script is planning-only. It does not create expanded labels, copy images,
or write any new data/interim files.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_CSV = (
    PROJECT_ROOT / "data" / "interim" / "czechlynx" / "czechlynx_real_manifest.csv"
)
PILOT_INTERNAL_CSV = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_pilot_internal_with_ids.csv"
)
FINAL_TRIAGE_CSV = (
    PROJECT_ROOT / "data" / "labels" / "czechlynx" / "czechlynx_pilot_triage_final.csv"
)
WORKING_TRIAGE_CSV = (
    PROJECT_ROOT / "data" / "labels" / "czechlynx" / "czechlynx_pilot_triage_working.csv"
)

PLANNING_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "planning"
QC_DIR = PROJECT_ROOT / "outputs" / "czechlynx" / "qc"
SUMMARY_CSV = PLANNING_DIR / "expanded_pilot_feasibility_summary.csv"
REPORT_TXT = QC_DIR / "expanded_pilot_feasibility_report.txt"

MANIFEST_REQUIRED_COLUMNS = ["unique_name", "path", "local_image_path", "image_exists"]
PILOT_INTERNAL_REQUIRED_COLUMNS = [
    "pilot_image_id",
    "unique_name",
    "path",
    "local_image_path",
]
TRIAGE_REQUIRED_COLUMNS = ["pilot_image_id", "triage_label"]

CANDIDATE_DESIGNS = [
    (100, 4),
    (125, 4),
    (150, 3),
    (250, 2),
]
COUNT_THRESHOLDS = [2, 3, 4, 5, 6]
READY_LABEL = "review-ready"
VALID_TRIAGE_LABELS = {"review-ready", "review-limited", "unidentifiable"}


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


def choose_triage_csv() -> Path:
    if FINAL_TRIAGE_CSV.exists():
        return FINAL_TRIAGE_CSV
    return WORKING_TRIAGE_CSV


def validate_inputs(
    manifest: pd.DataFrame,
    pilot_internal: pd.DataFrame,
    triage: pd.DataFrame,
    triage_csv: Path,
) -> None:
    missing_columns = [
        *require_columns(manifest, MANIFEST_REQUIRED_COLUMNS, "manifest"),
        *require_columns(
            pilot_internal, PILOT_INTERNAL_REQUIRED_COLUMNS, "pilot_internal"
        ),
        *require_columns(triage, TRIAGE_REQUIRED_COLUMNS, "triage"),
    ]
    if missing_columns:
        raise ValueError("missing required column(s): " + ", ".join(missing_columns))

    if pilot_internal["pilot_image_id"].duplicated().any():
        duplicate_count = int(pilot_internal["pilot_image_id"].duplicated().sum())
        raise ValueError(
            f"pilot internal map contains {duplicate_count} duplicate pilot_image_id value(s)"
        )

    if triage["pilot_image_id"].duplicated().any():
        duplicate_count = int(triage["pilot_image_id"].duplicated().sum())
        raise ValueError(
            f"{triage_csv.name} contains {duplicate_count} duplicate pilot_image_id value(s)"
        )

    unexpected_labels = sorted(set(triage["triage_label"]) - VALID_TRIAGE_LABELS)
    if unexpected_labels:
        raise ValueError(
            f"{triage_csv.name} contains unexpected triage_label value(s): "
            + ", ".join(unexpected_labels)
        )


def additional_manifest_rows(
    manifest: pd.DataFrame, pilot_internal: pd.DataFrame
) -> tuple[pd.DataFrame, str, str]:
    existing = manifest[truthy_image_exists(manifest["image_exists"])].copy()

    additional_by_path = existing[~existing["path"].isin(set(pilot_internal["path"]))].copy()
    additional_by_local_path = existing[
        ~existing["local_image_path"].isin(set(pilot_internal["local_image_path"]))
    ].copy()

    path_count = len(additional_by_path)
    local_path_count = len(additional_by_local_path)
    if path_count == local_path_count:
        exclusion_note = (
            "Current pilot images were excluded by manifest path; local_image_path "
            f"exclusion matched the same row count ({path_count})."
        )
    else:
        exclusion_note = (
            "Current pilot images were excluded by manifest path; local_image_path "
            f"exclusion produced a different row count ({local_path_count} vs {path_count})."
        )

    return additional_by_path, "path", exclusion_note


def summarize_designs(
    additional_counts: pd.Series, ready_rate: float
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for requested_ids, images_per_id in CANDIDATE_DESIGNS:
        candidate_ids_available = int((additional_counts >= images_per_id).sum())
        total_images = requested_ids * images_per_id
        same_pairs_per_id = math.comb(images_per_id, 2)
        maximum_same_pairs = requested_ids * same_pairs_per_id
        feasible = candidate_ids_available >= requested_ids
        expected_review_ready_images = total_images * ready_rate
        expected_ready_ready_same_pairs = maximum_same_pairs * ready_rate * ready_rate

        rows.append(
            {
                "design": f"{requested_ids} IDs x {images_per_id} images",
                "requested_ids": requested_ids,
                "images_per_id": images_per_id,
                "candidate_ids_available": candidate_ids_available,
                "total_images": total_images,
                "same_pairs_per_id": same_pairs_per_id,
                "maximum_same_pairs": maximum_same_pairs,
                "manual_labeling_workload_images": total_images,
                "feasible_by_image_availability": feasible,
                "current_pilot_review_ready_rate": round(ready_rate, 6),
                "estimated_review_ready_images": round(expected_review_ready_images, 2),
                "estimated_ready_ready_same_pairs": round(
                    expected_ready_ready_same_pairs, 2
                ),
                "estimate_status": "rough feasibility estimate; not a final claim",
            }
        )

    return pd.DataFrame(rows)


def write_report(
    report_path: Path,
    summary: pd.DataFrame,
    triage_csv: Path,
    label_counts: pd.Series,
    ready_rate: float,
    additional_rows: pd.DataFrame,
    additional_counts: pd.Series,
    count_summary: dict[int, int],
    exclusion_key: str,
    exclusion_note: str,
) -> None:
    best_design = summary.sort_values(
        ["feasible_by_image_availability", "maximum_same_pairs"],
        ascending=[False, False],
    ).iloc[0]

    lines = [
        "Expanded CzechLynx Pilot Feasibility Report",
        "============================================",
        "",
        "Purpose",
        "-------",
        "This is a planning-only feasibility report for an expanded CzechLynx pilot.",
        "It does not create expanded labels, copy images, train models, or make final scientific claims.",
        "",
        "Project-rule compliance",
        "-----------------------",
        "- Raw data were not modified.",
        "- Final 200-image labels were read only and were not modified.",
        "- Second-review files were not read or used.",
        "- No expanded labels or data/interim expanded pilot files were created.",
        "- No images were copied.",
        "- Outputs are aggregate planning/QC artifacts under outputs/.",
        "- The working individual ID column is used only for internal aggregate feasibility counts.",
        "",
        "Inputs",
        "------",
        f"- Manifest: {MANIFEST_CSV}",
        f"- Current pilot internal map: {PILOT_INTERNAL_CSV}",
        f"- Triage labels used: {triage_csv}",
        "",
        "Availability summary",
        "--------------------",
        f"- Additional image exclusion key: {exclusion_key}",
        f"- {exclusion_note}",
        f"- Existing additional real images considered: {len(additional_rows)}",
        f"- Working individual IDs with additional images: {additional_counts.index.nunique()}",
    ]

    for threshold, id_count in count_summary.items():
        lines.append(f"- IDs with at least {threshold} additional image(s): {id_count}")

    lines.extend(
        [
            "",
            "Current pilot label distribution",
            "--------------------------------",
        ]
    )
    for label, count in label_counts.sort_index().items():
        lines.append(f"- {label}: {int(count)}")
    lines.append(f"- Review-ready rate used for rough estimates: {ready_rate:.3f}")

    lines.extend(
        [
            "",
            "Candidate design feasibility",
            "----------------------------",
        ]
    )
    for _, row in summary.iterrows():
        lines.append(
            "- "
            f"{row['design']}: feasible={row['feasible_by_image_availability']}; "
            f"candidate IDs available={row['candidate_ids_available']}; "
            f"manual workload={row['manual_labeling_workload_images']} images; "
            f"maximum same pairs={row['maximum_same_pairs']}; "
            f"estimated ready_ready same pairs={row['estimated_ready_ready_same_pairs']}"
        )

    lines.extend(
        [
            "",
            "Planning recommendation",
            "-----------------------",
            f"Recommended feasibility default: {best_design['design']}.",
            "This design is recommended because it is feasible by aggregate image availability",
            "and has the highest maximum same-pair yield among the candidate designs.",
            "The readiness-based values are rough planning estimates only.",
            "",
            "Output files",
            "------------",
            f"- Summary CSV: {SUMMARY_CSV}",
            f"- QC report: {REPORT_TXT}",
            "",
            "RESULT: PASS",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    try:
        triage_csv = choose_triage_csv()
        for path in (MANIFEST_CSV, PILOT_INTERNAL_CSV, triage_csv):
            if not path.exists():
                return fail(f"required input not found: {path}")

        manifest = read_csv_clean(MANIFEST_CSV)
        pilot_internal = read_csv_clean(PILOT_INTERNAL_CSV)
        triage = read_csv_clean(triage_csv)
        validate_inputs(manifest, pilot_internal, triage, triage_csv)

        additional_rows, exclusion_key, exclusion_note = additional_manifest_rows(
            manifest, pilot_internal
        )
        additional_counts = additional_rows["unique_name"].value_counts()
        count_summary = {
            threshold: int((additional_counts >= threshold).sum())
            for threshold in COUNT_THRESHOLDS
        }

        label_counts = triage["triage_label"].value_counts()
        ready_rate = float((triage["triage_label"] == READY_LABEL).mean())
        summary = summarize_designs(additional_counts, ready_rate)

        PLANNING_DIR.mkdir(parents=True, exist_ok=True)
        summary.to_csv(SUMMARY_CSV, index=False)
        write_report(
            REPORT_TXT,
            summary,
            triage_csv,
            label_counts,
            ready_rate,
            additional_rows,
            additional_counts,
            count_summary,
            exclusion_key,
            exclusion_note,
        )

        print("Expanded CzechLynx pilot feasibility planning")
        print(f"Manifest: {MANIFEST_CSV}")
        print(f"Current pilot internal map: {PILOT_INTERNAL_CSV}")
        print(f"Triage labels used: {triage_csv}")
        print(f"Wrote summary CSV: {SUMMARY_CSV}")
        print(f"Wrote QC report: {REPORT_TXT}")
        print()
        print("Aggregate additional image availability:")
        for threshold, id_count in count_summary.items():
            print(f"  IDs with >= {threshold} additional image(s): {id_count}")
        print()
        print("Candidate designs:")
        for _, row in summary.iterrows():
            print(
                f"  {row['design']}: feasible={row['feasible_by_image_availability']}, "
                f"maximum same pairs={row['maximum_same_pairs']}, "
                "estimated ready_ready same pairs="
                f"{row['estimated_ready_ready_same_pairs']}"
            )
        print()
        print("RESULT: PASS")
        return 0
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
