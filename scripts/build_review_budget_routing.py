#!/usr/bin/env python3
"""Build fixed-budget PF-ERI review-routing diagnostics."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv"
)
ROUTES_CSV = PROJECT_ROOT / "outputs/modeling-validation/risk-calibrated-evidence-admission/risk_calibrated_pair_routes.csv"
BOBCAT_ROUTED_CSV = (
    PROJECT_ROOT / "outputs/modeling-validation/bobcat-wild-urban-transfer-stress/bobcat_transfer_stress_routed_pairs.csv"
)
CONFORMAL_THRESHOLDS_CSV = (
    PROJECT_ROOT / "outputs/modeling-validation/advanced-mathematical-validation/conformal_selective_thresholds.csv"
)
CLUSTER_INTERVALS_CSV = (
    PROJECT_ROOT / "outputs/modeling-validation/advanced-mathematical-validation/cluster_bootstrap_metric_intervals.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs/modeling-validation/review-budget-routing"
CZECH_BUDGET_CSV = OUTPUT_DIR / "czechlynx_budget_risk_coverage.csv"
BOBCAT_BUDGET_CSV = OUTPUT_DIR / "bobcat_budget_allocation.csv"
RECOMMENDATIONS_MD = OUTPUT_DIR / "review_budget_routing_recommendations.md"
AUDIT_JSON = OUTPUT_DIR / "review_budget_routing_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"

CZECH_BUDGETS = [25, 50, 100, 150, 200, 300, 400]
BOBCAT_BUDGETS = [50, 100, 250, 500, 1000, 2500, 5000]
TARGET_ALPHAS = [0.15, 0.30]
ROUTE_PRIORITY = {
    "accept_review": 3,
    "cautious_review": 2,
    "conflict_review": 1,
    "defer_low_evidence": 0,
}

CZECH_COLUMNS = [
    "dataset_scope",
    "strategy",
    "alpha",
    "budget",
    "selected_count",
    "selected_pair_coverage",
    "budget_used_fraction",
    "optimization_objective",
    "constraint_rule",
    "constraint_status",
    "expected_admissible_evidence_sum",
    "mean_predicted_evidence_risk",
    "review_ready_count",
    "not_ready_or_uncertain_count",
    "empirical_risk",
    "empirical_risk_ci_lower",
    "empirical_risk_ci_upper",
    "review_ready_rate",
    "evidence_admissible_coverage",
    "accept_review_count",
    "cautious_review_count",
    "conflict_review_count",
    "defer_low_evidence_count",
    "mean_evidence_admission_score",
    "mean_descriptor_similarity_percentile",
    "claim_boundary",
]
BOBCAT_COLUMNS = [
    "dataset_scope",
    "strategy",
    "alpha",
    "budget",
    "selected_count",
    "selected_pair_coverage",
    "budget_used_fraction",
    "optimization_objective",
    "constraint_rule",
    "constraint_status",
    "expected_admissible_evidence_sum",
    "mean_predicted_evidence_risk",
    "accept_review_count",
    "cautious_review_count",
    "conflict_review_count",
    "defer_low_evidence_count",
    "mean_evidence_admission_score",
    "mean_descriptor_similarity_percentile",
    "empirical_risk",
    "review_ready_rate",
    "claim_boundary",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def sum_value(rows: list[dict[str, Any]], column: str) -> float:
    return sum(to_float(row.get(column)) for row in rows)


def merge_czechlynx_rows() -> list[dict[str, Any]]:
    validation_rows = {
        (row["descriptor_name"], row["review_pair_id"]): row
        for row in read_csv(VALIDATION_TABLE_CSV)
    }
    output = []
    for route in read_csv(ROUTES_CSV):
        key = (route["descriptor_name"], route["review_pair_id"])
        validation = validation_rows[key]
        output.append({**validation, **route})
    return output


def pferi_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            ROUTE_PRIORITY.get(str(row.get("route_label", "")), -1),
            to_float(row.get("evidence_admission_score")),
            to_float(row.get("descriptor_similarity_percentile")),
        ),
        reverse=True,
    )


def descriptor_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            to_float(row.get("descriptor_similarity_percentile")),
            to_float(row.get("evidence_admission_score")),
        ),
        reverse=True,
    )


def route_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(row.get("route_label", "")) for row in rows)


def mean_value(rows: list[dict[str, Any]], column: str) -> float | str:
    if not rows:
        return ""
    return sum(to_float(row.get(column)) for row in rows) / len(rows)


def risk_score(row: dict[str, Any]) -> float:
    if str(row.get("evidence_risk_score", "")).strip():
        return to_float(row["evidence_risk_score"])
    return 1.0 - to_float(row.get("evidence_admission_score"))


def mean_predicted_risk(rows: list[dict[str, Any]]) -> float | str:
    if not rows:
        return ""
    return sum(risk_score(row) for row in rows) / len(rows)


def fixed_budget_prefix(rows: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    return rows[: min(budget, len(rows))]


def risk_constrained_prefix(rows: list[dict[str, Any]], budget: int, alpha: float) -> list[dict[str, Any]]:
    max_count = min(budget, len(rows))
    best: list[dict[str, Any]] = []
    best_value = -1.0
    for count in range(1, max_count + 1):
        candidate = rows[:count]
        predicted_risk = mean_predicted_risk(candidate)
        if predicted_risk == "" or predicted_risk > alpha:
            continue
        value = sum_value(candidate, "evidence_admission_score")
        if value > best_value or (value == best_value and len(candidate) > len(best)):
            best = candidate
            best_value = value
    return best


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float | str, float | str]:
    if total <= 0:
        return "", ""
    phat = successes / total
    denominator = 1.0 + z * z / total
    center = (phat + z * z / (2.0 * total)) / denominator
    half_width = z * ((phat * (1.0 - phat) / total + z * z / (4.0 * total * total)) ** 0.5) / denominator
    return max(0.0, center - half_width), min(1.0, center + half_width)


def cluster_interval(metric: str, scope: str = "all", cluster_family: str = "query_image_cluster") -> dict[str, str]:
    if not CLUSTER_INTERVALS_CSV.exists():
        return {}
    for row in read_csv(CLUSTER_INTERVALS_CSV):
        if row["cluster_family"] == cluster_family and row["scope"] == scope and row["metric"] == metric:
            return row
    return {}


def conformal_thresholds_by_alpha() -> dict[float, dict[str, str]]:
    if not CONFORMAL_THRESHOLDS_CSV.exists():
        return {}
    return {to_float(row["alpha"]): row for row in read_csv(CONFORMAL_THRESHOLDS_CSV)}


def czech_budget_metrics(
    rows: list[dict[str, Any]],
    strategy: str,
    budget: int,
    alpha: float,
    risk_constrained: bool = True,
) -> dict[str, Any]:
    selected = risk_constrained_prefix(rows, budget, alpha) if risk_constrained else fixed_budget_prefix(rows, budget)
    counts = route_counts(selected)
    total_ready = sum(int(row["review_ready_label"]) for row in rows)
    ready = sum(int(row["review_ready_label"]) for row in selected)
    not_ready = sum(int(row["not_ready_or_uncertain_label"]) for row in selected)
    selected_count = len(selected)
    lower, upper = wilson_interval(not_ready, selected_count)
    predicted_risk = mean_predicted_risk(selected)
    if selected_count == 0:
        constraint_status = "no_feasible_prefix"
    elif not risk_constrained:
        constraint_status = "not_enforced_fixed_budget_baseline"
    else:
        constraint_status = "predicted_risk_constraint_satisfied" if predicted_risk <= alpha else "predicted_risk_constraint_violated"
    return {
        "dataset_scope": "czechlynx_known_id_reviewed_pairs",
        "strategy": strategy,
        "alpha": alpha,
        "budget": budget,
        "selected_count": selected_count,
        "selected_pair_coverage": selected_count / len(rows) if rows else 0.0,
        "budget_used_fraction": selected_count / budget if budget else 0.0,
        "optimization_objective": "maximize_sum_evidence_admission_score_subject_to_selected_count_le_budget_and_mean_predicted_risk_le_alpha",
        "constraint_rule": (
            "mean(evidence_risk_score)<=alpha"
            if risk_constrained
            else "not_enforced_descriptor_fixed_budget_baseline"
        ),
        "constraint_status": constraint_status,
        "expected_admissible_evidence_sum": sum_value(selected, "evidence_admission_score"),
        "mean_predicted_evidence_risk": predicted_risk,
        "review_ready_count": ready,
        "not_ready_or_uncertain_count": not_ready,
        "empirical_risk": not_ready / selected_count if selected_count else "",
        "empirical_risk_ci_lower": lower,
        "empirical_risk_ci_upper": upper,
        "review_ready_rate": ready / selected_count if selected_count else "",
        "evidence_admissible_coverage": ready / total_ready if total_ready else "",
        "accept_review_count": counts["accept_review"],
        "cautious_review_count": counts["cautious_review"],
        "conflict_review_count": counts["conflict_review"],
        "defer_low_evidence_count": counts["defer_low_evidence"],
        "mean_evidence_admission_score": mean_value(selected, "evidence_admission_score"),
        "mean_descriptor_similarity_percentile": mean_value(selected, "descriptor_similarity_percentile"),
        "claim_boundary": "Known-ID reviewed-pair budget optimization diagnostics; selection uses predicted risk, empirical risk is post hoc.",
    }


def bobcat_budget_metrics(rows: list[dict[str, Any]], budget: int, alpha: float) -> dict[str, Any]:
    selected = risk_constrained_prefix(rows, budget, alpha)
    counts = route_counts(selected)
    predicted_risk = mean_predicted_risk(selected)
    return {
        "dataset_scope": "bobcat_unlabeled_transfer_stress_pairs",
        "strategy": "pferi_risk_constrained_workflow_queue",
        "alpha": alpha,
        "budget": budget,
        "selected_count": len(selected),
        "selected_pair_coverage": len(selected) / len(rows) if rows else 0.0,
        "budget_used_fraction": len(selected) / budget if budget else 0.0,
        "optimization_objective": "maximize_sum_evidence_admission_score_subject_to_selected_count_le_budget_and_mean_predicted_risk_le_alpha",
        "constraint_rule": "mean(evidence_risk_score)<=alpha",
        "constraint_status": "no_feasible_prefix" if not selected else "predicted_risk_constraint_satisfied",
        "expected_admissible_evidence_sum": sum_value(selected, "evidence_admission_score"),
        "mean_predicted_evidence_risk": predicted_risk,
        "accept_review_count": counts["accept_review"],
        "cautious_review_count": counts["cautious_review"],
        "conflict_review_count": counts["conflict_review"],
        "defer_low_evidence_count": counts["defer_low_evidence"],
        "mean_evidence_admission_score": mean_value(selected, "evidence_admission_score"),
        "mean_descriptor_similarity_percentile": mean_value(selected, "descriptor_similarity_percentile"),
        "empirical_risk": "not_estimable_without_bobcat_review_labels",
        "review_ready_rate": "not_estimable_without_bobcat_review_labels",
        "claim_boundary": "Budget allocation only; no Bobcat identity or reviewability ground-truth estimate.",
    }


def best_row(rows: list[dict[str, Any]], strategy: str, budget: int) -> dict[str, Any]:
    candidates = [row for row in rows if row["strategy"] == strategy and int(row["budget"]) == budget]
    if not candidates:
        raise ValueError(f"missing row for {strategy} budget={budget}")
    return candidates[0]


def write_recommendations(czech_rows: list[dict[str, Any]], bobcat_rows: list[dict[str, Any]]) -> None:
    pferi_100 = best_row(czech_rows, "pferi_risk_constrained_queue", 100)
    descriptor_100 = best_row(czech_rows, "descriptor_rank_fixed_budget_unconstrained", 100)
    bobcat_100 = best_row(bobcat_rows, "pferi_risk_constrained_workflow_queue", 100)
    lines = [
        "# Review-Budget Routing Recommendations",
        "",
        "## Practical Rule",
        "",
        "For a target risk alpha, select the feasible PF-ERI prefix that maximizes",
        "the sum of evidence admission scores under the budget. Descriptor rank remains",
        "a retrieval order baseline, not a review-readiness proxy.",
        "",
        "## CzechLynx Budget 100 Comparison",
        "",
        f"- PF-ERI alpha: `{pferi_100['alpha']}`",
        f"- PF-ERI selected count: `{pferi_100['selected_count']}`",
        f"- PF-ERI mean predicted risk: `{pferi_100['mean_predicted_evidence_risk']}`",
        f"- PF-ERI empirical risk: `{pferi_100['empirical_risk']}`",
        f"- PF-ERI evidence-admissible coverage: `{pferi_100['evidence_admissible_coverage']}`",
        f"- Descriptor-only empirical risk: `{descriptor_100['empirical_risk']}`",
        f"- Descriptor-only evidence-admissible coverage: `{descriptor_100['evidence_admissible_coverage']}`",
        "",
        "## Bobcat Boundary",
        "",
        f"At budget 100, Bobcat selected pairs are `{bobcat_100['selected_count']}`,",
        f"with `{bobcat_100['accept_review_count']}` accept-review routes. Empirical risk",
        "is not estimated because Bobcat lacks review labels and same/different identity labels",
        "in this workflow.",
    ]
    RECOMMENDATIONS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    czech_rows = merge_czechlynx_rows()
    pferi_rows = pferi_queue(czech_rows)
    descriptor_rows = descriptor_queue(czech_rows)
    czech_budget_rows = []
    for alpha in TARGET_ALPHAS:
        for budget in CZECH_BUDGETS:
            czech_budget_rows.append(czech_budget_metrics(pferi_rows, "pferi_risk_constrained_queue", budget, alpha))
            czech_budget_rows.append(
                czech_budget_metrics(descriptor_rows, "descriptor_rank_risk_checked_queue", budget, alpha)
            )
            czech_budget_rows.append(
                czech_budget_metrics(
                    descriptor_rows,
                    "descriptor_rank_fixed_budget_unconstrained",
                    budget,
                    alpha,
                    risk_constrained=False,
                )
            )

    bobcat_rows = pferi_queue(read_csv(BOBCAT_ROUTED_CSV))
    bobcat_budget_rows = [
        bobcat_budget_metrics(bobcat_rows, budget, alpha)
        for alpha in TARGET_ALPHAS
        for budget in BOBCAT_BUDGETS
    ]
    write_csv(CZECH_BUDGET_CSV, czech_budget_rows, CZECH_COLUMNS)
    write_csv(BOBCAT_BUDGET_CSV, bobcat_budget_rows, BOBCAT_COLUMNS)
    write_recommendations(czech_budget_rows, bobcat_budget_rows)

    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if czech_budget_rows and bobcat_budget_rows else "FAIL",
        "input_validation_table_csv": project_relative(VALIDATION_TABLE_CSV),
        "input_routes_csv": project_relative(ROUTES_CSV),
        "input_bobcat_routed_csv": project_relative(BOBCAT_ROUTED_CSV),
        "input_conformal_thresholds_csv": project_relative(CONFORMAL_THRESHOLDS_CSV),
        "input_cluster_intervals_csv": project_relative(CLUSTER_INTERVALS_CSV),
        "czech_budget_csv": project_relative(CZECH_BUDGET_CSV),
        "bobcat_budget_csv": project_relative(BOBCAT_BUDGET_CSV),
        "recommendations_md": project_relative(RECOMMENDATIONS_MD),
        "czech_pair_rows": len(czech_rows),
        "bobcat_pair_rows": len(bobcat_rows),
        "czech_budgets": CZECH_BUDGETS,
        "bobcat_budgets": BOBCAT_BUDGETS,
        "target_alphas": TARGET_ALPHAS,
        "strategies": [
            "pferi_risk_constrained_queue",
            "descriptor_rank_risk_checked_queue",
            "descriptor_rank_fixed_budget_unconstrained",
        ],
        "objective": "maximize sum evidence_admission_score with selected_count<=B and mean predicted evidence_risk_score<=alpha",
        "selection_leakage_guard": "Human review labels are not used for selection; they are used only for post-selection empirical risk reporting.",
        "conformal_thresholds_seen": sorted(str(key) for key in conformal_thresholds_by_alpha().keys()),
        "cluster_uncertainty_reference": cluster_interval("alpha_0_15_selective_risk"),
        "bobcat_descriptor_baseline_status": "not_estimable_without_bobcat_returned_pair_descriptor_scores",
        "claim_boundary": "Review-budget allocation only; not identity accuracy or descriptor performance.",
    }
    write_json(AUDIT_JSON, audit)
    write_report(audit)
    return audit


def write_report(audit: dict[str, Any]) -> None:
    cluster_reference = audit.get("cluster_uncertainty_reference", {})
    lines = [
        "# Review-Budget Routing",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This module turns the PF-ERI selective evidence router into fixed-budget",
        "risk-constrained workflow optimization for review triage.",
        "",
        "## Objective",
        "",
        audit["objective"],
        "",
        "Selection uses predicted evidence risk only. Human labels are reserved for",
        "post-selection empirical risk audits.",
        "",
        "This is a predicted-risk budget optimizer, not a new finite-sample conformal",
        "guarantee. The conformal thresholds and cluster bootstrap intervals are consumed",
        "as calibration/uncertainty references.",
        "",
        "## Uncertainty Reference",
        "",
        f"- Metric: `{cluster_reference.get('metric', '')}`",
        f"- Point estimate: `{cluster_reference.get('point_estimate', '')}`",
        f"- 95% cluster CI: `{cluster_reference.get('ci_lower', '')}` to `{cluster_reference.get('ci_upper', '')}`",
        f"- Status: `{cluster_reference.get('uncertainty_status', '')}`",
        "",
        "## Outputs",
        "",
        f"- CzechLynx risk/coverage table: `{audit['czech_budget_csv']}`",
        f"- Bobcat allocation table: `{audit['bobcat_budget_csv']}`",
        f"- Workflow recommendation: `{audit['recommendations_md']}`",
        "",
        "## Boundary",
        "",
        audit["claim_boundary"],
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
