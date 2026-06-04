#!/usr/bin/env python3
"""Compare CzechLynx first-review and second-review triage labels."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERNAL_MAPPING_CSV = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "czechlynx"
    / "czechlynx_second_review_internal_mapping.csv"
)
SECOND_REVIEW_CSV = (
    PROJECT_ROOT / "data" / "labels" / "czechlynx" / "czechlynx_second_review_blinded.csv"
)
REPORT_PATH = (
    PROJECT_ROOT / "outputs" / "czechlynx" / "qc" / "second_review_consistency_report.txt"
)

TRIAGE_LABELS = ["review-ready", "review-limited", "unidentifiable"]
AGREEMENT_FIELDS = ["pattern_visibility", "side_comparability", "exclusion_reason"]


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_csv_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in df.columns:
        df[column] = df[column].map(clean_cell)
    return df


def format_rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator / denominator:.3f}"


def agreement_summary(df: pd.DataFrame, field: str) -> tuple[int, int, str]:
    original = f"original_{field}"
    if original not in df.columns or field not in df.columns:
        return 0, 0, "missing field"

    complete = df[(df[original] != "") & (df[field] != "")]
    agreed = int((complete[original] == complete[field]).sum())
    total = len(complete)
    return agreed, total, format_rate(agreed, total)


def compute_kappa(first_labels: list[str], second_labels: list[str]) -> str:
    try:
        from sklearn.metrics import cohen_kappa_score
    except ImportError:
        return "skipped; scikit-learn is not available"

    if not first_labels:
        return "n/a; no completed second-review labels"
    return f"{cohen_kappa_score(first_labels, second_labels, labels=TRIAGE_LABELS):.3f}"


def build_report(mapping: pd.DataFrame, second_review: pd.DataFrame) -> str:
    joined = mapping.merge(second_review, on="second_review_id", how="inner")
    reviewed = joined[joined["triage_label"] != ""].copy()

    exact_agreements = int(
        (reviewed["original_triage_label"] == reviewed["triage_label"]).sum()
    )
    total_reviewed = len(reviewed)

    lines: list[str] = []
    lines.append("CzechLynx second-review consistency report")
    lines.append(f"Internal mapping: {INTERNAL_MAPPING_CSV}")
    lines.append(f"Second-review CSV: {SECOND_REVIEW_CSV}")
    lines.append("")
    lines.append("Summary")
    lines.append("-------")
    lines.append(f"Mapping rows: {len(mapping)}")
    lines.append(f"Second-review rows: {len(second_review)}")
    lines.append(f"Joined rows: {len(joined)}")
    lines.append(f"Total reviewed rows: {total_reviewed}")
    lines.append(
        "Exact triage_label agreement: "
        f"{exact_agreements}/{total_reviewed} ({format_rate(exact_agreements, total_reviewed)})"
    )
    lines.append(
        "Cohen's kappa for triage_label: "
        f"{compute_kappa(reviewed['original_triage_label'].tolist(), reviewed['triage_label'].tolist())}"
    )
    lines.append("")
    lines.append("Triage Label Confusion Matrix")
    lines.append("-----------------------------")
    if total_reviewed == 0:
        lines.append("(no completed second-review triage_label values)")
    else:
        confusion = pd.crosstab(
            reviewed["original_triage_label"],
            reviewed["triage_label"],
            rownames=["original"],
            colnames=["second_review"],
            dropna=False,
        )
        confusion = confusion.reindex(index=TRIAGE_LABELS, columns=TRIAGE_LABELS, fill_value=0)
        lines.extend(confusion.to_string().splitlines())

    lines.append("")
    lines.append("Field Agreement")
    lines.append("---------------")
    for field in AGREEMENT_FIELDS:
        agreed, total, rate = agreement_summary(reviewed, field)
        lines.append(f"{field}: {agreed}/{total} ({rate})")

    lines.append("")
    lines.append("Triage Label Disagreements")
    lines.append("--------------------------")
    disagreements = reviewed[
        reviewed["original_triage_label"] != reviewed["triage_label"]
    ].copy()
    if disagreements.empty:
        lines.append("(none)")
    else:
        for _, row in disagreements.iterrows():
            lines.append(
                f"- {row['second_review_id']} / {row['original_pilot_image_id']}: "
                f"original_triage_label={row['original_triage_label']!r}, "
                f"second_review_triage_label={row['triage_label']!r}"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    missing = [
        str(path)
        for path in (INTERNAL_MAPPING_CSV, SECOND_REVIEW_CSV)
        if not path.exists()
    ]
    if missing:
        print("FAIL: required input file(s) missing:")
        for path in missing:
            print(f"  {path}")
        return 1

    mapping = read_csv_clean(INTERNAL_MAPPING_CSV)
    second_review = read_csv_clean(SECOND_REVIEW_CSV)
    required_mapping = {
        "second_review_id",
        "original_pilot_image_id",
        "original_triage_label",
        "original_pattern_visibility",
        "original_side_comparability",
        "original_exclusion_reason",
    }
    required_second = {
        "second_review_id",
        "triage_label",
        "pattern_visibility",
        "side_comparability",
        "exclusion_reason",
    }

    missing_mapping = sorted(required_mapping - set(mapping.columns))
    missing_second = sorted(required_second - set(second_review.columns))
    if missing_mapping or missing_second:
        if missing_mapping:
            print(
                "FAIL: mapping missing required column(s): "
                + ", ".join(missing_mapping)
            )
        if missing_second:
            print(
                "FAIL: second-review CSV missing required column(s): "
                + ", ".join(missing_second)
            )
        return 1

    report = build_report(mapping, second_review)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
