#!/usr/bin/env python3
"""Build Phase 16F CzechLynx constrained high-confidence selection.

Phase 16F starts from Phase 16E recalibrated candidate scores. It does not
perform simple top-3000 selection. The default policy uses the balanced
recalibrated tier, applies an identity-like path-group cap, records rejected
rows and reasons, and emits an audit package for manual calibration.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_recalibrated_czechlynx_scores/phase16e_recalibrated_candidate_scores.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16f_czechlynx_constrained_selection"

SELECTED_CSV = "phase16f_czechlynx_selected_3000_manifest.csv"
REJECTED_CSV = "phase16f_czechlynx_selection_rejected_pool.csv"
BUCKET_SUMMARY_CSV = "phase16f_czechlynx_selection_bucket_summary.csv"
CURRENT_RECHECK_CSV = "phase16f_czechlynx_current_high_final_retention.csv"
MANUAL_AUDIT_CSV = "phase16f_czechlynx_manual_audit_sample.csv"
GROUP_SUMMARY_CSV = "phase16f_czechlynx_balance_group_summary.csv"
AUDIT_JSON = "phase16f_czechlynx_selection_audit.json"
REPORT_MD = "phase16f_czechlynx_selection_report.md"

DEFAULT_TARGET_COUNT = 3000
DEFAULT_MAX_PER_BALANCE_GROUP = 40
DEFAULT_MANUAL_AUDIT_PER_BUCKET = 40
RANDOM_SEED = 1606

REQUIRED_COLUMNS = [
    "candidate_id",
    "image_key",
    "image_load_success",
    "scoring_valid_for_selection",
    "final_candidate_score",
    "iqa_quality_proxy_score",
    "clip_side_view_score",
    "clip_viewpoint_label",
    "clip_viewpoint_prob_partial_or_occluded",
    "clip_viewpoint_prob_unclear",
    "clip_viewpoint_prob_frontal",
    "clip_viewpoint_prob_rear",
    "already_in_current_high_final",
    "strict_recalibrated_eligible",
    "balanced_recalibrated_eligible",
    "broad_recalibrated_eligible",
]

PUBLIC_OUTPUT_COLUMNS = [
    "phase16f_selection_rank",
    "phase16f_selected",
    "phase16f_selection_bucket",
    "phase16f_selection_score",
    "phase16f_balance_group",
    "phase16f_rejection_reason",
    "candidate_id",
    "phase16_expanded_candidate_index",
    "source_name",
    "target_quadrant",
    "species_label",
    "scientific_name",
    "environment_axis",
    "candidate_role",
    "source_priority",
    "image_key",
    "already_in_current_high_final",
    "strict_recalibrated_eligible",
    "balanced_recalibrated_eligible",
    "broad_recalibrated_eligible",
    "recommended_recalibrated_eligible",
    "hard_recalibration_valid",
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
    "iqa_musiq_crop_score",
    "iqa_topiq_nr_crop_score",
    "iqa_brisque_crop_score",
    "image_width",
    "image_height",
    "crop_width",
    "crop_height",
    "source_mode",
    "image_uri",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(0.0, index=df.index)
    return pd.to_numeric(df[column], errors="coerce").fillna(0.0)


def percentile_score(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() <= 1:
        return pd.Series(0.0, index=series.index)
    return numeric.rank(method="average", pct=True).fillna(0.0)


def derive_balance_group(image_key: object) -> str:
    """Use the CzechLynx identity-like path segment as a balancing proxy."""
    parts = str(image_key or "").split("/")
    if len(parts) >= 4 and parts[2]:
        return parts[2]
    return "unknown"


def validate_input(df: pd.DataFrame) -> None:
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required Phase 16F input columns: {missing}")
    if df["candidate_id"].duplicated().any():
        duplicate_count = int(df["candidate_id"].duplicated().sum())
        raise ValueError(f"candidate_id must be unique; duplicate_count={duplicate_count}")


def compute_selection_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add quality-preserving constrained-selection scores."""
    out = df.copy()
    final_pct = percentile_score(numeric_series(out, "final_candidate_score"))
    iqa_pct = percentile_score(numeric_series(out, "iqa_quality_proxy_score"))
    side_pct = percentile_score(numeric_series(out, "clip_side_view_score"))
    current_bonus = bool_series(out.get("already_in_current_high_final", pd.Series(False, index=out.index))).astype(float)

    partial_penalty = numeric_series(out, "clip_viewpoint_prob_partial_or_occluded")
    unclear_penalty = numeric_series(out, "clip_viewpoint_prob_unclear")
    front_rear_penalty = numeric_series(out, "clip_viewpoint_prob_frontal") + numeric_series(out, "clip_viewpoint_prob_rear")

    out["phase16f_final_score_percentile"] = final_pct
    out["phase16f_iqa_percentile"] = iqa_pct
    out["phase16f_side_view_percentile"] = side_pct
    out["phase16f_balance_group"] = out["image_key"].map(derive_balance_group)
    out["phase16f_selection_score"] = (
        0.45 * final_pct
        + 0.25 * iqa_pct
        + 0.20 * side_pct
        + 0.10 * current_bonus
        - 0.05 * partial_penalty
        - 0.05 * unclear_penalty
        - 0.03 * front_rear_penalty
    )
    return out


