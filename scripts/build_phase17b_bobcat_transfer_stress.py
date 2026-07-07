#!/usr/bin/env python3
"""Build Phase17B Bobcat transfer-stress and manual-audit queues."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_bobcat_score_analysis/phase16e_bobcat_recalibrated_scores.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase17/phase17b_bobcat_transfer_stress"

REQUIRED_COLUMNS = [
    "candidate_id",
    "source_tier",
    "source_role",
    "image_uri",
    "image_load_success",
    "scoring_valid_for_selection",
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
]

METRIC_COLUMNS = [
    "final_candidate_score",
    "iqa_quality_proxy_score",
    "clip_side_view_score",
    "clip_viewpoint_confidence",
    "clip_viewpoint_prob_partial_or_occluded",
    "clip_viewpoint_prob_unclear",
    "md_geometry_score",
]

SAMPLE_STRATA = [
    "strict",
    "balanced_not_strict",
    "broad_not_balanced",
    "low_score",
]


def _bool_series(frame: pd.DataFrame, column: str, default: bool = False) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=bool)
    values = frame[column]
    if values.dtype == bool:
        return values.fillna(default)
    return values.astype(str).str.lower().isin({"true", "1", "yes"})


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return float("nan")
    return float(numerator / denominator)


def _format_float(value: object, digits: int = 4) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "nan"
    if math.isnan(numeric):
        return "nan"
    return f"{numeric:.{digits}f}"


def load_bobcat_scores(input_csv: Path) -> pd.DataFrame:
    table = pd.read_csv(input_csv, low_memory=False)
    missing = [column for column in REQUIRED_COLUMNS if column not in table.columns]
    if missing:
        raise ValueError("Phase17B Bobcat input missing required columns: " + ", ".join(missing))
    return table


def prepare_bobcat_frame(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    for column in [
        "image_load_success",
        "scoring_valid_for_selection",
        "strict_recalibrated_eligible",
        "balanced_recalibrated_eligible",
        "broad_recalibrated_eligible",
        "model_fallback_mode",
        "pose_fallback_scoring_used",
    ]:
        frame[column] = _bool_series(frame, column)
    for column in METRIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    valid = (
        frame["image_load_success"]
        & frame["scoring_valid_for_selection"]
        & frame["final_candidate_score"].notna()
        & frame["iqa_quality_proxy_score"].notna()
    )
    frame = frame[valid].copy()
    if frame.empty:
        raise ValueError("Phase17B Bobcat frame is empty after validity filtering")
    frame["source_tier"] = frame["source_tier"].astype(str).str.replace(r"\.0$", "", regex=True)
    frame["phase17b_stratum"] = "low_score"
    frame.loc[frame["broad_recalibrated_eligible"], "phase17b_stratum"] = "broad_not_balanced"
    frame.loc[frame["balanced_recalibrated_eligible"], "phase17b_stratum"] = "balanced_not_strict"
    frame.loc[frame["strict_recalibrated_eligible"], "phase17b_stratum"] = "strict"
    frame["phase17b_route"] = assign_route(frame)
    return frame.reset_index(drop=True)


def assign_route(frame: pd.DataFrame) -> pd.Series:
    route = pd.Series("manual_low_evidence_check", index=frame.index, dtype=object)
    route.loc[frame["broad_recalibrated_eligible"]] = "coverage_reserve_review"
    route.loc[frame["balanced_recalibrated_eligible"]] = "primary_manual_review"
    route.loc[frame["strict_recalibrated_eligible"]] = "high_confidence_review"
    topup = frame["source_tier"].astype(str).eq("2")
    route.loc[topup & frame["balanced_recalibrated_eligible"]] = "topup_stress_review"
    weak_view = (
        frame["clip_viewpoint_prob_partial_or_occluded"].fillna(0) >= 0.90
    ) | frame["clip_viewpoint_label"].astype(str).eq("unclear")
    route.loc[weak_view & ~frame["balanced_recalibrated_eligible"]] = "non_comparable_or_defer"
    return route


def summarize_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    groupers = {
        "all": pd.Series("all", index=frame.index),
        "source_tier": frame["source_tier"],
        "source_role": frame["source_role"].astype(str),
        "phase17b_stratum": frame["phase17b_stratum"],
        "phase17b_route": frame["phase17b_route"],
    }
    for grouping, labels in groupers.items():
        for value, group in frame.groupby(labels, dropna=False):
            row: dict[str, object] = {
                "grouping": grouping,
                "value": str(value),
                "rows": int(len(group)),
                "row_share": _safe_divide(len(group), len(frame)),
                "strict_eligible_rate": float(group["strict_recalibrated_eligible"].mean()),
                "balanced_eligible_rate": float(group["balanced_recalibrated_eligible"].mean()),
                "broad_eligible_rate": float(group["broad_recalibrated_eligible"].mean()),
            }
            for metric in METRIC_COLUMNS:
                values = group[metric].dropna()
                row[f"{metric}_n"] = int(len(values))
                row[f"{metric}_mean"] = float(values.mean()) if len(values) else float("nan")
                row[f"{metric}_sd"] = float(values.std(ddof=1)) if len(values) > 1 else float("nan")
                for q in [0.10, 0.25, 0.50, 0.75, 0.90]:
                    row[f"{metric}_p{int(q * 100):02d}"] = float(values.quantile(q)) if len(values) else float("nan")
            rows.append(row)
    return pd.DataFrame(rows)


def _rankdata_average(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    sorted_values = values[order]
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        ranks[order[start:end]] = average_rank
        start = end
    return ranks


def mann_whitney_effect(x: pd.Series, y: pd.Series) -> dict[str, float]:
    x_values = pd.to_numeric(x, errors="coerce").dropna().to_numpy(dtype=float)
    y_values = pd.to_numeric(y, errors="coerce").dropna().to_numpy(dtype=float)
    if len(x_values) == 0 or len(y_values) == 0:
        return {
            "u_statistic": float("nan"),
            "rank_biserial": float("nan"),
            "normal_approx_z": float("nan"),
            "normal_approx_p": float("nan"),
        }
    combined = np.concatenate([x_values, y_values])
    ranks = _rankdata_average(combined)
    rank_sum_x = float(ranks[: len(x_values)].sum())
    n_x = len(x_values)
    n_y = len(y_values)
    u_x = rank_sum_x - (n_x * (n_x + 1) / 2.0)
    mean_u = n_x * n_y / 2.0
    sd_u = math.sqrt(n_x * n_y * (n_x + n_y + 1) / 12.0)
    z = (u_x - mean_u) / sd_u if sd_u else float("nan")
    p = math.erfc(abs(z) / math.sqrt(2.0)) if not math.isnan(z) else float("nan")
    return {
        "u_statistic": float(u_x),
        "rank_biserial": float((2.0 * u_x / (n_x * n_y)) - 1.0),
        "normal_approx_z": float(z),
        "normal_approx_p": float(p),
    }


def bootstrap_median_difference(
    x: pd.Series,
    y: pd.Series,
    iterations: int = 1000,
    seed: int = 1702,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    x_values = pd.to_numeric(x, errors="coerce").dropna().to_numpy(dtype=float)
    y_values = pd.to_numeric(y, errors="coerce").dropna().to_numpy(dtype=float)
    if len(x_values) == 0 or len(y_values) == 0:
        return {"median_difference": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
    observed = float(np.median(x_values) - np.median(y_values))
    boot = np.empty(iterations, dtype=float)
    for i in range(iterations):
        x_sample = rng.choice(x_values, size=len(x_values), replace=True)
        y_sample = rng.choice(y_values, size=len(y_values), replace=True)
        boot[i] = float(np.median(x_sample) - np.median(y_sample))
    return {
        "median_difference": observed,
        "ci_low": float(np.quantile(boot, 0.025)),
        "ci_high": float(np.quantile(boot, 0.975)),
    }


def source_tier_tests(frame: pd.DataFrame) -> pd.DataFrame:
    tiers = sorted(frame["source_tier"].astype(str).dropna().unique())
    if len(tiers) != 2:
        return pd.DataFrame()
    tier_a, tier_b = tiers
    group_a = frame[frame["source_tier"].astype(str).eq(tier_a)]
    group_b = frame[frame["source_tier"].astype(str).eq(tier_b)]
    rows: list[dict[str, object]] = []
    for metric in METRIC_COLUMNS:
        mw = mann_whitney_effect(group_a[metric], group_b[metric])
        boot = bootstrap_median_difference(group_a[metric], group_b[metric])
        rows.append(
            {
                "comparison": f"source_tier_{tier_a}_minus_{tier_b}",
                "metric": metric,
                "tier_a": tier_a,
                "tier_b": tier_b,
                "tier_a_n": int(group_a[metric].notna().sum()),
                "tier_b_n": int(group_b[metric].notna().sum()),
                "tier_a_median": float(group_a[metric].median()),
                "tier_b_median": float(group_b[metric].median()),
                **boot,
                **mw,
                "interpretation_boundary": "exploratory distribution test; not identity accuracy",
            }
        )
    return pd.DataFrame(rows)


def route_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total = len(frame)
    for route, group in frame.groupby("phase17b_route", dropna=False):
        rows.append(
            {
                "phase17b_route": route,
                "rows": int(len(group)),
                "row_share": _safe_divide(len(group), total),
                "source_tier_1_rows": int(group["source_tier"].astype(str).eq("1").sum()),
                "source_tier_2_rows": int(group["source_tier"].astype(str).eq("2").sum()),
                "median_final_candidate_score": float(group["final_candidate_score"].median()),
                "median_iqa_quality_proxy_score": float(group["iqa_quality_proxy_score"].median()),
                "median_clip_side_view_score": float(group["clip_side_view_score"].median()),
                "partial_or_occluded_rate": float(
                    group["clip_viewpoint_label"].astype(str).eq("partial_or_occluded").mean()
                ),
                "unclear_rate": float(group["clip_viewpoint_label"].astype(str).eq("unclear").mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("phase17b_route").reset_index(drop=True)


def assumption_diagnostics(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for metric in METRIC_COLUMNS:
        values = frame[metric].dropna()
        rows.append(
            {
                "metric": metric,
                "n": int(len(values)),
                "missing_rows": int(frame[metric].isna().sum()),
                "unique_values": int(values.nunique()),
                "mean": float(values.mean()) if len(values) else float("nan"),
                "median": float(values.median()) if len(values) else float("nan"),
                "sd": float(values.std(ddof=1)) if len(values) > 1 else float("nan"),
                "iqr": float(values.quantile(0.75) - values.quantile(0.25)) if len(values) else float("nan"),
                "skew_proxy_mean_minus_median": (
                    float(values.mean() - values.median()) if len(values) else float("nan")
                ),
                "zero_rate": float((values == 0).mean()) if len(values) else float("nan"),
                "analysis_decision": "nonparametric_effect_size_and_bootstrap_ci",
            }
        )
    return pd.DataFrame(rows)


def build_manual_audit_queue(
    frame: pd.DataFrame,
    per_source_stratum: int = 25,
    seed: int = 1702,
) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    columns = [
        "candidate_id",
        "source_tier",
        "source_role",
        "phase17b_stratum",
        "phase17b_route",
        "image_uri",
        "final_candidate_score",
        "iqa_quality_proxy_score",
        "clip_side_view_score",
        "clip_viewpoint_label",
        "clip_viewpoint_confidence",
        "clip_viewpoint_prob_partial_or_occluded",
        "clip_viewpoint_prob_unclear",
        "md_geometry_score",
        "strict_recalibrated_eligible",
        "balanced_recalibrated_eligible",
        "broad_recalibrated_eligible",
    ]
    for tier in sorted(frame["source_tier"].astype(str).unique()):
        tier_frame = frame[frame["source_tier"].astype(str).eq(tier)]
        for stratum in SAMPLE_STRATA:
            subset = tier_frame[tier_frame["phase17b_stratum"].eq(stratum)].copy()
            if subset.empty:
                continue
            take = min(per_source_stratum, len(subset))
            sampled = subset.sample(n=take, random_state=seed + len(pieces)).copy()
            sampled["manual_audit_batch"] = f"tier_{tier}_{stratum}"
            pieces.append(sampled)
    if not pieces:
        return pd.DataFrame(columns=["manual_audit_batch", *columns])
    queue = pd.concat(pieces, ignore_index=True)
    queue["manual_audit_priority"] = queue["phase17b_stratum"].map(
        {"strict": 1, "balanced_not_strict": 2, "broad_not_balanced": 3, "low_score": 4}
    )
    keep = ["manual_audit_batch", "manual_audit_priority", *columns]
    return queue[keep].sort_values(["manual_audit_priority", "source_tier", "candidate_id"]).reset_index(drop=True)


def build_manual_audit_sheet(queue: pd.DataFrame) -> pd.DataFrame:
    sheet = queue.copy()
    sheet["auditor_visible_individual_id"] = ""
    sheet["is_bobcat_visible"] = ""
    sheet["is_individual_review_usable"] = ""
    sheet["viewpoint_manual_label"] = ""
    sheet["occlusion_manual_label"] = ""
    sheet["route_agreement"] = ""
    sheet["audit_notes"] = ""
    sheet["claim_boundary"] = "manual review usability only; no automatic identity claim"
    return sheet


def build_audit(raw: pd.DataFrame, frame: pd.DataFrame, queue: pd.DataFrame) -> dict[str, object]:
    return {
        "status": "PASS" if len(frame) == len(raw) and len(queue) > 0 else "WARN",
        "claim_status": "TRANSFER_STRESS_REVIEW_READINESS_ONLY",
        "claim_boundary": (
            "Bobcat Phase17B evaluates score distributions, source-tier transfer stress, "
            "and manual-audit routing. It does not evaluate Bobcat identity accuracy."
        ),
        "input_rows": int(len(raw)),
        "analysis_rows": int(len(frame)),
        "manual_audit_queue_rows": int(len(queue)),
        "source_tier_counts": frame["source_tier"].value_counts().sort_index().astype(int).to_dict(),
        "stratum_counts": frame["phase17b_stratum"].value_counts().astype(int).to_dict(),
        "route_counts": frame["phase17b_route"].value_counts().astype(int).to_dict(),
        "candidate_id_unique": bool(frame["candidate_id"].is_unique),
        "duplicate_candidate_id_count": int(frame["candidate_id"].duplicated().sum()),
        "next_claim_rule": (
            "Use these outputs for tier-separated manual audit and review-routing design. "
            "Require verified individual IDs or audited same/different pairs before stronger claims."
        ),
    }


def write_report(
    audit: dict[str, object],
    metric_summary: pd.DataFrame,
    tests: pd.DataFrame,
    routes: pd.DataFrame,
    diagnostics: pd.DataFrame,
    output_dir: Path,
) -> None:
    tier_summary = metric_summary[metric_summary["grouping"].eq("source_tier")].sort_values("value")
    stratum_summary = metric_summary[metric_summary["grouping"].eq("phase17b_stratum")].sort_values("value")
    lines = [
        "# Phase17B Bobcat Transfer-Stress Review Routing",
        "",
        "This report evaluates Bobcat Phase16E scores as transfer-stress and manual-audit routing evidence.",
        "It does not evaluate Bobcat individual-ID accuracy.",
        "",
        "## Audit",
        "",
        f"- Status: {audit['status']}",
        f"- Claim status: {audit['claim_status']}",
        f"- Input rows: {audit['input_rows']:,}",
        f"- Analysis rows: {audit['analysis_rows']:,}",
        f"- Manual-audit queue rows: {audit['manual_audit_queue_rows']:,}",
        f"- Candidate IDs unique: {audit['candidate_id_unique']}",
        "",
        "## Source-Tier Summary",
        "",
        "| source tier | rows | strict rate | balanced rate | broad rate | final p50 | IQA p50 | side p50 | MD geometry p50 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in tier_summary.to_dict(orient="records"):
        lines.append(
            f"| {row['value']} | {int(row['rows']):,} | "
            f"{row['strict_eligible_rate']:.4f} | {row['balanced_eligible_rate']:.4f} | "
            f"{row['broad_eligible_rate']:.4f} | {_format_float(row['final_candidate_score_p50'])} | "
            f"{_format_float(row['iqa_quality_proxy_score_p50'])} | "
            f"{_format_float(row['clip_side_view_score_p50'])} | {_format_float(row['md_geometry_score_p50'])} |"
        )
    lines.extend(
        [
            "",
            "## Route Summary",
            "",
            "| route | rows | share | tier 1 rows | tier 2 rows | final p50 | partial/occluded rate | unclear rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in routes.to_dict(orient="records"):
        lines.append(
            f"| {row['phase17b_route']} | {int(row['rows']):,} | {row['row_share']:.4f} | "
            f"{int(row['source_tier_1_rows']):,} | {int(row['source_tier_2_rows']):,} | "
            f"{row['median_final_candidate_score']:.4f} | {row['partial_or_occluded_rate']:.4f} | "
            f"{row['unclear_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Source-Tier Statistical Tests",
            "",
            "Tests are exploratory and non-parametric. They quantify source-tier distribution pressure, not identity accuracy.",
            "",
            "| metric | tier 1 median | tier 2 median | median diff 95% CI | rank-biserial | p approx |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in tests.to_dict(orient="records"):
        lines.append(
            f"| {row['metric']} | {row['tier_a_median']:.4f} | {row['tier_b_median']:.4f} | "
            f"{row['median_difference']:.4f} [{row['ci_low']:.4f}, {row['ci_high']:.4f}] | "
            f"{row['rank_biserial']:.4f} | {row['normal_approx_p']:.3g} |"
        )
    lines.extend(
        [
            "",
            "## Stratum Summary",
            "",
            "| stratum | rows | share | final p50 | IQA p50 | side p50 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in stratum_summary.to_dict(orient="records"):
        lines.append(
            f"| {row['value']} | {int(row['rows']):,} | {row['row_share']:.4f} | "
            f"{_format_float(row['final_candidate_score_p50'])} | "
            f"{_format_float(row['iqa_quality_proxy_score_p50'])} | "
            f"{_format_float(row['clip_side_view_score_p50'])} |"
        )
    lines.extend(
        [
            "",
            "## Assumption Decision",
            "",
            "The score distributions are bounded, skewed, and include structural zeros in MD geometry for top-up rows.",
            "Therefore Phase17B reports medians, quantiles, rank-biserial effects, and bootstrap confidence intervals.",
            "The p approximations are secondary diagnostics and must not be presented as confirmatory identity evidence.",
            "",
            "## Files",
            "",
            "- `phase17b_bobcat_metric_summary.csv`",
            "- `phase17b_bobcat_source_tier_tests.csv`",
            "- `phase17b_bobcat_route_summary.csv`",
            "- `phase17b_bobcat_assumption_diagnostics.csv`",
            "- `phase17b_bobcat_manual_audit_queue.csv`",
            "- `phase17b_bobcat_manual_audit_sheet.csv`",
            "- `phase17b_bobcat_transfer_stress_audit.json`",
            "",
            "## Boundary",
            "",
            str(audit["claim_boundary"]),
            "",
        ]
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase17b_bobcat_transfer_stress_report.md").write_text("\n".join(lines), encoding="utf-8")


def run_phase17b_bobcat_transfer_stress(
    input_csv: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    per_source_stratum: int = 25,
) -> dict[str, object]:
    raw = load_bobcat_scores(input_csv)
    frame = prepare_bobcat_frame(raw)
    metric_summary = summarize_metrics(frame)
    tests = source_tier_tests(frame)
    routes = route_summary(frame)
    diagnostics = assumption_diagnostics(frame)
    queue = build_manual_audit_queue(frame, per_source_stratum=per_source_stratum)
    sheet = build_manual_audit_sheet(queue)
    audit = build_audit(raw, frame, queue)

    output_dir.mkdir(parents=True, exist_ok=True)
    metric_summary.to_csv(output_dir / "phase17b_bobcat_metric_summary.csv", index=False)
    tests.to_csv(output_dir / "phase17b_bobcat_source_tier_tests.csv", index=False)
    routes.to_csv(output_dir / "phase17b_bobcat_route_summary.csv", index=False)
    diagnostics.to_csv(output_dir / "phase17b_bobcat_assumption_diagnostics.csv", index=False)
    queue.to_csv(output_dir / "phase17b_bobcat_manual_audit_queue.csv", index=False)
    sheet.to_csv(output_dir / "phase17b_bobcat_manual_audit_sheet.csv", index=False)
    (output_dir / "phase17b_bobcat_transfer_stress_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(audit, metric_summary, tests, routes, diagnostics, output_dir)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--per-source-stratum", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = run_phase17b_bobcat_transfer_stress(
        input_csv=args.input,
        output_dir=args.output_dir,
        per_source_stratum=args.per_source_stratum,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
