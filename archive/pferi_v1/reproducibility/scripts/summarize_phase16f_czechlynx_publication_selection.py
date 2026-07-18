#!/usr/bin/env python3
"""Summarize Phase 16F CzechLynx selected 3000 for publication tables.

This script reads the constrained-selection manifest and writes compact tables
and a methods/results note. It does not relabel images and does not turn the
selection into identity validation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTED = (
    PROJECT_ROOT
    / "outputs/phase16/phase16f_czechlynx_constrained_selection/phase16f_czechlynx_selected_3000_manifest.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16f_czechlynx_publication_summary"

METRIC_SUMMARY_CSV = "phase16f_czechlynx_publication_metric_summary.csv"
VIEWPOINT_SUMMARY_CSV = "phase16f_czechlynx_publication_viewpoint_summary.csv"
GROUP_SUMMARY_CSV = "phase16f_czechlynx_publication_balance_group_summary.csv"
CURRENT_FINAL_SUMMARY_CSV = "phase16f_czechlynx_publication_current_final_summary.csv"
METHODS_SNIPPET_MD = "phase16f_czechlynx_publication_methods_snippet.md"
REPORT_MD = "phase16f_czechlynx_publication_summary.md"
AUDIT_JSON = "phase16f_czechlynx_publication_summary_audit.json"

METRICS = [
    "phase16f_selection_score",
    "final_candidate_score",
    "iqa_quality_proxy_score",
    "clip_side_view_score",
    "clip_viewpoint_confidence",
    "iqa_musiq_crop_score",
    "iqa_topiq_nr_crop_score",
    "iqa_brisque_crop_score",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def numeric(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(pd.NA, index=df.index, dtype="Float64")
    return pd.to_numeric(df[column], errors="coerce")


def summarize_metric_frame(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows = []
    grouped = df.groupby(group_cols, dropna=False) if group_cols else [((), df)]
    for key, group in grouped:
        if not isinstance(key, tuple):
            key = (key,)
        row = {column: value for column, value in zip(group_cols, key)}
        row["count"] = int(len(group))
        for metric in METRICS:
            if metric not in df.columns:
                continue
            series = numeric(group, metric).dropna()
            row[f"{metric}_mean"] = float(series.mean()) if len(series) else None
            row[f"{metric}_p10"] = float(series.quantile(0.10)) if len(series) else None
            row[f"{metric}_p50"] = float(series.quantile(0.50)) if len(series) else None
            row[f"{metric}_p90"] = float(series.quantile(0.90)) if len(series) else None
        rows.append(row)
    return pd.DataFrame(rows)


def build_metric_summary(selected: pd.DataFrame) -> pd.DataFrame:
    return summarize_metric_frame(selected, ["phase16f_selection_bucket"]).sort_values(
        "count",
        ascending=False,
    )


def build_viewpoint_summary(selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for bucket, group in selected.groupby("phase16f_selection_bucket", dropna=False):
        total = len(group)
        counts = group["clip_viewpoint_label"].fillna("missing").astype(str).value_counts()
        for label, count in counts.items():
            rows.append(
                {
                    "phase16f_selection_bucket": bucket,
                    "clip_viewpoint_label": label,
                    "count": int(count),
                    "rate_within_bucket": float(count / total) if total else 0.0,
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["phase16f_selection_bucket", "count"],
        ascending=[True, False],
    )


def build_balance_group_summary(selected: pd.DataFrame) -> pd.DataFrame:
    selected = selected.copy()
    for column in [
        "phase16f_selection_score",
        "final_candidate_score",
        "iqa_quality_proxy_score",
        "clip_side_view_score",
    ]:
        if column not in selected.columns:
            selected[column] = pd.NA
    return (
        selected.groupby("phase16f_balance_group", dropna=False)
        .agg(
            selected_count=("candidate_id", "count"),
            strict_core_count=(
                "phase16f_selection_bucket",
                lambda s: int((s.astype(str) == "strict_core").sum()),
            ),
            current_high_final_count=(
                "already_in_current_high_final",
                lambda s: int(bool_series(s).sum()),
            ),
            mean_selection_score=("phase16f_selection_score", "mean"),
            median_final_candidate_score=("final_candidate_score", "median"),
            median_iqa_quality_proxy_score=("iqa_quality_proxy_score", "median"),
            median_clip_side_view_score=("clip_side_view_score", "median"),
        )
        .reset_index()
        .sort_values(["selected_count", "mean_selection_score"], ascending=[False, False])
    )


def build_current_final_summary(selected: pd.DataFrame) -> pd.DataFrame:
    selected = selected.copy()
    selected["already_in_current_high_final_bool"] = bool_series(selected["already_in_current_high_final"])
    rows = []
    for bucket, group in selected.groupby("phase16f_selection_bucket", dropna=False):
        rows.append(
            {
                "phase16f_selection_bucket": bucket,
                "selected_count": int(len(group)),
                "current_high_final_count": int(group["already_in_current_high_final_bool"].sum()),
                "current_high_final_rate": float(group["already_in_current_high_final_bool"].mean())
                if len(group)
                else 0.0,
            }
        )
    rows.append(
        {
            "phase16f_selection_bucket": "all_selected",
            "selected_count": int(len(selected)),
            "current_high_final_count": int(selected["already_in_current_high_final_bool"].sum()),
            "current_high_final_rate": float(selected["already_in_current_high_final_bool"].mean())
            if len(selected)
            else 0.0,
        }
    )
    return pd.DataFrame(rows)


def write_methods_snippet(output_dir: Path, audit: dict) -> None:
    text = f"""# Phase 16F CzechLynx Methods Snippet