def hard_valid_mask(df: pd.DataFrame) -> pd.Series:
    if "hard_recalibration_valid" in df.columns:
        return bool_series(df["hard_recalibration_valid"])
    return (
        bool_series(df["image_load_success"])
        & bool_series(df["scoring_valid_for_selection"])
        & pd.to_numeric(df["final_candidate_score"], errors="coerce").notna()
        & pd.to_numeric(df["iqa_quality_proxy_score"], errors="coerce").notna()
        & pd.to_numeric(df["clip_side_view_score"], errors="coerce").notna()
    )


def assign_candidate_buckets(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    strict = bool_series(out["strict_recalibrated_eligible"])
    balanced = bool_series(out["balanced_recalibrated_eligible"])
    broad = bool_series(out["broad_recalibrated_eligible"])
    current = bool_series(out["already_in_current_high_final"])
    hard_valid = hard_valid_mask(out)
    high_score_threshold = numeric_series(out, "final_candidate_score").quantile(0.75)
    high_score_uncertain = (
        numeric_series(out, "final_candidate_score").ge(high_score_threshold)
        & (
            numeric_series(out, "clip_viewpoint_prob_partial_or_occluded").ge(0.50)
            | numeric_series(out, "clip_viewpoint_prob_unclear").ge(0.50)
        )
    )

    out["phase16f_selection_bucket"] = "outside_recalibrated_pool"
    out.loc[~hard_valid, "phase16f_selection_bucket"] = "hard_invalid"
    out.loc[high_score_uncertain & hard_valid, "phase16f_selection_bucket"] = "high_score_uncertain_or_partial"
    out.loc[broad & hard_valid, "phase16f_selection_bucket"] = "broad_reserve"
    out.loc[current & ~balanced & hard_valid, "phase16f_selection_bucket"] = "current_high_final_not_balanced"
    out.loc[balanced & hard_valid, "phase16f_selection_bucket"] = "balanced_only"
    out.loc[strict & hard_valid, "phase16f_selection_bucket"] = "strict_core"
    return out


def selection_sort(df: pd.DataFrame) -> pd.DataFrame:
    pool_priority = {
        "strict_core": 0,
        "balanced_only": 1,
        "current_high_final_not_balanced": 2,
        "broad_reserve": 3,
        "high_score_uncertain_or_partial": 4,
        "outside_recalibrated_pool": 5,
        "hard_invalid": 6,
    }
    out = df.copy()
    out["phase16f_pool_priority"] = out["phase16f_selection_bucket"].map(pool_priority).fillna(99)
    return out.sort_values(
        ["phase16f_pool_priority", "phase16f_selection_score", "final_candidate_score", "candidate_id"],
        ascending=[True, False, False, True],
    )


def choose_with_group_cap(
    candidates: pd.DataFrame,
    already_selected_ids: set[str],
    group_counts: dict[str, int],
    target_count: int,
    max_per_balance_group: int,
) -> list[str]:
    chosen: list[str] = []
    for row in candidates.itertuples(index=False):
        candidate_id = str(getattr(row, "candidate_id"))
        if candidate_id in already_selected_ids:
            continue
        group = str(getattr(row, "phase16f_balance_group"))
        if group_counts.get(group, 0) >= max_per_balance_group:
            continue
        chosen.append(candidate_id)
        already_selected_ids.add(candidate_id)
        group_counts[group] = group_counts.get(group, 0) + 1
        if len(already_selected_ids) >= target_count:
            break
    return chosen


def build_constrained_selection(
    df: pd.DataFrame,
    target_count: int = DEFAULT_TARGET_COUNT,
    max_per_balance_group: int = DEFAULT_MAX_PER_BALANCE_GROUP,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    ordered = selection_sort(df)
    selected_ids: set[str] = set()
    group_counts: dict[str, int] = {}

    balanced_pool = ordered[ordered["phase16f_selection_bucket"].isin({"strict_core", "balanced_only"})]
    choose_with_group_cap(
        balanced_pool,
        selected_ids,
        group_counts,
        target_count=target_count,
        max_per_balance_group=max_per_balance_group,
    )

    if len(selected_ids) < target_count:
        reserve_pool = ordered[ordered["phase16f_selection_bucket"].eq("broad_reserve")]
        choose_with_group_cap(
            reserve_pool,
            selected_ids,
            group_counts,
            target_count=target_count,
            max_per_balance_group=max_per_balance_group,
        )

    out = ordered.copy()
    out["phase16f_selected"] = out["candidate_id"].astype(str).isin(selected_ids)
    out["phase16f_selection_rank"] = ""
    selected_order = out[out["phase16f_selected"]].sort_values(
        ["phase16f_pool_priority", "phase16f_selection_score", "final_candidate_score", "candidate_id"],
        ascending=[True, False, False, True],
    )
    rank_map = {candidate_id: rank for rank, candidate_id in enumerate(selected_order["candidate_id"], start=1)}
    out.loc[out["phase16f_selected"], "phase16f_selection_rank"] = out.loc[
        out["phase16f_selected"], "candidate_id"
    ].map(rank_map)

    out["phase16f_rejection_reason"] = ""
    hard_valid = hard_valid_mask(out)
    selected = out["phase16f_selected"]
    out.loc[~selected & ~hard_valid, "phase16f_rejection_reason"] = "failed_hard_validity"
    out.loc[
        ~selected & hard_valid & out["phase16f_selection_bucket"].eq("outside_recalibrated_pool"),
        "phase16f_rejection_reason",
    ] = "outside_recalibrated_pool"
    out.loc[
        ~selected
        & hard_valid
        & out["phase16f_selection_bucket"].isin({"strict_core", "balanced_only", "broad_reserve"}),
        "phase16f_rejection_reason",
    ] = "below_constrained_selection_cut_or_group_cap"
    out.loc[
        ~selected & hard_valid & out["phase16f_selection_bucket"].eq("current_high_final_not_balanced"),
        "phase16f_rejection_reason",
    ] = "current_high_final_not_balanced_reaudit"
    out.loc[
        ~selected & hard_valid & out["phase16f_selection_bucket"].eq("high_score_uncertain_or_partial"),
        "phase16f_rejection_reason",
    ] = "high_score_uncertain_or_partial_audit_pool"

    selected_df = out[out["phase16f_selected"]].copy()
    rejected_df = out[~out["phase16f_selected"]].copy()
    audit = {
        "created_at": utc_now(),
        "input_rows": int(len(df)),
        "target_count": int(target_count),
        "selected_rows": int(len(selected_df)),
        "selection_status": "PASS" if len(selected_df) == target_count else "REVIEW_INSUFFICIENT_ROWS",
        "max_per_balance_group": int(max_per_balance_group),
        "selected_unique_candidate_id": bool(selected_df["candidate_id"].is_unique),
        "selected_duplicate_image_uri_count": int(selected_df["image_uri"].duplicated().sum())
        if "image_uri" in selected_df.columns
        else None,
        "selected_balance_group_count": int(selected_df["phase16f_balance_group"].nunique()),
        "selected_max_balance_group_count": int(selected_df["phase16f_balance_group"].value_counts().max())
        if not selected_df.empty
        else 0,
        "selected_bucket_counts": selected_df["phase16f_selection_bucket"].value_counts().to_dict(),
        "input_bucket_counts": df["phase16f_selection_bucket"].value_counts().to_dict(),
        "broad_reserve_used_count": int(selected_df["phase16f_selection_bucket"].eq("broad_reserve").sum()),
        "current_high_final_input_count": int(bool_series(df["already_in_current_high_final"]).sum()),
        "current_high_final_selected_count": int(bool_series(selected_df["already_in_current_high_final"]).sum()),
        "claim_boundary": "Phase 16F constrained candidate selection only; no identity assignment and no automatic final validation",
        "selection_policy": (
            "balanced_recalibrated_eligible primary pool, broad_recalibrated_eligible reserve only if needed, "
            "identity-like path-group cap, IQA/side-view/final-score composite ranking"
        ),
    }
    return selected_df, rejected_df, audit


def public_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in PUBLIC_OUTPUT_COLUMNS if column in df.columns]


def build_bucket_summary(df: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    input_counts = df["phase16f_selection_bucket"].value_counts()
    selected_counts = selected["phase16f_selection_bucket"].value_counts()
    rows = []
    for bucket in sorted(set(input_counts.index) | set(selected_counts.index)):
        rows.append(
            {
                "phase16f_selection_bucket": bucket,
                "input_count": int(input_counts.get(bucket, 0)),
                "selected_count": int(selected_counts.get(bucket, 0)),
                "selected_rate_within_bucket": (
                    float(selected_counts.get(bucket, 0) / input_counts.get(bucket, 1))
                    if input_counts.get(bucket, 0)
                    else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def build_group_summary(selected: pd.DataFrame) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    return (
        selected.groupby("phase16f_balance_group", dropna=False)
        .agg(
            selected_count=("candidate_id", "count"),
            mean_selection_score=("phase16f_selection_score", "mean"),
            mean_final_candidate_score=("final_candidate_score", "mean"),
            current_high_final_count=("already_in_current_high_final", lambda s: int(bool_series(s).sum())),
        )
        .reset_index()
        .sort_values(["selected_count", "mean_selection_score"], ascending=[False, False])
    )


def build_current_high_final_retention(df: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    selected_ids = set(selected["candidate_id"].astype(str))
    current = df[bool_series(df["already_in_current_high_final"])].copy()
    current["phase16f_selected"] = current["candidate_id"].astype(str).isin(selected_ids)
    rows = []
    for bucket, group in current.groupby("phase16f_selection_bucket", dropna=False):
        rows.append(
            {
                "phase16f_selection_bucket": bucket,
                "current_high_final_count": int(len(group)),
                "selected_count": int(group["phase16f_selected"].sum()),
                "selected_rate": float(group["phase16f_selected"].mean()) if len(group) else 0.0,
                "median_final_candidate_score": float(group["final_candidate_score"].median()),
                "median_iqa_quality_proxy_score": float(group["iqa_quality_proxy_score"].median()),
                "median_clip_side_view_score": float(group["clip_side_view_score"].median()),
            }
        )
    return pd.DataFrame(rows).sort_values("current_high_final_count", ascending=False)


def manual_audit_sample(
    df: pd.DataFrame,
    per_bucket: int = DEFAULT_MANUAL_AUDIT_PER_BUCKET,
    random_seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    samples = []
    wanted = [
        "strict_core",
        "balanced_only",
        "current_high_final_not_balanced",
        "broad_reserve",
        "high_score_uncertain_or_partial",
    ]
    for bucket in wanted:
        bucket_rows = df[df["phase16f_selection_bucket"].eq(bucket)]
        if bucket_rows.empty:
            continue
        n = min(per_bucket, len(bucket_rows))
        samples.append(
            bucket_rows.sample(n=n, random_state=random_seed)
            .sort_values("phase16f_selection_score", ascending=False)
        )
    if not samples:
        return df.head(0).copy()
    sample = pd.concat(samples, ignore_index=True)
    sample["phase16f_manual_audit_reason"] = sample["phase16f_selection_bucket"].map(
        {
            "strict_core": "confirm high-score strict-core evidence",
            "balanced_only": "calibrate balanced-only inclusion boundary",
            "current_high_final_not_balanced": "recheck old high-final row that failed balanced tier",
            "broad_reserve": "estimate reserve-pool rescue quality",
            "high_score_uncertain_or_partial": "inspect high score under uncertain or partial viewpoint proxy",
        }
    )
    return sample


def write_report(output_dir: Path, audit: dict[str, Any]) -> None:
    selected_counts = audit["selected_bucket_counts"]
    lines = [
        "# Phase 16F CzechLynx Constrained Selection",
        "",
        "This output selects a CzechLynx candidate foundation from Phase 16E recalibrated scores.",
        "It is not simple top-3000 and not identity assignment.",
        "",
        "## Summary",
        "",
        f"- Input rows: {audit['input_rows']:,}.",
        f"- Target selected rows: {audit['target_count']:,}.",
        f"- Selected rows: {audit['selected_rows']:,}.",
        f"- Status: `{audit['selection_status']}`.",
        f"- Max per balance group: {audit['max_per_balance_group']}.",
        f"- Selected balance groups: {audit['selected_balance_group_count']:,}.",
        f"- Largest selected balance group count: {audit['selected_max_balance_group_count']:,}.",
        f"- Broad reserve rows used: {audit['broad_reserve_used_count']:,}.",
        "",
        "## Selected Bucket Counts",
        "",
        "| bucket | selected rows |",
        "| --- | ---: |",
    ]
    for bucket, count in selected_counts.items():
        lines.append(f"| `{bucket}` | {count:,} |")
    lines.extend(
        [
            "",
            "## Policy",
            "",
            "```text",
            audit["selection_policy"],
            "```",
            "",
            "## Boundary",
            "",
            audit["claim_boundary"],
            "",
            "## Files",
            "",
            f"- `{SELECTED_CSV}`",
            f"- `{REJECTED_CSV}`",
            f"- `{BUCKET_SUMMARY_CSV}`",
            f"- `{CURRENT_RECHECK_CSV}`",
            f"- `{MANUAL_AUDIT_CSV}`",
            f"- `{GROUP_SUMMARY_CSV}`",
            f"- `{AUDIT_JSON}`",
        ]
    )
    (output_dir / REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target-count", type=int, default=DEFAULT_TARGET_COUNT)
    parser.add_argument("--max-per-balance-group", type=int, default=DEFAULT_MAX_PER_BALANCE_GROUP)
    parser.add_argument("--manual-audit-per-bucket", type=int, default=DEFAULT_MANUAL_AUDIT_PER_BUCKET)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input, low_memory=False)
    validate_input(df)
    df = assign_candidate_buckets(compute_selection_scores(df))

    selected, rejected, audit = build_constrained_selection(
        df,
        target_count=args.target_count,
        max_per_balance_group=args.max_per_balance_group,
    )
    audit["input_path"] = str(args.input)
    audit["output_dir"] = str(args.output_dir)

    selected[public_columns(selected)].to_csv(args.output_dir / SELECTED_CSV, index=False)
    rejected[public_columns(rejected)].to_csv(args.output_dir / REJECTED_CSV, index=False)
    build_bucket_summary(df, selected).to_csv(args.output_dir / BUCKET_SUMMARY_CSV, index=False)
    build_group_summary(selected).to_csv(args.output_dir / GROUP_SUMMARY_CSV, index=False)
    build_current_high_final_retention(df, selected).to_csv(args.output_dir / CURRENT_RECHECK_CSV, index=False)
    manual_audit = manual_audit_sample(
        df,
        per_bucket=args.manual_audit_per_bucket,
        random_seed=RANDOM_SEED,
    )
    manual_audit[public_columns(manual_audit) + ["phase16f_manual_audit_reason"]].to_csv(
        args.output_dir / MANUAL_AUDIT_CSV,
        index=False,
    )
    (args.output_dir / AUDIT_JSON).write_text(json.dumps(audit, indent=2), encoding="utf-8")
    write_report(args.output_dir, audit)

    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
