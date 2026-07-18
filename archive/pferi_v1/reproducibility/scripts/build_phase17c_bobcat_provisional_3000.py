#!/usr/bin/env python3
"""Build Phase17C Bobcat provisional 3000 algorithm-prep manifest.

The output is a provisional review-readiness foundation, not a final Bobcat
identity dataset. The default policy selects a clean Tier 1 backbone plus a
small Tier 2 transfer sentinel so downstream algorithms cannot silently overfit
to the easiest primary-source subset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_phase17b_bobcat_transfer_stress import prepare_bobcat_frame


DEFAULT_INPUT = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_bobcat_score_analysis/phase16e_bobcat_recalibrated_scores.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase17/phase17c_bobcat_provisional_3000"

SELECTED_CSV = "phase17c_bobcat_provisional_3000_manifest.csv"
REJECTED_CSV = "phase17c_bobcat_provisional_3000_rejected_pool.csv"
BUCKET_SUMMARY_CSV = "phase17c_bobcat_selection_bucket_summary.csv"
GROUP_SUMMARY_CSV = "phase17c_bobcat_balance_group_summary.csv"
ROUTE_SUMMARY_CSV = "phase17c_bobcat_selected_route_summary.csv"
MANUAL_AUDIT_CSV = "phase17c_bobcat_manual_audit_expansion_sheet.csv"
AUDIT_JSON = "phase17c_bobcat_provisional_3000_audit.json"
REPORT_MD = "phase17c_bobcat_provisional_3000_report.md"

DEFAULT_TARGET_COUNT = 3000
DEFAULT_TRANSFER_SENTINEL_COUNT = 300
DEFAULT_MAX_PER_BALANCE_GROUP = 80
DEFAULT_MANUAL_AUDIT_PER_BUCKET = 40
RANDOM_SEED = 1703

PUBLIC_OUTPUT_COLUMNS = [
    "phase17c_selection_rank",
    "phase17c_selected",
    "phase17c_selection_role",
    "phase17c_selection_bucket",
    "phase17c_selection_score",
    "phase17c_balance_group_hash",
    "phase17c_rejection_reason",
    "candidate_id",
    "source_tier",
    "source_role",
    "source_dataset",
    "topup_reason",
    "target_quadrant",
    "species_label",
    "scientific_name",
    "source_mode",
    "image_uri",
    "phase17b_stratum",
    "phase17b_route",
    "strict_recalibrated_eligible",
    "balanced_recalibrated_eligible",
    "broad_recalibrated_eligible",
    "final_candidate_score",
    "iqa_quality_proxy_score",
    "clip_side_view_score",
    "clip_viewpoint_label",
    "clip_viewpoint_confidence",
    "clip_viewpoint_prob_partial_or_occluded",
    "clip_viewpoint_prob_unclear",
    "md_geometry_score",
    "image_width",
    "image_height",
    "crop_width",
    "crop_height",
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


def balance_group_hash(row: pd.Series) -> str:
    key = str(row.get("original_source_key") or row.get("image_uri") or row.get("candidate_id") or "")
    parts = key.split("/")
    raw_group = "/".join(parts[:2]) if len(parts) >= 2 else key[:80]
    digest = hashlib.sha1(raw_group.encode("utf-8")).hexdigest()[:12]
    return f"bg_{digest}"


def validate_input(raw: pd.DataFrame) -> None:
    if "candidate_id" not in raw.columns:
        raise ValueError("Phase17C input missing candidate_id")
    if raw["candidate_id"].duplicated().any():
        duplicate_count = int(raw["candidate_id"].duplicated().sum())
        raise ValueError(f"candidate_id must be unique; duplicate_count={duplicate_count}")


def compute_selection_scores(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["phase17c_final_percentile"] = percentile_score(numeric_series(out, "final_candidate_score"))
    out["phase17c_iqa_percentile"] = percentile_score(numeric_series(out, "iqa_quality_proxy_score"))
    out["phase17c_side_percentile"] = percentile_score(numeric_series(out, "clip_side_view_score"))
    out["phase17c_geometry_percentile"] = percentile_score(numeric_series(out, "md_geometry_score"))
    partial = numeric_series(out, "clip_viewpoint_prob_partial_or_occluded")
    unclear = numeric_series(out, "clip_viewpoint_prob_unclear")
    out["phase17c_balance_group_hash"] = out.apply(balance_group_hash, axis=1)
    out["phase17c_selection_score"] = (
        0.45 * out["phase17c_final_percentile"]
        + 0.20 * out["phase17c_iqa_percentile"]
        + 0.15 * out["phase17c_side_percentile"]
        + 0.15 * out["phase17c_geometry_percentile"]
        + 0.05 * numeric_series(out, "clip_viewpoint_confidence")
        - 0.05 * partial
        - 0.05 * unclear
    )
    return out


def assign_selection_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    tier1 = out["source_tier"].astype(str).eq("1")
    tier2 = out["source_tier"].astype(str).eq("2")
    strict = bool_series(out["strict_recalibrated_eligible"])
    balanced = bool_series(out["balanced_recalibrated_eligible"])
    broad = bool_series(out["broad_recalibrated_eligible"])

    out["phase17c_selection_bucket"] = "outside_review_ready_pool"
    out.loc[broad, "phase17c_selection_bucket"] = "broad_reserve"
    out.loc[tier2 & broad, "phase17c_selection_bucket"] = "tier2_broad_transfer_reserve"
    out.loc[tier1 & broad, "phase17c_selection_bucket"] = "tier1_broad_reserve"
    out.loc[tier2 & balanced & ~strict, "phase17c_selection_bucket"] = "tier2_balanced_transfer_support"
    out.loc[tier2 & strict, "phase17c_selection_bucket"] = "tier2_strict_transfer_sentinel"
    out.loc[tier1 & balanced & ~strict, "phase17c_selection_bucket"] = "tier1_balanced_support"
    out.loc[tier1 & strict, "phase17c_selection_bucket"] = "tier1_strict_clean_core"
    return out


def selection_sort(frame: pd.DataFrame) -> pd.DataFrame:
    priority = {
        "tier1_strict_clean_core": 0,
        "tier1_balanced_support": 1,
        "tier2_strict_transfer_sentinel": 2,
        "tier2_balanced_transfer_support": 3,
        "tier1_broad_reserve": 4,
        "tier2_broad_transfer_reserve": 5,
        "broad_reserve": 6,
        "outside_review_ready_pool": 7,
    }
    out = frame.copy()
    out["phase17c_pool_priority"] = out["phase17c_selection_bucket"].map(priority).fillna(99)
    return out.sort_values(
        ["phase17c_pool_priority", "phase17c_selection_score", "final_candidate_score", "candidate_id"],
        ascending=[True, False, False, True],
    )


def choose_rows(
    candidates: pd.DataFrame,
    selected_ids: set[str],
    group_counts: dict[str, int],
    take_count: int,
    max_per_balance_group: int,
) -> None:
    if take_count <= 0:
        return
    stop_at = len(selected_ids) + take_count
    for row in candidates.itertuples(index=False):
        candidate_id = str(getattr(row, "candidate_id"))
        if candidate_id in selected_ids:
            continue
        group = str(getattr(row, "phase17c_balance_group_hash"))
        if group_counts.get(group, 0) >= max_per_balance_group:
            continue
        selected_ids.add(candidate_id)
        group_counts[group] = group_counts.get(group, 0) + 1
        if len(selected_ids) >= stop_at:
            return


def choose_until_total(
    candidates: pd.DataFrame,
    selected_ids: set[str],
    group_counts: dict[str, int],
    target_total: int,
    max_per_balance_group: int,
) -> None:
    remaining = target_total - len(selected_ids)
    choose_rows(candidates, selected_ids, group_counts, remaining, max_per_balance_group)


def build_provisional_selection(
    frame: pd.DataFrame,
    target_count: int = DEFAULT_TARGET_COUNT,
    transfer_sentinel_count: int = DEFAULT_TRANSFER_SENTINEL_COUNT,
    max_per_balance_group: int = DEFAULT_MAX_PER_BALANCE_GROUP,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    ordered = selection_sort(frame)
    selected_ids: set[str] = set()
    group_counts: dict[str, int] = {}
    clean_target = max(0, target_count - transfer_sentinel_count)

    transfer_pool = ordered[
        ordered["phase17c_selection_bucket"].isin(
            {"tier2_strict_transfer_sentinel", "tier2_balanced_transfer_support"}
        )
    ]
    choose_rows(transfer_pool, selected_ids, group_counts, transfer_sentinel_count, max_per_balance_group)

    clean_pool = ordered[
        ordered["phase17c_selection_bucket"].isin({"tier1_strict_clean_core", "tier1_balanced_support"})
    ]
    choose_until_total(clean_pool, selected_ids, group_counts, transfer_sentinel_count + clean_target, max_per_balance_group)

    if len(selected_ids) < target_count:
        reserve_pool = ordered[
            ordered["phase17c_selection_bucket"].isin({"tier1_broad_reserve", "tier2_broad_transfer_reserve"})
        ]
        choose_until_total(reserve_pool, selected_ids, group_counts, target_count, max_per_balance_group)

    out = ordered.copy()
    out["phase17c_selected"] = out["candidate_id"].astype(str).isin(selected_ids)
    out["phase17c_selection_role"] = ""
    out.loc[
        out["phase17c_selected"] & out["source_tier"].astype(str).eq("1"),
        "phase17c_selection_role",
    ] = "clean_backbone"
    out.loc[
        out["phase17c_selected"] & out["source_tier"].astype(str).eq("2"),
        "phase17c_selection_role",
    ] = "transfer_sentinel"
    out["phase17c_selection_rank"] = ""
    selected_order = out[out["phase17c_selected"]].sort_values(
        ["phase17c_selection_role", "phase17c_pool_priority", "phase17c_selection_score", "candidate_id"],
        ascending=[True, True, False, True],
    )
    rank_map = {candidate_id: rank for rank, candidate_id in enumerate(selected_order["candidate_id"], start=1)}
    out.loc[out["phase17c_selected"], "phase17c_selection_rank"] = out.loc[
        out["phase17c_selected"], "candidate_id"
    ].map(rank_map)

    out["phase17c_rejection_reason"] = ""
    out.loc[
        ~out["phase17c_selected"] & out["phase17c_selection_bucket"].eq("outside_review_ready_pool"),
        "phase17c_rejection_reason",
    ] = "outside_review_ready_pool"
    out.loc[
        ~out["phase17c_selected"]
        & out["phase17c_selection_bucket"].isin(
            {
                "tier1_strict_clean_core",
                "tier1_balanced_support",
                "tier2_strict_transfer_sentinel",
                "tier2_balanced_transfer_support",
                "tier1_broad_reserve",
                "tier2_broad_transfer_reserve",
            }
        ),
        "phase17c_rejection_reason",
    ] = "below_quota_or_balance_group_cap"

    selected = out[out["phase17c_selected"]].copy()
    rejected = out[~out["phase17c_selected"]].copy()
    selected_tier_counts = selected["source_tier"].astype(str).value_counts().to_dict()
    audit = {
        "created_at": utc_now(),
        "input_rows": int(len(frame)),
        "target_count": int(target_count),
        "selected_rows": int(len(selected)),
        "selection_status": "PASS" if len(selected) == target_count else "REVIEW_INSUFFICIENT_ROWS",
        "transfer_sentinel_target": int(transfer_sentinel_count),
        "clean_backbone_target": int(clean_target),
        "max_per_balance_group": int(max_per_balance_group),
        "selected_unique_candidate_id": bool(selected["candidate_id"].is_unique),
        "selected_duplicate_image_uri_count": int(selected["image_uri"].duplicated().sum())
        if "image_uri" in selected
        else None,
        "selected_balance_group_count": int(selected["phase17c_balance_group_hash"].nunique()),
        "selected_max_balance_group_count": int(selected["phase17c_balance_group_hash"].value_counts().max())
        if not selected.empty
        else 0,
        "selected_source_tier_counts": selected_tier_counts,
        "selected_role_counts": selected["phase17c_selection_role"].value_counts().to_dict(),
        "selected_bucket_counts": selected["phase17c_selection_bucket"].value_counts().to_dict(),
        "input_bucket_counts": frame["phase17c_selection_bucket"].value_counts().to_dict(),
        "claim_status": "PROVISIONAL_REVIEW_READINESS_FOUNDATION_ONLY",
        "claim_boundary": (
            "Phase17C selects a provisional Bobcat review-readiness 3000 for algorithm preparation. "
            "It is not a final Bobcat high-confidence identity set and not an identity-accuracy claim."
        ),
        "selection_policy": (
            "Tier 1 strict/balanced rows form the clean backbone; Tier 2 strict/balanced rows are capped "
            "as transfer sentinels; broad rows are reserve only; low-score/defer rows are excluded from "
            "the provisional 3000 and sampled separately for audit."
        ),
    }
    return selected, rejected, audit


def public_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in PUBLIC_OUTPUT_COLUMNS if column in frame.columns]


def bucket_summary(frame: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    input_counts = frame["phase17c_selection_bucket"].value_counts()
    selected_counts = selected["phase17c_selection_bucket"].value_counts()
    rows = []
    for bucket in sorted(set(input_counts.index) | set(selected_counts.index)):
        input_count = int(input_counts.get(bucket, 0))
        selected_count = int(selected_counts.get(bucket, 0))
        rows.append(
            {
                "phase17c_selection_bucket": bucket,
                "input_count": input_count,
                "selected_count": selected_count,
                "selected_rate_within_bucket": selected_count / input_count if input_count else 0.0,
            }
        )
    return pd.DataFrame(rows)


def selected_route_summary(selected: pd.DataFrame) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    return (
        selected.groupby(["phase17c_selection_role", "phase17b_route"], dropna=False)
        .agg(
            selected_rows=("candidate_id", "count"),
            median_final_candidate_score=("final_candidate_score", "median"),
            median_iqa_quality_proxy_score=("iqa_quality_proxy_score", "median"),
            median_clip_side_view_score=("clip_side_view_score", "median"),
            median_md_geometry_score=("md_geometry_score", "median"),
        )
        .reset_index()
        .sort_values(["phase17c_selection_role", "selected_rows"], ascending=[True, False])
    )


def balance_group_summary(selected: pd.DataFrame) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    return (
        selected.groupby("phase17c_balance_group_hash", dropna=False)
        .agg(
            selected_rows=("candidate_id", "count"),
            clean_backbone_rows=("phase17c_selection_role", lambda s: int((s == "clean_backbone").sum())),
            transfer_sentinel_rows=("phase17c_selection_role", lambda s: int((s == "transfer_sentinel").sum())),
            median_selection_score=("phase17c_selection_score", "median"),
        )
        .reset_index()
        .sort_values(["selected_rows", "median_selection_score"], ascending=[False, False])
    )


def manual_audit_expansion_sheet(
    frame: pd.DataFrame,
    selected: pd.DataFrame,
    per_bucket: int = DEFAULT_MANUAL_AUDIT_PER_BUCKET,
    random_seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    selected_ids = set(selected["candidate_id"].astype(str))
    if "phase17b_route" in frame.columns:
        defer_mask = frame["phase17b_route"].isin({"non_comparable_or_defer", "manual_low_evidence_check"})
    else:
        defer_mask = frame["phase17c_selection_bucket"].eq("outside_review_ready_pool")
    pools = {
        "selected_clean_backbone": selected[selected["phase17c_selection_role"].eq("clean_backbone")],
        "selected_transfer_sentinel": selected[selected["phase17c_selection_role"].eq("transfer_sentinel")],
        "rejected_tier1_borderline": frame[
            ~frame["candidate_id"].astype(str).isin(selected_ids)
            & frame["phase17c_selection_bucket"].isin({"tier1_strict_clean_core", "tier1_balanced_support"})
        ],
        "rejected_tier2_borderline": frame[
            ~frame["candidate_id"].astype(str).isin(selected_ids)
            & frame["phase17c_selection_bucket"].isin(
                {"tier2_strict_transfer_sentinel", "tier2_balanced_transfer_support"}
            )
        ],
        "defer_or_low_score": frame[defer_mask],
    }
    pieces = []
    for reason, pool in pools.items():
        if pool.empty:
            continue
        n = min(per_bucket, len(pool))
        sample = pool.sample(n=n, random_state=random_seed + len(pieces)).copy()
        sample["phase17c_manual_audit_reason"] = reason
        pieces.append(sample)
    if not pieces:
        return frame.head(0).copy()
    sheet = pd.concat(pieces, ignore_index=True)
    sheet["auditor_visible_individual_id"] = ""
    sheet["is_bobcat_visible"] = ""
    sheet["is_individual_review_usable"] = ""
    sheet["viewpoint_manual_label"] = ""
    sheet["occlusion_manual_label"] = ""
    sheet["selection_role_agreement"] = ""
    sheet["algorithm_entry_allowed"] = ""
    sheet["audit_notes"] = ""
    sheet["claim_boundary"] = "manual audit for review-readiness only; no automatic identity claim"
    keep = public_columns(sheet) + [
        "phase17c_manual_audit_reason",
        "auditor_visible_individual_id",
        "is_bobcat_visible",
        "is_individual_review_usable",
        "viewpoint_manual_label",
        "occlusion_manual_label",
        "selection_role_agreement",
        "algorithm_entry_allowed",
        "audit_notes",
        "claim_boundary",
    ]
    return sheet[keep].sort_values(["phase17c_manual_audit_reason", "candidate_id"]).reset_index(drop=True)


def write_report(output_dir: Path, audit: dict[str, Any]) -> None:
    lines = [
        "# Phase17C Bobcat Provisional 3000",
        "",
        "This output selects a provisional Bobcat review-readiness foundation for algorithm preparation.",
        "It is not a final high-confidence identity set and not a Bobcat identity-accuracy result.",
        "",
        "## Summary",
        "",
        f"- Input rows: {audit['input_rows']:,}.",
        f"- Target rows: {audit['target_count']:,}.",
        f"- Selected rows: {audit['selected_rows']:,}.",
        f"- Status: `{audit['selection_status']}`.",
        f"- Clean backbone target: {audit['clean_backbone_target']:,}.",
        f"- Transfer sentinel target: {audit['transfer_sentinel_target']:,}.",
        f"- Max per balance group: {audit['max_per_balance_group']:,}.",
        f"- Selected balance groups: {audit['selected_balance_group_count']:,}.",
        f"- Largest selected balance group: {audit['selected_max_balance_group_count']:,}.",
        "",
        "## Selected Roles",
        "",
        "| role | selected rows |",
        "| --- | ---: |",
    ]
    for role, count in audit["selected_role_counts"].items():
        lines.append(f"| `{role}` | {count:,} |")
    lines.extend(["", "## Selected Buckets", "", "| bucket | selected rows |", "| --- | ---: |"])
    for bucket, count in audit["selected_bucket_counts"].items():
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
            f"- `{GROUP_SUMMARY_CSV}`",
            f"- `{ROUTE_SUMMARY_CSV}`",
            f"- `{MANUAL_AUDIT_CSV}`",
            f"- `{AUDIT_JSON}`",
        ]
    )
    (output_dir / REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_phase17c_bobcat_provisional_3000(
    input_csv: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    target_count: int = DEFAULT_TARGET_COUNT,
    transfer_sentinel_count: int = DEFAULT_TRANSFER_SENTINEL_COUNT,
    max_per_balance_group: int = DEFAULT_MAX_PER_BALANCE_GROUP,
    manual_audit_per_bucket: int = DEFAULT_MANUAL_AUDIT_PER_BUCKET,
) -> dict[str, Any]:
    raw = pd.read_csv(input_csv, low_memory=False)
    validate_input(raw)
    frame = assign_selection_buckets(compute_selection_scores(prepare_bobcat_frame(raw)))
    selected, rejected, audit = build_provisional_selection(
        frame,
        target_count=target_count,
        transfer_sentinel_count=transfer_sentinel_count,
        max_per_balance_group=max_per_balance_group,
    )
    audit["input_path"] = str(input_csv)
    audit["output_dir"] = str(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    selected[public_columns(selected)].to_csv(output_dir / SELECTED_CSV, index=False)
    rejected[public_columns(rejected)].to_csv(output_dir / REJECTED_CSV, index=False)
    bucket_summary(frame, selected).to_csv(output_dir / BUCKET_SUMMARY_CSV, index=False)
    balance_group_summary(selected).to_csv(output_dir / GROUP_SUMMARY_CSV, index=False)
    selected_route_summary(selected).to_csv(output_dir / ROUTE_SUMMARY_CSV, index=False)
    manual_audit = manual_audit_expansion_sheet(
        frame,
        selected,
        per_bucket=manual_audit_per_bucket,
        random_seed=RANDOM_SEED,
    )
    manual_audit.to_csv(output_dir / MANUAL_AUDIT_CSV, index=False)
    audit["manual_audit_rows"] = int(len(manual_audit))
    (output_dir / AUDIT_JSON).write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    write_report(output_dir, audit)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target-count", type=int, default=DEFAULT_TARGET_COUNT)
    parser.add_argument("--transfer-sentinel-count", type=int, default=DEFAULT_TRANSFER_SENTINEL_COUNT)
    parser.add_argument("--max-per-balance-group", type=int, default=DEFAULT_MAX_PER_BALANCE_GROUP)
    parser.add_argument("--manual-audit-per-bucket", type=int, default=DEFAULT_MANUAL_AUDIT_PER_BUCKET)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = run_phase17c_bobcat_provisional_3000(
        input_csv=args.input,
        output_dir=args.output_dir,
        target_count=args.target_count,
        transfer_sentinel_count=args.transfer_sentinel_count,
        max_per_balance_group=args.max_per_balance_group,
        manual_audit_per_bucket=args.manual_audit_per_bucket,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