Phase 16F used Phase 16E pretrained proxy scores as a candidate-screening layer,
not as identity evidence. We first required successful image loading, valid
scoring, and membership in the recalibrated CzechLynx balanced tier. Candidate
rows were ranked by a composite of final candidate score, image-quality proxy,
side-view proxy, and a small retention bonus for rows already present in the
previous high-confidence working set. Rows were then selected under an
identity-like path-group cap to reduce dominance by any single folder/individual
proxy. The resulting set contains {audit['selected_rows']:,} images across
{audit['balance_group_count']:,} balance groups, with a maximum of
{audit['max_balance_group_count']:,} selected rows in any one group.

This output is a constrained candidate foundation for manual audit calibration.
It is not automatic individual identification, not a new descriptor, and not a
final validation set until manual audit is complete.
"""
    (output_dir / METHODS_SNIPPET_MD).write_text(text, encoding="utf-8")


def write_report(output_dir: Path, audit: dict, metric_summary: pd.DataFrame) -> None:
    lines = [
        "# Phase 16F CzechLynx Publication Summary",
        "",
        "This summary converts the constrained 3000-row CzechLynx selection into compact paper-ready tables.",
        "",
        "## Key Counts",
        "",
        f"- Selected rows: {audit['selected_rows']:,}.",
        f"- Selection buckets: {audit['bucket_counts']}.",
        f"- Balance groups: {audit['balance_group_count']:,}.",
        f"- Max rows in one balance group: {audit['max_balance_group_count']:,}.",
        f"- Current high-final retained rows: {audit['current_high_final_count']:,}.",
        "",
        "## Bucket Metric Medians",
        "",
        "| bucket | count | final p50 | IQA p50 | side p50 | selection p50 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in metric_summary.iterrows():
        lines.append(
            "| `{bucket}` | {count:,} | {final:.4f} | {iqa:.4f} | {side:.4f} | {score:.4f} |".format(
                bucket=row["phase16f_selection_bucket"],
                count=int(row["count"]),
                final=float(row.get("final_candidate_score_p50", 0)),
                iqa=float(row.get("iqa_quality_proxy_score_p50", 0)),
                side=float(row.get("clip_side_view_score_p50", 0)),
                score=float(row.get("phase16f_selection_score_p50", 0)),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The selected 3000 are a constrained high-confidence candidate foundation, not a simple top-score list.",
            "- The selected set can support paper tables about candidate filtering, score distributions, and audit readiness.",
            "- Identity claims remain out of scope until downstream Re-ID and manual audit evidence are available.",
            "",
            "## Files",
            "",
            f"- `{METRIC_SUMMARY_CSV}`",
            f"- `{VIEWPOINT_SUMMARY_CSV}`",
            f"- `{GROUP_SUMMARY_CSV}`",
            f"- `{CURRENT_FINAL_SUMMARY_CSV}`",
            f"- `{METHODS_SNIPPET_MD}`",
            f"- `{AUDIT_JSON}`",
        ]
    )
    (output_dir / REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_publication_summary(selected_csv: Path, output_dir: Path) -> dict:
    if not selected_csv.exists():
        raise FileNotFoundError(selected_csv)
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = pd.read_csv(selected_csv, low_memory=False)
    required = {"candidate_id", "phase16f_selection_bucket", "phase16f_balance_group"}
    missing = sorted(required - set(selected.columns))
    if missing:
        raise ValueError(f"Missing selected manifest columns: {missing}")

    metric_summary = build_metric_summary(selected)
    viewpoint_summary = build_viewpoint_summary(selected)
    balance_summary = build_balance_group_summary(selected)
    current_summary = build_current_final_summary(selected)

    metric_summary.to_csv(output_dir / METRIC_SUMMARY_CSV, index=False)
    viewpoint_summary.to_csv(output_dir / VIEWPOINT_SUMMARY_CSV, index=False)
    balance_summary.to_csv(output_dir / GROUP_SUMMARY_CSV, index=False)
    current_summary.to_csv(output_dir / CURRENT_FINAL_SUMMARY_CSV, index=False)

    audit = {
        "created_at": utc_now(),
        "selected_csv": str(selected_csv),
        "selected_rows": int(len(selected)),
        "unique_candidate_id": bool(selected["candidate_id"].is_unique),
        "bucket_counts": selected["phase16f_selection_bucket"].value_counts().to_dict(),
        "balance_group_count": int(selected["phase16f_balance_group"].nunique()),
        "max_balance_group_count": int(selected["phase16f_balance_group"].value_counts().max())
        if len(selected)
        else 0,
        "current_high_final_count": int(bool_series(selected["already_in_current_high_final"]).sum())
        if "already_in_current_high_final" in selected.columns
        else 0,
        "claim_boundary": "Publication summary only; no identity assignment and no final validation before manual audit",
    }
    (output_dir / AUDIT_JSON).write_text(json.dumps(audit, indent=2), encoding="utf-8")
    write_methods_snippet(output_dir, audit)
    write_report(output_dir, audit, metric_summary)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, default=DEFAULT_SELECTED)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = build_publication_summary(args.selected, args.output_dir)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
