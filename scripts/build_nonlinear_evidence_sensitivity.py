#!/usr/bin/env python3
"""Build nonlinear/binned sensitivity checks for PF-ERI evidence features."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADVANCED_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/advanced-mathematical-validation"
CONTRACT_AUDIT_JSON = ADVANCED_DIR / "advanced_mathematical_validation_contract_audit.json"
VALIDATION_TABLE_CSV = (
    PROJECT_ROOT
    / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_reviewability_validation_table.csv"
)
MODEL_METRICS_CSV = (
    PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation/known_id_model_metrics.csv"
)
CONFORMAL_ROUTES_CSV = ADVANCED_DIR / "conformal_selective_pair_routes.csv"
SENSITIVITY_CSV = ADVANCED_DIR / "nonlinear_evidence_sensitivity.csv"
FAMILY_COMPARISON_CSV = ADVANCED_DIR / "nonlinear_evidence_family_comparison.csv"
AUDIT_JSON = ADVANCED_DIR / "feature_effect_monotonicity_audit.json"
REPORT_MD = ADVANCED_DIR / "nonlinear_evidence_sensitivity_README.md"

CORE_FEATURES = [
    "visible_pattern_area_score",
    "body_part_overlap_score",
    "viewpoint_side_compatibility",
    "night_or_motion_blur_risk",
    "cross_descriptor_agreement_score",
    "source_domain_shift_score",
]

FEATURE_DIRECTIONS = {
    "visible_pattern_area_score": "increasing_review_ready",
    "body_part_overlap_score": "increasing_review_ready",
    "viewpoint_side_compatibility": "increasing_review_ready",
    "night_or_motion_blur_risk": "decreasing_review_ready",
    "cross_descriptor_agreement_score": "increasing_review_ready",
    "source_domain_shift_score": "diagnostic_only",
}

FEATURE_CLAIMS = {
    "visible_pattern_area_score": "Visible pattern evidence sensitivity; not estimable if constant.",
    "body_part_overlap_score": "Pair-level body overlap/comparability sensitivity.",
    "viewpoint_side_compatibility": "Pair-level viewpoint compatibility sensitivity; not estimable if constant.",
    "night_or_motion_blur_risk": "Technical blur/night risk sensitivity; not estimable if constant.",
    "cross_descriptor_agreement_score": "Descriptor-evidence agreement sensitivity.",
    "source_domain_shift_score": "Source/domain stress diagnostic only, never a causal shortcut in this table.",
}

MODEL_FAMILIES = ["descriptor_only", "quality_only", "pf_eri_evidence_only", "descriptor_plus_pf_eri"]
PRIMARY_MODEL = "descriptor_plus_pf_eri"
QUALITY_BASELINE = "quality_only"
PF_ERI_BASELINE = "pf_eri_evidence_only"
MIN_UNIQUE_FOR_BINS = 4
DEFAULT_BIN_COUNT = 4
MONOTONIC_TOLERANCE = 1e-12

SENSITIVITY_COLUMNS = [
    "feature_name",
    "descriptor_name",
    "bin_id",
    "bin_count",
    "row_count",
    "unique_feature_values",
    "bin_min",
    "bin_max",
    "mean_feature_value",
    "review_ready_count",
    "not_ready_or_uncertain_count",
    "review_ready_rate",
    "not_ready_or_uncertain_rate",
    "mean_evidence_admission_score",
    "alpha_0_15_admitted_rate",
    "expected_direction",
    "directional_endpoint_effect",
    "monotonic_violation_count",
    "sensitivity_status",
    "claim_boundary",
]

FAMILY_COLUMNS = [
    "scope",
    "model_family",
    "pair_count",
    "auroc",
    "auprc",
    "brier_score",
    "ece_5bin",
    "auroc_delta_vs_quality_only",
    "auroc_delta_vs_descriptor_only",
    "interpretation",
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


def mean(values: list[float]) -> float:
    if not values:
        return math.nan
    return sum(values) / len(values)


def merge_validation_with_routes(
    validation_rows: list[dict[str, str]],
    route_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    route_lookup = {(row["descriptor_name"], row["review_pair_id"]): row for row in route_rows}
    merged = []
    for row in validation_rows:
        route = route_lookup.get((row["descriptor_name"], row["review_pair_id"]), {})
        merged.append({**row, **{f"route_{key}": value for key, value in route.items()}})
    return merged


def rank_quantile_bins(rows: list[dict[str, Any]], feature_name: str, bin_count: int = DEFAULT_BIN_COUNT) -> list[list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: (to_float(row[feature_name]), row["descriptor_name"], row["review_pair_id"]))
    n_rows = len(ordered)
    bins: list[list[dict[str, Any]]] = []
    for bin_index in range(bin_count):
        start = (bin_index * n_rows) // bin_count
        end = ((bin_index + 1) * n_rows) // bin_count
        subset = ordered[start:end]
        if subset:
            bins.append(subset)
    return bins


def tie_aware_quantile_bins(
    rows: list[dict[str, Any]],
    feature_name: str,
    bin_count: int = DEFAULT_BIN_COUNT,
) -> list[list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: (to_float(row[feature_name]), row["descriptor_name"], row["review_pair_id"]))
    value_groups: list[list[dict[str, Any]]] = []
    for row in ordered:
        if not value_groups or to_float(value_groups[-1][0][feature_name]) != to_float(row[feature_name]):
            value_groups.append([row])
        else:
            value_groups[-1].append(row)

    target = max(1, math.ceil(len(rows) / bin_count))
    bins: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for group in value_groups:
        if current and len(current) + len(group) > target and len(bins) < bin_count - 1:
            bins.append(current)
            current = []
        current.extend(group)
    if current:
        bins.append(current)
    return bins


def monotonic_status(
    rates: list[float],
    expected_direction: str,
    unique_values: int,
) -> tuple[str, float | str, int]:
    if unique_values < MIN_UNIQUE_FOR_BINS:
        return "not_estimable_constant_feature", "", 0
    if expected_direction == "diagnostic_only":
        return "diagnostic_only_not_modeled_as_effect", "", 0
    if len(rates) < 2:
        return "not_estimable_sparse_bins", "", 0
    raw_delta = rates[-1] - rates[0]
    if expected_direction == "increasing_review_ready":
        violations = sum(1 for left, right in zip(rates, rates[1:]) if right + MONOTONIC_TOLERANCE < left)
        directional_effect = raw_delta
    elif expected_direction == "decreasing_review_ready":
        violations = sum(1 for left, right in zip(rates, rates[1:]) if right > left + MONOTONIC_TOLERANCE)
        directional_effect = -raw_delta
    else:
        violations = 0
        directional_effect = ""
    if directional_effect == "":
        return "diagnostic_only_not_modeled_as_effect", "", violations
    if violations:
        return "nonlinear_or_nonmonotonic_pattern", directional_effect, violations
    if violations == 0 and directional_effect > MONOTONIC_TOLERANCE:
        return "monotonic_supported", directional_effect, violations
    if abs(directional_effect) <= MONOTONIC_TOLERANCE:
        return "flat_or_weak_endpoint_effect", directional_effect, violations
    return "direction_opposes_expected", directional_effect, violations


def summarize_bins(
    feature_name: str,
    descriptor_name: str,
    rows: list[dict[str, Any]],
    expected_direction: str,
) -> list[dict[str, Any]]:
    values = [to_float(row[feature_name]) for row in rows]
    unique_values = len(set(values))
    if unique_values < MIN_UNIQUE_FOR_BINS:
        bin_groups = [rows]
    else:
        bin_groups = tie_aware_quantile_bins(rows, feature_name)

    bin_ready_rates = []
    for group in bin_groups:
        ready_count = sum(int(row["review_ready_label"]) for row in group)
        bin_ready_rates.append(ready_count / len(group))
    status, directional_effect, violations = monotonic_status(bin_ready_rates, expected_direction, unique_values)
    if status == "monotonic_supported" and min(len(group) for group in bin_groups) < 20:
        status = "monotonic_supported_sparse_bin_caveat"

    output = []
    for index, group in enumerate(bin_groups, start=1):
        feature_values = [to_float(row[feature_name]) for row in group]
        ready_count = sum(int(row["review_ready_label"]) for row in group)
        not_ready_count = sum(int(row["not_ready_or_uncertain_label"]) for row in group)
        route_scores = [
            to_float(row.get("route_evidence_admission_score", ""), math.nan)
            for row in group
            if str(row.get("route_evidence_admission_score", "")).strip()
        ]
        admitted_labels = [row.get("route_alpha_0_15_admitted", "") for row in group]
        admitted_known = [label for label in admitted_labels if label in {"yes", "no"}]
        admitted_rate = (
            sum(1 for label in admitted_known if label == "yes") / len(admitted_known) if admitted_known else ""
        )
        output.append(
            {
                "feature_name": feature_name,
                "descriptor_name": descriptor_name,
                "bin_id": index,
                "bin_count": len(bin_groups),
                "row_count": len(group),
                "unique_feature_values": unique_values,
                "bin_min": min(feature_values),
                "bin_max": max(feature_values),
                "mean_feature_value": mean(feature_values),
                "review_ready_count": ready_count,
                "not_ready_or_uncertain_count": not_ready_count,
                "review_ready_rate": ready_count / len(group),
                "not_ready_or_uncertain_rate": not_ready_count / len(group),
                "mean_evidence_admission_score": mean(route_scores) if route_scores else "",
                "alpha_0_15_admitted_rate": admitted_rate,
                "expected_direction": expected_direction,
                "directional_endpoint_effect": directional_effect,
                "monotonic_violation_count": violations,
                "sensitivity_status": status,
                "claim_boundary": FEATURE_CLAIMS.get(feature_name, "Synthetic or extension feature sensitivity helper."),
            }
        )
    return output


def sensitivity_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    descriptor_names = ["pooled", *sorted({row["descriptor_name"] for row in rows})]
    for feature_name in CORE_FEATURES:
        expected = FEATURE_DIRECTIONS[feature_name]
        for descriptor_name in descriptor_names:
            subset = rows if descriptor_name == "pooled" else [row for row in rows if row["descriptor_name"] == descriptor_name]
            output.extend(summarize_bins(feature_name, descriptor_name, subset, expected))
    return output


def metrics_by_scope_family(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(row["scope"], row["model_family"]): row for row in rows}


def family_comparison_rows(metric_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    lookup = metrics_by_scope_family(metric_rows)
    scopes = sorted({row["scope"] for row in metric_rows})
    output = []
    for scope in scopes:
        quality = lookup[(scope, QUALITY_BASELINE)]
        descriptor = lookup[(scope, "descriptor_only")]
        for family in MODEL_FAMILIES:
            row = lookup[(scope, family)]
            auroc = to_float(row["auroc"])
            delta_quality = auroc - to_float(quality["auroc"])
            delta_descriptor = auroc - to_float(descriptor["auroc"])
            if family == PF_ERI_BASELINE and delta_quality > 0:
                interpretation = "PF-ERI evidence-only exceeds image-quality-only AUROC in this scope."
            elif family == PRIMARY_MODEL and delta_quality > 0:
                interpretation = "Descriptor+PF-ERI exceeds image-quality-only AUROC in this scope."
            elif family == QUALITY_BASELINE:
                interpretation = "Image-quality comparator baseline."
            elif family == "descriptor_only":
                interpretation = "Strong-descriptor comparator baseline."
            else:
                interpretation = "No positive AUROC delta versus image-quality-only in this scope."
            output.append(
                {
                    "scope": scope,
                    "model_family": family,
                    "pair_count": int(row["pair_count"]),
                    "auroc": auroc,
                    "auprc": to_float(row["auprc"]),
                    "brier_score": to_float(row["brier_score"]),
                    "ece_5bin": to_float(row["ece_5bin"]),
                    "auroc_delta_vs_quality_only": delta_quality,
                    "auroc_delta_vs_descriptor_only": delta_descriptor,
                    "interpretation": interpretation,
                    "claim_boundary": "CzechLynx reviewability model-family comparison only; not identity retrieval accuracy.",
                }
            )
    return output


def variation_audit(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    audit = {}
    for feature_name in CORE_FEATURES:
        values = [to_float(row[feature_name]) for row in rows]
        counts = Counter(values)
        audit[feature_name] = {
            "unique_values": len(counts),
            "min": min(values),
            "max": max(values),
            "most_common_value": counts.most_common(1)[0][0],
            "most_common_count": counts.most_common(1)[0][1],
            "estimability_status": (
                "estimable_binned_sensitivity" if len(counts) >= MIN_UNIQUE_FOR_BINS else "not_estimable_constant_feature"
            ),
            "expected_direction": FEATURE_DIRECTIONS[feature_name],
        }
    return audit


def write_report(
    path: Path,
    sensitivity: list[dict[str, Any]],
    family_rows: list[dict[str, Any]],
    audit: dict[str, Any],
) -> None:
    pooled_status = {
        feature: next(
            row["sensitivity_status"]
            for row in sensitivity
            if row["feature_name"] == feature and row["descriptor_name"] == "pooled" and int(row["bin_id"]) == 1
        )
        for feature in CORE_FEATURES
    }
    quality_rows = [
        row for row in family_rows
        if row["scope"] == "pooled" and row["model_family"] in {QUALITY_BASELINE, PF_ERI_BASELINE, PRIMARY_MODEL}
    ]
    lines = [
        "# Nonlinear Evidence Sensitivity",
        "",
        "This report tests whether core PF-ERI evidence features show binned nonlinear or monotonic-style sensitivity in the 400-row CzechLynx known-ID reviewability validation table.",
        "",
        "## Feature Estimability",
        "",
    ]
    for feature in CORE_FEATURES:
        entry = audit["feature_variation"][feature]
        lines.append(
            f"- `{feature}`: {entry['estimability_status']} "
            f"(unique={entry['unique_values']}, min={entry['min']}, max={entry['max']}); pooled status `{pooled_status[feature]}`."
        )
    lines.extend(
        [
            "",
            "## Quality-Only Guardrail",
            "",
        ]
    )
    for row in quality_rows:
        lines.append(
            f"- pooled `{row['model_family']}` AUROC={row['auroc']:.6f}; "
            f"delta_vs_quality={row['auroc_delta_vs_quality_only']:.6f}."
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "Only features with sufficient variation support binned sensitivity claims. Constant features are reported as current design/data limitations, not as null biological effects. Source/domain stress remains diagnostic only because this supervised table has no source variation.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    contract = read_json(CONTRACT_AUDIT_JSON)
    validation_rows = read_csv(VALIDATION_TABLE_CSV)
    route_rows = read_csv(CONFORMAL_ROUTES_CSV)
    merged_rows = merge_validation_with_routes(validation_rows, route_rows)
    sensitivity = sensitivity_rows(merged_rows)
    family_rows = family_comparison_rows(read_csv(MODEL_METRICS_CSV))
    audit = {
        "generated_at": utc_now(),
        "contract_issue": contract.get("issue"),
        "input_files": {
            "contract_audit": project_relative(CONTRACT_AUDIT_JSON),
            "validation_table": project_relative(VALIDATION_TABLE_CSV),
            "model_metrics": project_relative(MODEL_METRICS_CSV),
            "conformal_routes": project_relative(CONFORMAL_ROUTES_CSV),
        },
        "output_files": {
            "sensitivity": project_relative(SENSITIVITY_CSV),
            "family_comparison": project_relative(FAMILY_COMPARISON_CSV),
            "audit": project_relative(AUDIT_JSON),
            "report": project_relative(REPORT_MD),
        },
        "row_count": len(merged_rows),
        "descriptor_counts": dict(Counter(row["descriptor_name"] for row in merged_rows)),
        "feature_variation": variation_audit(merged_rows),
        "method": {
            "binning": "tie_aware_quantile_bins_for_features_with_at_least_4_unique_values",
            "constant_feature_policy": "report_not_estimable_do_not_fit_or_interpolate",
            "monotonic_check": "consecutive_bin_review_ready_rate_violations_against_prespecified_direction",
            "quality_guardrail": "compare PF-ERI evidence-only and descriptor+PF-ERI AUROC against image-quality-only AUROC",
        },
        "claim_boundary": "Nonlinear sensitivity is CzechLynx reviewability evidence only; no identity matching or Bobcat transfer guarantee.",
    }
    write_csv(SENSITIVITY_CSV, sensitivity, SENSITIVITY_COLUMNS)
    write_csv(FAMILY_COMPARISON_CSV, family_rows, FAMILY_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_report(REPORT_MD, sensitivity, family_rows, audit)
    return audit


def main() -> int:
    audit = build()
    print("Nonlinear evidence sensitivity")
    print(f"Rows analyzed: {audit['row_count']}")
    for feature_name, entry in audit["feature_variation"].items():
        print(f"{feature_name}: {entry['estimability_status']} (unique={entry['unique_values']})")
    print(f"Output: {project_relative(SENSITIVITY_CSV)}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
