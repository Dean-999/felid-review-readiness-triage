#!/usr/bin/env python3
"""Build Phase17A CzechLynx review-utility validation outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "outputs/phase16/phase16h_czechlynx_readiness_controls/phase16h_czechlynx_scored_pair_table.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase17/phase17a_czechlynx_review_utility"

REQUIRED_COLUMNS = [
    "pair_id",
    "query_image_id",
    "candidate_image_id",
    "phase16h_label",
    "label_allowed_for_modeling",
    "source_leakage_pressure_flag",
    "descriptor_evidence_conflict_flag",
    "score_descriptor_only",
    "score_quality_only",
    "score_evidence_only",
    "score_conflict_penalized_descriptor",
    "score_phase16h_diagnostic",
]

POLICY_SCORE_COLUMNS = {
    "descriptor_only": "score_descriptor_only",
    "quality_only": "score_quality_only",
    "evidence_only": "score_evidence_only",
    "conflict_penalized_descriptor": "score_conflict_penalized_descriptor",
    "phase17a_diagnostic_review_utility": "score_phase16h_diagnostic",
}

K_VALUES = [1, 3, 5, 10, 20]
POSITIVE_RETENTION_TARGETS = [0.50, 0.70, 0.80, 0.90, 0.95]
PAIR_COVERAGE_LEVELS = [0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00]


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


def load_review_table(input_csv: Path) -> pd.DataFrame:
    table = pd.read_csv(input_csv, low_memory=False)
    missing = [column for column in REQUIRED_COLUMNS if column not in table.columns]
    if missing:
        raise ValueError("Phase17A input missing required columns: " + ", ".join(missing))
    return table


def prepare_review_frame(pair_table: pd.DataFrame, exclude_leakage: bool = True) -> pd.DataFrame:
    frame = pair_table.copy()
    frame["phase17a_label"] = _bool_series(frame, "phase16h_label")
    frame["source_leakage_pressure_flag"] = _bool_series(frame, "source_leakage_pressure_flag")
    frame["descriptor_evidence_conflict_flag"] = _bool_series(frame, "descriptor_evidence_conflict_flag")
    frame["label_allowed_for_modeling"] = _bool_series(frame, "label_allowed_for_modeling", default=True)
    frame = frame[frame["label_allowed_for_modeling"]].copy()
    if exclude_leakage:
        frame = frame[~frame["source_leakage_pressure_flag"]].copy()
    for column in POLICY_SCORE_COLUMNS.values():
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    if frame.empty:
        raise ValueError("Phase17A review frame is empty after filtering")
    if frame["phase17a_label"].nunique() < 2:
        raise ValueError("Phase17A review frame requires both positive and false pairs")
    return frame.reset_index(drop=True)


def _summarize_retained(retained: pd.DataFrame, all_queries: pd.Index) -> dict[str, object]:
    labels = retained["phase17a_label"].astype(bool) if len(retained) else pd.Series(dtype=bool)
    per_query = retained.groupby("query_image_id")["phase17a_label"].agg(
        retained_pairs="size",
        retained_positive=lambda s: int(s.astype(bool).sum()),
        retained_false=lambda s: int((~s.astype(bool)).sum()),
    )
    per_query = pd.DataFrame(index=all_queries).join(per_query).fillna(0)
    positive = int(labels.sum()) if len(labels) else 0
    false = int((~labels).sum()) if len(labels) else 0
    return {
        "retained_pairs": int(len(retained)),
        "retained_positive_pairs": positive,
        "retained_false_pairs": false,
        "positive_retention": np.nan,
        "false_retention": np.nan,
        "false_rate_among_retained": _safe_divide(false, len(retained)),
        "queries_with_retained_pair_rate": float((per_query["retained_pairs"] > 0).mean()),
        "hit_rate": float((per_query["retained_positive"] > 0).mean()),
        "mean_review_pairs_per_query": float(per_query["retained_pairs"].mean()),
        "mean_false_retained_per_query": float(per_query["retained_false"].mean()),
        "mean_positive_retained_per_query": float(per_query["retained_positive"].mean()),
        "false_per_positive_retained": _safe_divide(false, positive),
    }


def evaluate_fixed_review_budget(frame: pd.DataFrame, k_values: list[int] | None = None) -> pd.DataFrame:
    k_values = k_values or K_VALUES
    rows: list[dict[str, object]] = []
    all_queries = pd.Index(frame["query_image_id"].drop_duplicates())
    total_positive = int(frame["phase17a_label"].sum())
    total_false = int((~frame["phase17a_label"].astype(bool)).sum())
    for policy_id, score_column in POLICY_SCORE_COLUMNS.items():
        ranked = frame.copy()
        ranked["_policy_rank"] = ranked.groupby("query_image_id")[score_column].rank(method="first", ascending=False)
        for k in k_values:
            retained = ranked[ranked["_policy_rank"] <= k].copy()
            row = _summarize_retained(retained, all_queries)
            row.update(
                {
                    "policy_id": policy_id,
                    "review_budget_type": "top_k_per_query",
                    "review_budget_value": int(k),
                    "positive_retention": _safe_divide(row["retained_positive_pairs"], total_positive),
                    "false_retention": _safe_divide(row["retained_false_pairs"], total_false),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def evaluate_fixed_positive_retention(
    frame: pd.DataFrame,
    targets: list[float] | None = None,
) -> pd.DataFrame:
    targets = targets or POSITIVE_RETENTION_TARGETS
    rows: list[dict[str, object]] = []
    all_queries = pd.Index(frame["query_image_id"].drop_duplicates())
    total_positive = int(frame["phase17a_label"].sum())
    total_false = int((~frame["phase17a_label"].astype(bool)).sum())
    for policy_id, score_column in POLICY_SCORE_COLUMNS.items():
        ordered = frame.sort_values(score_column, ascending=False, kind="mergesort").copy()
        ordered["_cumulative_positive"] = ordered["phase17a_label"].astype(int).cumsum()
        for target in targets:
            needed_positive = int(np.ceil(total_positive * target))
            if needed_positive <= 0:
                retained = ordered.iloc[0:0].copy()
            else:
                cutoff = ordered[ordered["_cumulative_positive"] >= needed_positive]
                if len(cutoff):
                    cutoff_position = int(np.flatnonzero(ordered["_cumulative_positive"].to_numpy() >= needed_positive)[0])
                    retained = ordered.iloc[: cutoff_position + 1].copy()
                else:
                    retained = ordered.copy()
            row = _summarize_retained(retained, all_queries)
            row.update(
                {
                    "policy_id": policy_id,
                    "target_positive_retention": float(target),
                    "actual_pair_coverage": _safe_divide(len(retained), len(frame)),
                    "positive_retention": _safe_divide(row["retained_positive_pairs"], total_positive),
                    "false_retention": _safe_divide(row["retained_false_pairs"], total_false),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def evaluate_abstention_coverage(
    frame: pd.DataFrame,
    coverage_levels: list[float] | None = None,
) -> pd.DataFrame:
    coverage_levels = coverage_levels or PAIR_COVERAGE_LEVELS
    rows: list[dict[str, object]] = []
    all_queries = pd.Index(frame["query_image_id"].drop_duplicates())
    total_positive = int(frame["phase17a_label"].sum())
    total_false = int((~frame["phase17a_label"].astype(bool)).sum())
    for policy_id, score_column in POLICY_SCORE_COLUMNS.items():
        ordered = frame.sort_values(score_column, ascending=False, kind="mergesort").copy()
        for coverage in coverage_levels:
            take = min(len(ordered), max(1, int(np.ceil(len(ordered) * coverage))))
            retained = ordered.iloc[:take].copy()
            deferred = ordered.iloc[take:].copy()
            row = _summarize_retained(retained, all_queries)
            deferred_labels = deferred["phase17a_label"].astype(bool) if len(deferred) else pd.Series(dtype=bool)
            row.update(
                {
                    "policy_id": policy_id,
                    "target_pair_coverage": float(coverage),
                    "actual_pair_coverage": _safe_divide(len(retained), len(frame)),
                    "positive_retention": _safe_divide(row["retained_positive_pairs"], total_positive),
                    "false_retention": _safe_divide(row["retained_false_pairs"], total_false),
                    "deferred_pairs": int(len(deferred)),
                    "deferred_positive_pairs": int(deferred_labels.sum()) if len(deferred_labels) else 0,
                    "deferred_false_pairs": int((~deferred_labels).sum()) if len(deferred_labels) else 0,
                    "deferred_false_rate": float((~deferred_labels).mean()) if len(deferred_labels) else np.nan,
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def evaluate_conflict_enrichment(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    labels = frame["phase17a_label"].astype(bool)
    conflict = frame["descriptor_evidence_conflict_flag"].astype(bool)
    subsets = {
        "all_pairs": pd.Series(True, index=frame.index),
        "descriptor_top_decile": frame["score_descriptor_only"] >= frame["score_descriptor_only"].quantile(0.90),
        "diagnostic_top_decile": frame["score_phase16h_diagnostic"] >= frame["score_phase16h_diagnostic"].quantile(0.90),
    }
    for subset_name, mask in subsets.items():
        subset = frame[mask].copy()
        if subset.empty:
            continue
        subset_labels = subset["phase17a_label"].astype(bool)
        subset_conflict = subset["descriptor_evidence_conflict_flag"].astype(bool)
        conflict_rows = subset[subset_conflict]
        non_conflict_rows = subset[~subset_conflict]
        conflict_false_rate = float((~conflict_rows["phase17a_label"].astype(bool)).mean()) if len(conflict_rows) else np.nan
        non_conflict_false_rate = (
            float((~non_conflict_rows["phase17a_label"].astype(bool)).mean()) if len(non_conflict_rows) else np.nan
        )
        rows.append(
            {
                "subset_name": subset_name,
                "pair_rows": int(len(subset)),
                "positive_pairs": int(subset_labels.sum()),
                "false_pairs": int((~subset_labels).sum()),
                "conflict_pairs": int(subset_conflict.sum()),
                "conflict_rate": float(subset_conflict.mean()),
                "conflict_false_rate": conflict_false_rate,
                "non_conflict_false_rate": non_conflict_false_rate,
                "false_rate_lift_conflict_vs_non_conflict": (
                    conflict_false_rate - non_conflict_false_rate
                    if pd.notna(conflict_false_rate) and pd.notna(non_conflict_false_rate)
                    else np.nan
                ),
                "global_conflict_rate": float(conflict.mean()),
                "global_false_rate": float((~labels).mean()),
            }
        )
    return pd.DataFrame(rows)


def assign_proxy_review_actions(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    evidence = out["score_evidence_only"]
    descriptor = out["score_descriptor_only"]
    diagnostic = out["score_phase16h_diagnostic"]
    evidence_low = evidence.quantile(0.20)
    evidence_high = evidence.quantile(0.70)
    descriptor_high = descriptor.quantile(0.80)
    diagnostic_low = diagnostic.quantile(0.30)
    conflict = out["descriptor_evidence_conflict_flag"].astype(bool)
    out["phase17a_proxy_review_action"] = "review"
    out.loc[evidence <= evidence_low, "phase17a_proxy_review_action"] = "non_comparable"
    out.loc[(evidence > evidence_low) & (diagnostic <= diagnostic_low), "phase17a_proxy_review_action"] = "defer"
    out.loc[(evidence > evidence_low) & conflict, "phase17a_proxy_review_action"] = "defer"
    out.loc[(evidence >= evidence_high) & (descriptor >= descriptor_high) & ~conflict, "phase17a_proxy_review_action"] = (
        "accept_for_expert_review"
    )
    out.loc[(evidence <= evidence_low) & (descriptor >= descriptor_high), "phase17a_proxy_review_action"] = "species_level_only"
    return out


def summarize_proxy_actions(action_frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_pairs = len(action_frame)
    total_positive = int(action_frame["phase17a_label"].sum())
    for action, group in action_frame.groupby("phase17a_proxy_review_action", dropna=False):
        labels = group["phase17a_label"].astype(bool)
        positives = int(labels.sum())
        false_pairs = int((~labels).sum())
        rows.append(
            {
                "proxy_review_action": action,
                "pair_rows": int(len(group)),
                "pair_share": _safe_divide(len(group), total_pairs),
                "positive_pairs": positives,
                "false_pairs": false_pairs,
                "positive_share_captured": _safe_divide(positives, total_positive),
                "false_rate": _safe_divide(false_pairs, len(group)),
                "mean_descriptor_score": float(group["score_descriptor_only"].mean()),
                "mean_evidence_score": float(group["score_evidence_only"].mean()),
                "mean_diagnostic_score": float(group["score_phase16h_diagnostic"].mean()),
                "conflict_rate": float(group["descriptor_evidence_conflict_flag"].astype(bool).mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("proxy_review_action").reset_index(drop=True)


def build_audit(
    raw: pd.DataFrame,
    frame: pd.DataFrame,
    budget_metrics: pd.DataFrame,
    conflict_enrichment: pd.DataFrame,
) -> dict[str, object]:
    required_policies = set(POLICY_SCORE_COLUMNS)
    present_policies = set(budget_metrics["policy_id"].astype(str))
    k10 = budget_metrics[budget_metrics["review_budget_value"].eq(10)]
    descriptor = k10[k10["policy_id"].eq("descriptor_only")]
    diagnostic = k10[k10["policy_id"].eq("phase17a_diagnostic_review_utility")]
    if not descriptor.empty and not diagnostic.empty:
        descriptor_row = descriptor.iloc[0]
        diagnostic_row = diagnostic.iloc[0]
        false_delta_at_k10 = float(descriptor_row["mean_false_retained_per_query"]) - float(
            diagnostic_row["mean_false_retained_per_query"]
        )
        hit_delta_at_k10 = float(diagnostic_row["hit_rate"]) - float(descriptor_row["hit_rate"])
    else:
        false_delta_at_k10 = float("nan")
        hit_delta_at_k10 = float("nan")
    audit = {
        "status": "PASS" if required_policies.issubset(present_policies) and not conflict_enrichment.empty else "FAIL",
        "claim_status": "REVIEW_UTILITY_VALIDATION_ONLY",
        "claim_boundary": (
            "CzechLynx review-utility validation only; no descriptor replacement, "
            "automatic identity assignment, or Bobcat identity-accuracy claim."
        ),
        "input_rows": int(len(raw)),
        "review_scope_rows": int(len(frame)),
        "excluded_leakage_rows": int(len(raw) - len(frame)),
        "query_count": int(frame["query_image_id"].nunique()),
        "positive_pair_rows": int(frame["phase17a_label"].sum()),
        "false_pair_rows": int((~frame["phase17a_label"].astype(bool)).sum()),
        "policies_present": sorted(present_policies),
        "diagnostic_minus_descriptor_hit_delta_at_k10": hit_delta_at_k10,
        "descriptor_minus_diagnostic_false_per_query_delta_at_k10": false_delta_at_k10,
        "next_claim_rule": (
            "Use Phase17A for review-utility endpoints. Do not convert these outputs into a "
            "top-k identity-ranking improvement claim unless a later validation clears the locked gate."
        ),
    }
    return audit


def write_report(
    audit: dict[str, object],
    budget_metrics: pd.DataFrame,
    positive_retention: pd.DataFrame,
    abstention: pd.DataFrame,
    conflict_enrichment: pd.DataFrame,
    action_summary: pd.DataFrame,
    output_dir: Path,
) -> None:
    k10 = budget_metrics[budget_metrics["review_budget_value"].eq(10)].sort_values(
        ["mean_false_retained_per_query", "hit_rate"],
        ascending=[True, False],
    )
    retention90 = positive_retention[positive_retention["target_positive_retention"].eq(0.90)].sort_values(
        "retained_false_pairs"
    )
    coverage20 = abstention[abstention["target_pair_coverage"].eq(0.20)].sort_values(
        ["positive_retention", "false_rate_among_retained"],
        ascending=[False, True],
    )
    lines = [
        "# Phase17A CzechLynx Review-Utility Validation",
        "",
        "This report evaluates PF-ERI as a post-retrieval review-utility layer on known-ID CzechLynx pairs.",
        "It is not a descriptor-replacement or automatic identity-assignment claim.",
        "",
        "## Audit",
        "",
        f"- Status: {audit['status']}",
        f"- Claim status: {audit['claim_status']}",
        f"- Review-scope rows: {audit['review_scope_rows']:,}",
        f"- Excluded leakage rows: {audit['excluded_leakage_rows']:,}",
        f"- Queries: {audit['query_count']:,}",
        f"- Positive pairs: {audit['positive_pair_rows']:,}",
        f"- False pairs: {audit['false_pair_rows']:,}",
        "",
        "## Fixed Review Budget At k=10",
        "",
        "| policy | hit rate | mean false/query | false rate retained | false/positive retained |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in k10.to_dict(orient="records"):
        lines.append(
            f"| {row['policy_id']} | {row['hit_rate']:.4f} | "
            f"{row['mean_false_retained_per_query']:.4f} | {row['false_rate_among_retained']:.4f} | "
            f"{row['false_per_positive_retained']:.4f} |"
        )
    lines.extend(["", "## Fixed Positive Retention Target 0.90", "", "| policy | pair coverage | false retained | false/positive | review pairs/query |", "| --- | ---: | ---: | ---: | ---: |"])
    for row in retention90.to_dict(orient="records"):
        lines.append(
            f"| {row['policy_id']} | {row['actual_pair_coverage']:.4f} | "
            f"{int(row['retained_false_pairs'])} | {row['false_per_positive_retained']:.4f} | "
            f"{row['mean_review_pairs_per_query']:.4f} |"
        )
    lines.extend(["", "## Abstention Coverage Target 0.20", "", "| policy | positive retention | false retained | deferred false rate |", "| --- | ---: | ---: | ---: |"])
    for row in coverage20.to_dict(orient="records"):
        lines.append(
            f"| {row['policy_id']} | {row['positive_retention']:.4f} | "
            f"{int(row['retained_false_pairs'])} | {row['deferred_false_rate']:.4f} |"
        )
    lines.extend(["", "## Conflict Enrichment", "", "| subset | conflict rate | conflict false rate | non-conflict false rate | lift |", "| --- | ---: | ---: | ---: | ---: |"])
    for row in conflict_enrichment.to_dict(orient="records"):
        lines.append(
            f"| {row['subset_name']} | {row['conflict_rate']:.4f} | "
            f"{row['conflict_false_rate']:.4f} | {row['non_conflict_false_rate']:.4f} | "
            f"{row['false_rate_lift_conflict_vs_non_conflict']:.4f} |"
        )
    lines.extend(["", "## Proxy Review Actions", "", "| action | pairs | pair share | positive captured | false rate | conflict rate |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for row in action_summary.to_dict(orient="records"):
        lines.append(
            f"| {row['proxy_review_action']} | {int(row['pair_rows'])} | {row['pair_share']:.4f} | "
            f"{row['positive_share_captured']:.4f} | {row['false_rate']:.4f} | {row['conflict_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Use these outputs to evaluate review utility, risk coverage, conflict enrichment, and review burden.",
            "Do not use them to claim a new descriptor, automatic identity assignment, Bobcat identity accuracy, or unsupported top-k ranking improvement.",
            "",
        ]
    )
    (output_dir / "phase17a_review_utility_report.md").write_text("\n".join(lines))


def run_phase17a_review_utility(
    input_csv: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    exclude_leakage: bool = True,
) -> dict[str, object]:
    raw = load_review_table(input_csv)
    frame = prepare_review_frame(raw, exclude_leakage=exclude_leakage)
    budget_metrics = evaluate_fixed_review_budget(frame)
    positive_retention = evaluate_fixed_positive_retention(frame)
    abstention = evaluate_abstention_coverage(frame)
    conflict_enrichment = evaluate_conflict_enrichment(frame)
    action_frame = assign_proxy_review_actions(frame)
    action_summary = summarize_proxy_actions(action_frame)
    audit = build_audit(raw, frame, budget_metrics, conflict_enrichment)

    output_dir.mkdir(parents=True, exist_ok=True)
    budget_metrics.to_csv(output_dir / "phase17a_fixed_review_budget.csv", index=False)
    positive_retention.to_csv(output_dir / "phase17a_fixed_positive_retention.csv", index=False)
    abstention.to_csv(output_dir / "phase17a_abstention_coverage.csv", index=False)
    conflict_enrichment.to_csv(output_dir / "phase17a_conflict_enrichment.csv", index=False)
    action_frame.to_csv(output_dir / "phase17a_proxy_review_actions.csv", index=False)
    action_summary.to_csv(output_dir / "phase17a_proxy_review_action_summary.csv", index=False)
    (output_dir / "phase17a_review_utility_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n"
    )
    write_report(
        audit,
        budget_metrics,
        positive_retention,
        abstention,
        conflict_enrichment,
        action_summary,
        output_dir,
    )
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--include-leakage", action="store_true")
    args = parser.parse_args()

    audit = run_phase17a_review_utility(
        input_csv=args.input,
        output_dir=args.output_dir,
        exclude_leakage=not args.include_leakage,
    )
    print(f"Status: {audit['status']}")
    print(f"Claim status: {audit['claim_status']}")
    print(f"Review-scope rows: {audit['review_scope_rows']}")
    print(f"Excluded leakage rows: {audit['excluded_leakage_rows']}")
    print(f"Wrote {args.output_dir}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
