#!/usr/bin/env python3
"""Receive and analyze Phase 16E Bobcat score outputs.

Use this after Bobcat Phase 16E merged scores return from Kaggle/Colab. The
script validates the handoff, runs the existing Phase 16E recalibration tier
logic, preserves Bobcat source-tier metadata, and writes transfer-stress
summary tables. It does not evaluate Bobcat identity accuracy.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.recalibrate_phase16e_candidate_scores import apply_profile_tiers


DEFAULT_INPUT_CANDIDATES = [
    PROJECT_ROOT / "outputs/phase16/phase16e_bobcat_candidate_model_filter/phase16e_bobcat_scores_00000_19999_merged.csv",
    PROJECT_ROOT / "outputs/phase16/phase16e_candidate_model_filter/phase16e_bobcat_scores_00000_19999_merged.csv",
    PROJECT_ROOT / "outputs/phase16/phase16e_candidate_model_filter/phase16e2_bobcat_scores_00000_19999_merged.csv",
]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16e_bobcat_score_analysis"
CZECHLYNX_REFERENCE = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_czechlynx_analysis/phase16e_czechlynx_metric_quantiles.csv"
)

RECALIBRATED_CSV = "phase16e_bobcat_recalibrated_scores.csv"
SOURCE_TIER_SUMMARY_CSV = "phase16e_bobcat_source_tier_summary.csv"
VIEWPOINT_SUMMARY_CSV = "phase16e_bobcat_viewpoint_summary.csv"
METRIC_SUMMARY_CSV = "phase16e_bobcat_metric_summary.csv"
TRANSFER_COMPARISON_CSV = "phase16e_bobcat_vs_czechlynx_metric_comparison.csv"
REPORT_MD = "phase16e_bobcat_score_analysis_report.md"
AUDIT_JSON = "phase16e_bobcat_score_analysis_audit.json"

REQUIRED_COLUMNS = [
    "candidate_id",
    "target_quadrant",
    "species_label",
    "scientific_name",
    "source_mode",
    "image_uri",
    "image_load_success",
    "rejection_reason",
    "selection_eligible",
    "final_candidate_score",
    "iqa_quality_proxy_score",
    "clip_side_view_score",
    "clip_viewpoint_label",
    "clip_viewpoint_confidence",
    "clip_viewpoint_prob_left_side",
    "clip_viewpoint_prob_right_side",
    "clip_viewpoint_prob_frontal",
    "clip_viewpoint_prob_rear",
    "clip_viewpoint_prob_partial_or_occluded",
    "clip_viewpoint_prob_unclear",
    "pose_enabled",
    "pose_model_name",
    "pose_success",
    "pose_failure_reason",
    "pose_num_keypoints",
    "pose_mean_keypoint_confidence",
    "pose_valid_keypoint_fraction",
    "pose_body_coverage_score",
    "pose_orientation_proxy",
    "pose_side_view_proxy",
    "pose_front_rear_proxy",
    "pose_partial_body_proxy",
    "pose_quality_score",
    "pose_fallback_scoring_used",
]

BOBCAT_METADATA_COLUMNS = [
    "source_tier",
    "source_role",
    "source_dataset",
    "identity_label_available",
    "topup_reason",
]

FORBIDDEN_SENSITIVE_COLUMNS = [
    "unique_name",
    "identity",
    "identity_label",
    "individual_id",
    "animal_id",
    "lynx_id",
    "latitude",
    "longitude",
    "trap_id",
    "location",
    "location_id",
    "cell_code",
    "camera_id",
]

METRICS = [
    "final_candidate_score",
    "iqa_quality_proxy_score",
    "clip_side_view_score",
    "clip_viewpoint_confidence",
    "clip_viewpoint_prob_partial_or_occluded",
    "clip_viewpoint_prob_unclear",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def default_input_path() -> Path:
    for path in DEFAULT_INPUT_CANDIDATES:
        if path.exists():
            return path
    return DEFAULT_INPUT_CANDIDATES[0]


def build_required_column_report(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "missing_required_columns": sorted(set(REQUIRED_COLUMNS) - set(df.columns)),
        "missing_bobcat_metadata_columns": sorted(set(BOBCAT_METADATA_COLUMNS) - set(df.columns)),
        "forbidden_sensitive_columns_present": sorted(
            set(FORBIDDEN_SENSITIVE_COLUMNS).intersection(df.columns)
        ),
    }


def numeric(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(pd.NA, index=df.index, dtype="Float64")
    return pd.to_numeric(df[column], errors="coerce")


def summarize_metrics(df: pd.DataFrame, group_cols: list[str] | None = None) -> pd.DataFrame:
    rows = []
    grouped = df.groupby(group_cols, dropna=False) if group_cols else [((), df)]
    for key, group in grouped:
        if group_cols and not isinstance(key, tuple):
            key = (key,)
        row = {}
        if group_cols:
            row.update({column: value for column, value in zip(group_cols, key)})
        row["count"] = int(len(group))
        row["image_load_success_count"] = int(bool_series(group["image_load_success"]).sum()) if "image_load_success" in group else 0
        row["strict_recalibrated_eligible_count"] = int(bool_series(group["strict_recalibrated_eligible"]).sum()) if "strict_recalibrated_eligible" in group else 0
        row["balanced_recalibrated_eligible_count"] = int(bool_series(group["balanced_recalibrated_eligible"]).sum()) if "balanced_recalibrated_eligible" in group else 0
        row["broad_recalibrated_eligible_count"] = int(bool_series(group["broad_recalibrated_eligible"]).sum()) if "broad_recalibrated_eligible" in group else 0
        for metric in METRICS:
            if metric not in group.columns:
                continue
            series = numeric(group, metric).dropna()
            row[f"{metric}_mean"] = float(series.mean()) if len(series) else None
            row[f"{metric}_p10"] = float(series.quantile(0.10)) if len(series) else None
            row[f"{metric}_p50"] = float(series.quantile(0.50)) if len(series) else None
            row[f"{metric}_p90"] = float(series.quantile(0.90)) if len(series) else None
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_by_source_tier(df: pd.DataFrame) -> pd.DataFrame:
    if "source_tier" not in df.columns:
        df = df.copy()
        df["source_tier"] = "missing"
    return summarize_metrics(df, ["source_tier"]).sort_values("source_tier")


def summarize_viewpoint(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tier, group in df.groupby("source_tier", dropna=False) if "source_tier" in df.columns else [("missing", df)]:
        total = len(group)
        counts = group["clip_viewpoint_label"].fillna("missing").astype(str).value_counts()
        for label, count in counts.items():
            rows.append(
                {
                    "source_tier": tier,
                    "clip_viewpoint_label": label,
                    "count": int(count),
                    "rate_within_source_tier": float(count / total) if total else 0.0,
                }
            )
    return pd.DataFrame(rows).sort_values(["source_tier", "count"], ascending=[True, False])


def build_transfer_comparison(bobcat: pd.DataFrame, czechlynx_reference: Path) -> pd.DataFrame:
    if not czechlynx_reference.exists():
        return pd.DataFrame()
    ref = pd.read_csv(czechlynx_reference)
    ref = ref[ref["metric"].isin(METRICS)].set_index("metric")
    rows = []
    for metric in METRICS:
        if metric not in bobcat.columns or metric not in ref.index:
            continue
        series = numeric(bobcat, metric).dropna()
        rows.append(
            {
                "metric": metric,
                "bobcat_p10": float(series.quantile(0.10)) if len(series) else None,
                "bobcat_p50": float(series.quantile(0.50)) if len(series) else None,
                "bobcat_p90": float(series.quantile(0.90)) if len(series) else None,
                "czechlynx_p10": float(ref.loc[metric, "p10"]),
                "czechlynx_p50": float(ref.loc[metric, "p50"]),
                "czechlynx_p90": float(ref.loc[metric, "p90"]),
                "bobcat_minus_czechlynx_p50": (
                    float(series.quantile(0.50)) - float(ref.loc[metric, "p50"])
                    if len(series)
                    else None
                ),
            }
        )
    return pd.DataFrame(rows)


def write_report(output_dir: Path, audit: dict[str, Any], source_summary: pd.DataFrame) -> None:
    lines = [
        "# Phase 16E Bobcat Score Analysis",
        "",
        "This report validates returned Bobcat Phase 16E scores and prepares them for Phase 16F transfer-stress selection.",
        "It does not evaluate Bobcat identity accuracy.",
        "",
        "## Handoff Status",
        "",
        f"- Input rows: {audit['input_rows']:,}.",
        f"- Candidate IDs unique: `{audit['candidate_id_unique']}`.",
        f"- Missing required columns: `{audit['missing_required_columns']}`.",
        f"- Missing Bobcat metadata columns: `{audit['missing_bobcat_metadata_columns']}`.",
        f"- Forbidden sensitive columns present: `{audit['forbidden_sensitive_columns_present']}`.",
        f"- Image load success rows: {audit['image_load_success_count']:,}.",
        f"- Strict eligible: {audit['strict_recalibrated_eligible_count']:,}.",
        f"- Balanced eligible: {audit['balanced_recalibrated_eligible_count']:,}.",
        f"- Broad eligible: {audit['broad_recalibrated_eligible_count']:,}.",
        "",
        "## Source Tier Summary",
        "",
        "| source tier | rows | balanced eligible | broad eligible | final p50 | IQA p50 | side p50 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in source_summary.iterrows():
        lines.append(
            "| `{tier}` | {count:,} | {balanced:,} | {broad:,} | {final:.4f} | {iqa:.4f} | {side:.4f} |".format(
                tier=row.get("source_tier", "missing"),
                count=int(row.get("count", 0)),
                balanced=int(row.get("balanced_recalibrated_eligible_count", 0)),
                broad=int(row.get("broad_recalibrated_eligible_count", 0)),
                final=float(row.get("final_candidate_score_p50", 0) or 0),
                iqa=float(row.get("iqa_quality_proxy_score_p50", 0) or 0),
                side=float(row.get("clip_side_view_score_p50", 0) or 0),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            audit["claim_boundary"],
            "",
            "## Files",
            "",
            f"- `{RECALIBRATED_CSV}`",
            f"- `{SOURCE_TIER_SUMMARY_CSV}`",
            f"- `{VIEWPOINT_SUMMARY_CSV}`",
            f"- `{METRIC_SUMMARY_CSV}`",
            f"- `{TRANSFER_COMPARISON_CSV}`",
            f"- `{AUDIT_JSON}`",
        ]
    )
    (output_dir / REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_bobcat_score_analysis(
    input_csv: Path,
    output_dir: Path,
    source_audit_json: Path | None = None,
    czechlynx_reference: Path = CZECHLYNX_REFERENCE,
) -> dict[str, Any]:
    if not input_csv.exists():
        raise FileNotFoundError(input_csv)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(input_csv, low_memory=False)
    report = build_required_column_report(raw)

    recalibrated, recalibration_audit = apply_profile_tiers(raw)
    recalibrated.to_csv(output_dir / RECALIBRATED_CSV, index=False)

    source_summary = summarize_by_source_tier(recalibrated)
    metric_summary = summarize_metrics(recalibrated)
    viewpoint_summary = summarize_viewpoint(recalibrated)
    transfer_comparison = build_transfer_comparison(recalibrated, czechlynx_reference)

    source_summary.to_csv(output_dir / SOURCE_TIER_SUMMARY_CSV, index=False)
    metric_summary.to_csv(output_dir / METRIC_SUMMARY_CSV, index=False)
    viewpoint_summary.to_csv(output_dir / VIEWPOINT_SUMMARY_CSV, index=False)
    transfer_comparison.to_csv(output_dir / TRANSFER_COMPARISON_CSV, index=False)

    source_audit = None
    if source_audit_json and source_audit_json.exists():
        source_audit = json.loads(source_audit_json.read_text(encoding="utf-8"))

    audit = {
        "created_at": utc_now(),
        "input_csv": str(input_csv),
        "source_audit_json": str(source_audit_json) if source_audit_json else None,
        "source_audit_status": source_audit.get("status") if isinstance(source_audit, dict) else None,
        "input_rows": int(len(raw)),
        "candidate_id_unique": bool(raw["candidate_id"].is_unique) if "candidate_id" in raw.columns else False,
        "duplicate_candidate_id_count": int(raw["candidate_id"].duplicated().sum()) if "candidate_id" in raw.columns else None,
        "duplicate_image_uri_count": int(raw["image_uri"].duplicated().sum()) if "image_uri" in raw.columns else None,
        **report,
        "image_load_success_count": int(bool_series(raw["image_load_success"]).sum()) if "image_load_success" in raw else 0,
        "strict_recalibrated_eligible_count": int(bool_series(recalibrated["strict_recalibrated_eligible"]).sum()),
        "balanced_recalibrated_eligible_count": int(bool_series(recalibrated["balanced_recalibrated_eligible"]).sum()),
        "broad_recalibrated_eligible_count": int(bool_series(recalibrated["broad_recalibrated_eligible"]).sum()),
        "source_tier_counts": recalibrated["source_tier"].astype(str).value_counts().to_dict()
        if "source_tier" in recalibrated.columns
        else {},
        "recalibration_audit": recalibration_audit,
        "claim_boundary": "Bobcat Phase 16E score analysis only; review-readiness transfer stress, not Bobcat identity accuracy",
    }
    (output_dir / AUDIT_JSON).write_text(json.dumps(audit, indent=2), encoding="utf-8")
    write_report(output_dir, audit, source_summary)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_input_path())
    parser.add_argument("--source-audit-json", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--czechlynx-reference", type=Path, default=CZECHLYNX_REFERENCE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = build_bobcat_score_analysis(
        input_csv=args.input,
        output_dir=args.output_dir,
        source_audit_json=args.source_audit_json,
        czechlynx_reference=args.czechlynx_reference,
    )
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
