#!/usr/bin/env python3
"""Build cluster-aware uncertainty intervals for PF-ERI validation metrics."""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts import build_known_id_evidence_sufficiency_validation as validation
except ImportError:  # pragma: no cover - direct script execution
    import build_known_id_evidence_sufficiency_validation as validation


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADVANCED_DIR = PROJECT_ROOT / "outputs/modeling-validation/advanced-mathematical-validation"
CONTRACT_AUDIT_JSON = ADVANCED_DIR / "advanced_mathematical_validation_contract_audit.json"
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv"
)
CONFORMAL_ROUTES_CSV = ADVANCED_DIR / "conformal_selective_pair_routes.csv"
METRIC_INTERVALS_CSV = ADVANCED_DIR / "cluster_bootstrap_metric_intervals.csv"
RESAMPLING_AUDIT_JSON = ADVANCED_DIR / "cluster_bootstrap_resampling_audit.json"
DIAGNOSTICS_CSV = ADVANCED_DIR / "cluster_bootstrap_diagnostics.csv"
REPORT_MD = ADVANCED_DIR / "cluster_bootstrap_uncertainty_README.md"

RANDOM_SEED = 20260707
BOOTSTRAP_ITERATIONS = 500
ALPHA_ROUTE_COLUMN = "alpha_0_15_admitted"
CLUSTER_SPECS = [
    ("query_image_cluster", "query_pferi_image_id"),
    ("component_group_cluster", "component_group_id"),
]
METRIC_COLUMNS = [
    "cluster_family",
    "scope",
    "metric",
    "point_estimate",
    "ci_lower",
    "ci_upper",
    "bootstrap_iterations_requested",
    "bootstrap_iterations_used",
    "cluster_count",
    "row_count",
    "uncertainty_status",
    "skipped_reason",
    "claim_boundary",
]
DIAGNOSTIC_COLUMNS = [
    "cluster_family",
    "cluster_column",
    "cluster_count",
    "row_count",
    "min_cluster_size",
    "max_cluster_size",
    "identity_bootstrap_status",
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def merge_validation_and_conformal_routes() -> list[dict[str, Any]]:
    validation_rows = {
        (row["descriptor_name"], row["review_pair_id"]): row
        for row in read_csv(VALIDATION_TABLE_CSV)
    }
    output = []
    for route in read_csv(CONFORMAL_ROUTES_CSV):
        key = (route["descriptor_name"], route["review_pair_id"])
        output.append({**validation_rows[key], **route})
    return output


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def average_precision(labels: list[int], scores: list[float]) -> float:
    positives = sum(labels)
    if positives == 0:
        return 0.0
    ranked = sorted(zip(scores, labels), reverse=True)
    hits = 0
    precision_sum = 0.0
    for rank, (_, label) in enumerate(ranked, start=1):
        if label == 1:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / positives


def metric_value(rows: list[dict[str, Any]], metric: str) -> float | None:
    if not rows:
        return None
    labels_ready = [int(row["review_ready_label"]) for row in rows]
    scores = [to_float(row["evidence_admission_score"]) for row in rows]
    if metric == "auroc":
        if len(set(labels_ready)) < 2:
            return None
        return validation.auroc(labels_ready, scores)
    if metric == "auprc":
        if len(set(labels_ready)) < 2:
            return None
        return average_precision(labels_ready, scores)
    if metric == "brier_score":
        return validation.brier(labels_ready, scores)
    if metric == "ece_5bin":
        return validation.ece(labels_ready, scores)
    admitted = [row for row in rows if row[ALPHA_ROUTE_COLUMN] == "yes"]
    if metric == "alpha_0_15_selective_risk":
        if not admitted:
            return None
        return sum(int(row["not_ready_or_uncertain_label"]) for row in admitted) / len(admitted)
    if metric == "alpha_0_15_coverage":
        return len(admitted) / len(rows)
    raise ValueError(f"unknown metric: {metric}")


def rows_by_cluster(rows: list[dict[str, Any]], cluster_column: str) -> dict[str, list[dict[str, Any]]]:
    clusters: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        cluster_id = str(row.get(cluster_column, "")).strip()
        clusters.setdefault(cluster_id, []).append(row)
    return clusters


def cluster_bootstrap_samples(
    rows: list[dict[str, Any]],
    cluster_column: str,
    iterations: int = BOOTSTRAP_ITERATIONS,
    seed: int = RANDOM_SEED,
) -> list[list[dict[str, Any]]]:
    clusters = rows_by_cluster(rows, cluster_column)
    cluster_ids = sorted(clusters)
    rng = random.Random(seed)
    samples = []
    for _ in range(iterations):
        sampled_rows: list[dict[str, Any]] = []
        sampled_cluster_ids = [rng.choice(cluster_ids) for _ in cluster_ids]
        for cluster_id in sampled_cluster_ids:
            sampled_rows.extend(clusters[cluster_id])
        samples.append(sampled_rows)
    return samples


def interval_row(
    rows: list[dict[str, Any]],
    cluster_family: str,
    cluster_column: str,
    scope: str,
    metric: str,
) -> dict[str, Any]:
    subset = [row for row in rows if scope == "all" or row["calibration_role"] == scope]
    point = metric_value(subset, metric)
    clusters = rows_by_cluster(subset, cluster_column)
    estimates = []
    skipped_reason = ""
    if point is None:
        skipped_reason = "point_metric_not_estimable"
    elif len(clusters) < 2:
        skipped_reason = "cluster_count_lt_2"
    else:
        for sample in cluster_bootstrap_samples(subset, cluster_column):
            value = metric_value(sample, metric)
            if value is not None:
                estimates.append(value)
        if not estimates:
            skipped_reason = "bootstrap_metric_not_estimable"
    return {
        "cluster_family": cluster_family,
        "scope": scope,
        "metric": metric,
        "point_estimate": point if point is not None else "",
        "ci_lower": percentile(estimates, 0.025) if estimates else "",
        "ci_upper": percentile(estimates, 0.975) if estimates else "",
        "bootstrap_iterations_requested": BOOTSTRAP_ITERATIONS,
        "bootstrap_iterations_used": len(estimates),
        "cluster_count": len(clusters),
        "row_count": len(subset),
        "uncertainty_status": "sparse_cluster_warning" if len(clusters) < 10 else "cluster_interval_reportable",
        "skipped_reason": skipped_reason,
        "claim_boundary": "Cluster-aware uncertainty for CzechLynx reviewability only; not a Bobcat identity metric.",
    }


def diagnostics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    identity_status = "not_feasible_identity_relation_has_only_yes_no_not_resolved_identity_clusters"
    for family, column in CLUSTER_SPECS:
        clusters = rows_by_cluster(rows, column)
        sizes = [len(value) for value in clusters.values()]
        out.append(
            {
                "cluster_family": family,
                "cluster_column": column,
                "cluster_count": len(clusters),
                "row_count": len(rows),
                "min_cluster_size": min(sizes) if sizes else 0,
                "max_cluster_size": max(sizes) if sizes else 0,
                "identity_bootstrap_status": identity_status,
            }
        )
    return out


def build() -> dict[str, Any]:
    contract = read_json(CONTRACT_AUDIT_JSON)
    rows = merge_validation_and_conformal_routes()
    metrics = ["auroc", "auprc", "brier_score", "ece_5bin", "alpha_0_15_selective_risk", "alpha_0_15_coverage"]
    scopes = ["all", "calibration", "evaluation"]
    interval_rows = []
    for family, column in CLUSTER_SPECS:
        for scope in scopes:
            for metric in metrics:
                interval_rows.append(interval_row(rows, family, column, scope, metric))
    diagnostic_rows = diagnostics(rows)
    skipped_counts: dict[str, int] = {}
    uncertainty_status_counts: dict[str, int] = {}
    for row in interval_rows:
        if row["skipped_reason"]:
            skipped_counts[str(row["skipped_reason"])] = skipped_counts.get(str(row["skipped_reason"]), 0) + 1
        uncertainty_status_counts[str(row["uncertainty_status"])] = uncertainty_status_counts.get(str(row["uncertainty_status"]), 0) + 1
    audit = {
        "built_at_utc": utc_now(),
        "status": "PASS" if contract.get("status") == "PASS" and interval_rows and diagnostic_rows else "FAIL",
        "input_contract_audit_json": project_relative(CONTRACT_AUDIT_JSON),
        "input_validation_table_csv": project_relative(VALIDATION_TABLE_CSV),
        "input_conformal_routes_csv": project_relative(CONFORMAL_ROUTES_CSV),
        "metric_intervals_csv": project_relative(METRIC_INTERVALS_CSV),
        "diagnostics_csv": project_relative(DIAGNOSTICS_CSV),
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "random_seed": RANDOM_SEED,
        "row_count": len(rows),
        "cluster_specs": [{"cluster_family": family, "cluster_column": column} for family, column in CLUSTER_SPECS],
        "metric_count": len(interval_rows),
        "skipped_metric_counts": dict(sorted(skipped_counts.items())),
        "uncertainty_status_counts": dict(sorted(uncertainty_status_counts.items())),
        "identity_bootstrap_status": diagnostic_rows[0]["identity_bootstrap_status"] if diagnostic_rows else "",
        "claim_boundary": "Cluster-aware uncertainty intervals for CzechLynx reviewability; Bobcat identity claims remain blocked.",
    }
    write_csv(METRIC_INTERVALS_CSV, interval_rows, METRIC_COLUMNS)
    write_csv(DIAGNOSTICS_CSV, diagnostic_rows, DIAGNOSTIC_COLUMNS)
    write_json(RESAMPLING_AUDIT_JSON, audit)
    write_report(audit)
    return audit


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Cluster Bootstrap Uncertainty",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This module estimates uncertainty for PF-ERI validation metrics by",
        "resampling clusters instead of individual rows.",
        "",
        "## Cluster Units",
        "",
        "- `query_image_cluster`: rows grouped by query PF-ERI image id.",
        "- `component_group_cluster`: rows grouped by connected fold/component group.",
        "",
        "## Identity Bootstrap",
        "",
        audit["identity_bootstrap_status"],
        "",
        "## Sparse Cluster Warning",
        "",
        "Intervals with fewer than 10 clusters are reported as diagnostics, not",
        "high-precision uncertainty estimates. Component-group calibration and",
        "evaluation splits are especially sparse because they contain only a few",
        "fold/component clusters.",
        "",
        "## Outputs",
        "",
        f"- Metric intervals: `{audit['metric_intervals_csv']}`",
        f"- Diagnostics: `{audit['diagnostics_csv']}`",
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
