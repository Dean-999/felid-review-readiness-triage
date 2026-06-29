#!/usr/bin/env python3
"""Build Phase16H CzechLynx readiness controls before model training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "outputs/phase16/phase16g_czechlynx_real_pair_table/phase16g_czechlynx_pair_table.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16h_czechlynx_readiness_controls"
K_VALUES = [1, 5, 10, 20, 50]
RISK_COVERAGE_LEVELS = [0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00]
REQUIRED_COLUMNS = [
    "pair_id",
    "query_image_id",
    "candidate_image_id",
    "descriptor_similarity",
    "weakest_iqa_score",
    "query_side_probability",
    "candidate_side_probability",
    "descriptor_margin",
    "source_leakage_pressure_flag",
    "laterality_relation",
    "same_identity_label",
    "label_allowed_for_modeling",
    "split_group",
]


def _numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(frame.get(column, default), errors="coerce").fillna(default).astype(float)


def _bool_series(frame: pd.DataFrame, column: str, default: bool = False) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=bool)
    values = frame[column]
    if values.dtype == bool:
        return values.fillna(default)
    return values.astype(str).str.lower().isin({"true", "1", "yes"})


def _normalise_0_1(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0)
    low = float(numeric.min())
    high = float(numeric.max())
    if high <= low:
        return pd.Series(0.0, index=series.index)
    return (numeric - low) / (high - low)


def load_pair_table(input_csv: Path) -> pd.DataFrame:
    table = pd.read_csv(input_csv, low_memory=False)
    missing = [column for column in REQUIRED_COLUMNS if column not in table.columns]
    if missing:
        raise ValueError("Phase16H input missing required columns: " + ", ".join(missing))
    return table


def compute_policy_scores(pair_table: pd.DataFrame) -> pd.DataFrame:
    out = pair_table.copy()
    descriptor = _normalise_0_1(_numeric(out, "descriptor_similarity"))
    weakest_iqa = _normalise_0_1(_numeric(out, "weakest_iqa_score"))
    weakest_side = _normalise_0_1(
        pd.concat(
            [
                _numeric(out, "query_side_probability"),
                _numeric(out, "candidate_side_probability"),
            ],
            axis=1,
        ).min(axis=1)
    )
    conflict = _normalise_0_1(_numeric(out, "descriptor_margin"))
    leakage = _bool_series(out, "source_leakage_pressure_flag").astype(float)

    out["score_descriptor_only"] = descriptor
    out["score_quality_only"] = weakest_iqa
    out["score_evidence_only"] = (0.60 * weakest_iqa) + (0.40 * weakest_side)
    out["score_conflict_penalized_descriptor"] = descriptor - (0.35 * conflict)
    out["score_phase16h_diagnostic"] = (
        (0.45 * descriptor)
        + (0.25 * weakest_iqa)
        + (0.20 * weakest_side)
        - (0.07 * conflict)
        - (0.03 * leakage)
    )
    out["phase16h_label"] = _bool_series(out, "same_identity_label")
    return out


def _topk_for_score(frame: pd.DataFrame, score_column: str, policy_id: str, k_values: list[int]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    ranked = frame.copy()
    ranked["_policy_rank"] = ranked.groupby("query_image_id")[score_column].rank(method="first", ascending=False)
    all_queries = pd.DataFrame(index=ranked["query_image_id"].drop_duplicates())
    for k in k_values:
        top = ranked[ranked["_policy_rank"] <= k]
        per_query = top.groupby("query_image_id")["phase16h_label"].agg(
            retained_pairs="size",
            retained_positive=lambda s: int(s.sum()),
            retained_false=lambda s: int((~s.astype(bool)).sum()),
        )
        per_query = all_queries.join(per_query).fillna(0)
        rows.append(
            {
                "policy_id": policy_id,
                "k": int(k),
                "queries": int(len(per_query)),
                "retained_pairs": int(len(top)),
                "hit_rate": float((per_query["retained_positive"] > 0).mean()),
                "mean_false_retained_per_query": float(per_query["retained_false"].mean()),
                "mean_positive_retained_per_query": float(per_query["retained_positive"].mean()),
                "false_rate_among_retained": float((~top["phase16h_label"].astype(bool)).mean()) if len(top) else np.nan,
                "random_repeats": 0,
            }
        )
    return rows


def _random_same_size(frame: pd.DataFrame, k_values: list[int], random_repeats: int, random_seed: int) -> list[dict[str, object]]:
    rng = np.random.default_rng(random_seed)
    rows: list[dict[str, object]] = []
    groups = list(frame.groupby("query_image_id", sort=False))
    for k in k_values:
        repeat_rows = []
        for _ in range(random_repeats):
            sampled_parts = []
            for _, group in groups:
                take = min(k, len(group))
                sampled_idx = rng.choice(group.index.to_numpy(), size=take, replace=False)
                sampled_parts.append(frame.loc[sampled_idx])
            sampled = pd.concat(sampled_parts, ignore_index=True) if sampled_parts else frame.iloc[0:0]
            per_query = sampled.groupby("query_image_id")["phase16h_label"].agg(
                retained_pairs="size",
                retained_positive=lambda s: int(s.sum()),
                retained_false=lambda s: int((~s.astype(bool)).sum()),
            )
            all_queries = pd.DataFrame(index=frame["query_image_id"].drop_duplicates())
            per_query = all_queries.join(per_query).fillna(0)
            repeat_rows.append(
                {
                    "hit_rate": float((per_query["retained_positive"] > 0).mean()),
                    "mean_false_retained_per_query": float(per_query["retained_false"].mean()),
                    "mean_positive_retained_per_query": float(per_query["retained_positive"].mean()),
                    "false_rate_among_retained": float((~sampled["phase16h_label"].astype(bool)).mean()) if len(sampled) else np.nan,
                    "retained_pairs": int(len(sampled)),
                }
            )
        repeat_frame = pd.DataFrame(repeat_rows)
        rows.append(
            {
                "policy_id": "random_same_size",
                "k": int(k),
                "queries": int(frame["query_image_id"].nunique()),
                "retained_pairs": float(repeat_frame["retained_pairs"].mean()),
                "hit_rate": float(repeat_frame["hit_rate"].mean()),
                "mean_false_retained_per_query": float(repeat_frame["mean_false_retained_per_query"].mean()),
                "mean_positive_retained_per_query": float(repeat_frame["mean_positive_retained_per_query"].mean()),
                "false_rate_among_retained": float(repeat_frame["false_rate_among_retained"].mean()),
                "random_repeats": int(random_repeats),
            }
        )
    return rows


def evaluate_topk_controls(
    scored: pd.DataFrame,
    k_values: list[int] | None = None,
    random_repeats: int = 50,
    random_seed: int = 20260628,
) -> pd.DataFrame:
    k_values = k_values or K_VALUES
    policy_scores = {
        "descriptor_only": "score_descriptor_only",
        "quality_only": "score_quality_only",
        "evidence_only": "score_evidence_only",
        "conflict_penalized_descriptor": "score_conflict_penalized_descriptor",
        "phase16h_diagnostic_no_training": "score_phase16h_diagnostic",
    }
    rows: list[dict[str, object]] = []
    for policy_id, score_column in policy_scores.items():
        rows.extend(_topk_for_score(scored, score_column, policy_id, k_values))
    rows.extend(_random_same_size(scored, k_values, random_repeats, random_seed))
    return pd.DataFrame(rows)


def evaluate_risk_coverage(scored: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    score_columns = {
        "descriptor_only": "score_descriptor_only",
        "phase16h_diagnostic_no_training": "score_phase16h_diagnostic",
    }
    all_queries = pd.DataFrame(index=scored["query_image_id"].drop_duplicates())
    for policy_id, score_column in score_columns.items():
        for coverage in RISK_COVERAGE_LEVELS:
            threshold = scored[score_column].quantile(1.0 - coverage)
            retained = scored[scored[score_column] >= threshold]
            per_query = retained.groupby("query_image_id")["phase16h_label"].agg(
                retained_pairs="size",
                retained_positive=lambda s: int(s.sum()),
                retained_false=lambda s: int((~s.astype(bool)).sum()),
            )
            per_query = all_queries.join(per_query).fillna(0)
            rows.append(
                {
                    "policy_id": policy_id,
                    "target_pair_coverage": float(coverage),
                    "actual_pair_coverage": float(len(retained) / max(len(scored), 1)),
                    "query_coverage": float((per_query["retained_pairs"] > 0).mean()),
                    "hit_rate": float((per_query["retained_positive"] > 0).mean()),
                    "mean_false_retained_per_query": float(per_query["retained_false"].mean()),
                    "mean_positive_retained_per_query": float(per_query["retained_positive"].mean()),
                    "score_threshold": float(threshold),
                }
            )
    return pd.DataFrame(rows)


def evaluate_leakage_sensitivity(scored: pd.DataFrame, k_values: list[int] | None = None) -> pd.DataFrame:
    k_values = k_values or [1, 5, 10, 20]
    leakage = _bool_series(scored, "source_leakage_pressure_flag")
    subsets = {
        "all_pairs": scored,
        "leakage_excluded": scored[~leakage].copy(),
        "leakage_only": scored[leakage].copy(),
    }
    rows: list[pd.DataFrame] = []
    for subset_name, subset in subsets.items():
        if subset.empty:
            continue
        metrics = evaluate_topk_controls(
            subset,
            k_values=k_values,
            random_repeats=10,
            random_seed=20260628,
        )
        metrics["sensitivity_subset"] = subset_name
        metrics["subset_pair_rows"] = int(len(subset))
        metrics["source_leakage_pressure_rate"] = float(_bool_series(subset, "source_leakage_pressure_flag").mean())
        rows.append(metrics)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build_confidence_loop(
    scored: pd.DataFrame,
    leakage_sensitivity_available: bool = False,
    controls: pd.DataFrame | None = None,
) -> pd.DataFrame:
    vulnerabilities: list[dict[str, object]] = []
    laterality_unknown_rate = float(scored["laterality_relation"].astype(str).str.contains("unknown", case=False, na=True).mean())
    leakage_rate = float(_bool_series(scored, "source_leakage_pressure_flag").mean())
    selected_only_scope = scored["control_regime"].astype(str).nunique() == 1 if "control_regime" in scored.columns else True
    positive_rate = float(scored["phase16h_label"].mean()) if len(scored) else 0.0
    query_count = int(scored["query_image_id"].nunique()) if "query_image_id" in scored.columns else 0

    if selected_only_scope:
        vulnerabilities.append(
            {
                "vulnerability": "selected_only_pair_scope",
                "severity": "medium",
                "evidence": "Phase16H readiness table currently uses pairs where both images are inside the Phase16F selected set.",
                "mitigation": "Treat results as selected-set validation; before final claims, rebuild descriptor retrieval with selected queries against a documented gallery or add full-pool comparison.",
                "resolved_for_training_gate": False,
            }
        )
    if laterality_unknown_rate > 0.50:
        vulnerabilities.append(
            {
                "vulnerability": "laterality_mostly_unknown",
                "severity": "medium",
                "evidence": f"Laterality unknown-like rate is {laterality_unknown_rate:.3f}.",
                "mitigation": "Do not use laterality as a primary model feature yet; run laterality extraction/audit on Phase16F selected images or treat it as missingness diagnostic.",
                "resolved_for_training_gate": False,
            }
        )
    if leakage_rate > 0.10:
        if leakage_sensitivity_available:
            vulnerabilities.append(
                {
                    "vulnerability": "source_leakage_pressure_present",
                    "severity": "medium",
                    "evidence": f"Source leakage-pressure flag rate is {leakage_rate:.3f}; leakage sensitivity outputs were generated.",
                    "mitigation": "Use leakage_excluded as the default Phase16H training sensitivity and report leakage_only/all_pairs as robustness diagnostics.",
                    "resolved_for_training_gate": True,
                }
            )
        else:
            vulnerabilities.append(
                {
                    "vulnerability": "source_leakage_pressure_present",
                    "severity": "high",
                    "evidence": f"Source leakage-pressure flag rate is {leakage_rate:.3f}.",
                    "mitigation": "Report leakage-stratified metrics and exclude or downweight leakage-pressure pairs in any Phase16H training sensitivity run.",
                    "resolved_for_training_gate": False,
                }
            )
    if positive_rate <= 0.02 or positive_rate >= 0.95:
        vulnerabilities.append(
            {
                "vulnerability": "label_balance_extreme",
                "severity": "high",
                "evidence": f"Positive pair rate is {positive_rate:.3f}.",
                "mitigation": "Use grouped query splits, class-balanced calibration, and report AP/false-burden rather than accuracy.",
                "resolved_for_training_gate": False,
            }
        )
    if query_count < 50:
        vulnerabilities.append(
            {
                "vulnerability": "low_query_count",
                "severity": "high",
                "evidence": f"Query count is {query_count}.",
                "mitigation": "Increase query coverage before training; do not fit Phase16H review-router on this table.",
                "resolved_for_training_gate": False,
            }
        )
    if controls is not None and not controls.empty:
        k10 = controls[controls["k"].eq(10)]
        if k10.empty:
            k10 = controls[controls["k"].eq(int(controls["k"].min()))]
        descriptor_rows = k10[k10["policy_id"].eq("descriptor_only")]
        diagnostic_rows = k10[k10["policy_id"].eq("phase16h_diagnostic_no_training")]
        if not descriptor_rows.empty and not diagnostic_rows.empty:
            descriptor = descriptor_rows.iloc[0]
            diagnostic = diagnostic_rows.iloc[0]
            diagnostic_not_better = (
                float(diagnostic["mean_false_retained_per_query"])
                >= float(descriptor["mean_false_retained_per_query"])
                and float(diagnostic["hit_rate"]) <= float(descriptor["hit_rate"])
            )
            if diagnostic_not_better:
                vulnerabilities.append(
                    {
                        "vulnerability": "diagnostic_score_not_beating_descriptor",
                        "severity": "medium",
                        "evidence": (
                            "The no-training Phase16H diagnostic score does not beat descriptor-only "
                            "on the inspected top-k control snapshot."
                        ),
                        "mitigation": "Do not claim PF-ERI improves ranking yet; use Phase16H to test calibrated grouped-split models against descriptor-only and quality/random controls.",
                        "resolved_for_training_gate": False,
                    }
                )
    if not vulnerabilities:
        vulnerabilities.append(
            {
                "vulnerability": "no_unresolved_major_readiness_vulnerability_detected",
                "severity": "info",
                "evidence": "Automated readiness checks did not detect a major blocker.",
                "mitigation": "Proceed only with grouped split validation and keep Bobcat identity-claim boundary unchanged.",
                "resolved_for_training_gate": True,
            }
        )
    return pd.DataFrame(vulnerabilities)


def build_readiness_audit(scored: pd.DataFrame, controls: pd.DataFrame, confidence_loop: pd.DataFrame) -> dict[str, object]:
    required_policies = {
        "descriptor_only",
        "quality_only",
        "evidence_only",
        "conflict_penalized_descriptor",
        "phase16h_diagnostic_no_training",
        "random_same_size",
    }
    present_policies = set(controls["policy_id"].astype(str))
    blocker = (
        confidence_loop["severity"].isin(["high"])
        & ~confidence_loop["resolved_for_training_gate"].astype(bool)
    ).any()
    audit = {
        "status": "PASS" if len(scored) > 0 and required_policies.issubset(present_policies) else "FAIL",
        "training_gate_status": "REVIEW_REQUIRED" if blocker else "READY_FOR_DESIGN_NOT_TRAINING_CLAIM",
        "pair_rows": int(len(scored)),
        "query_count": int(scored["query_image_id"].nunique()),
        "positive_pair_rows": int(scored["phase16h_label"].sum()),
        "false_pair_rows": int((~scored["phase16h_label"].astype(bool)).sum()),
        "required_control_policies_present": sorted(present_policies),
        "unresolved_high_vulnerability_count": int(
            (
                confidence_loop["severity"].isin(["high"])
                & ~confidence_loop["resolved_for_training_gate"].astype(bool)
            ).sum()
        ),
        "claim_boundary": "Readiness controls only; no calibrated model training and no Bobcat identity claim.",
    }
    return audit


def write_report(audit: dict[str, object], controls: pd.DataFrame, confidence_loop: pd.DataFrame, output_dir: Path) -> None:
    top10 = controls[controls["k"].eq(10)].sort_values("mean_false_retained_per_query").head(8)
    lines = [
        "# Phase16H CzechLynx Readiness Controls",
        "",
        "This is a training-readiness and control-baseline report, not a calibrated model.",
        "",
        "## Audit",
        "",
        f"- Status: {audit['status']}",
        f"- Training gate: {audit['training_gate_status']}",
        f"- Pair rows: {audit['pair_rows']:,}",
        f"- Queries: {audit['query_count']:,}",
        f"- Positive pairs: {audit['positive_pair_rows']:,}",
        f"- False pairs: {audit['false_pair_rows']:,}",
        f"- Unresolved high vulnerabilities: {audit['unresolved_high_vulnerability_count']}",
        "",
        "## Top-k Control Snapshot At k=10",
        "",
        "| policy | hit rate | mean false/query | false rate retained |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in top10.to_dict(orient="records"):
        lines.append(
            f"| {row['policy_id']} | {row['hit_rate']:.4f} | "
            f"{row['mean_false_retained_per_query']:.4f} | {row['false_rate_among_retained']:.4f} |"
        )
    lines.extend(
        [
            "",
        "## Confidence Loop",
            "",
            "| vulnerability | severity | mitigation |",
            "| --- | --- | --- |",
        ]
    )
    for row in confidence_loop.to_dict(orient="records"):
        lines.append(f"| {row['vulnerability']} | {row['severity']} | {row['mitigation']} |")
    lines.extend(
        [
            "",
            "## Required Mitigation For Phase16H",
            "",
            "Any later model-training script must either exclude `source_leakage_pressure_flag == True` pairs by default or run an explicit leakage-stratified sensitivity analysis.",
            "Laterality must remain a missingness/audit field until Phase16F-selected images have stronger side labels.",
            "",
            "",
            "## Boundary",
            "",
            "Do not use this report to claim automatic identity assignment, final model training, or Bobcat identity accuracy.",
            "",
        ]
    )
    (output_dir / "phase16h_czechlynx_readiness_report.md").write_text("\n".join(lines))


def run_phase16h_readiness(
    input_csv: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    random_repeats: int = 50,
    random_seed: int = 20260628,
) -> dict[str, object]:
    pair_table = load_pair_table(input_csv)
    scored = compute_policy_scores(pair_table)
    controls = evaluate_topk_controls(scored, random_repeats=random_repeats, random_seed=random_seed)
    risk_coverage = evaluate_risk_coverage(scored)
    leakage_sensitivity = evaluate_leakage_sensitivity(scored)
    confidence_loop = build_confidence_loop(
        scored,
        leakage_sensitivity_available=not leakage_sensitivity.empty,
        controls=controls,
    )
    audit = build_readiness_audit(scored, controls, confidence_loop)

    output_dir.mkdir(parents=True, exist_ok=True)
    scored.to_csv(output_dir / "phase16h_czechlynx_scored_pair_table.csv", index=False)
    controls.to_csv(output_dir / "phase16h_czechlynx_control_topk_metrics.csv", index=False)
    risk_coverage.to_csv(output_dir / "phase16h_czechlynx_risk_coverage_controls.csv", index=False)
    leakage_sensitivity.to_csv(output_dir / "phase16h_czechlynx_leakage_sensitivity.csv", index=False)
    confidence_loop.to_csv(output_dir / "phase16h_czechlynx_confidence_loop.csv", index=False)
    (output_dir / "phase16h_czechlynx_readiness_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n"
    )
    write_report(audit, controls, confidence_loop, output_dir)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--random-repeats", type=int, default=50)
    parser.add_argument("--random-seed", type=int, default=20260628)
    args = parser.parse_args()

    audit = run_phase16h_readiness(
        input_csv=args.input,
        output_dir=args.output_dir,
        random_repeats=args.random_repeats,
        random_seed=args.random_seed,
    )
    print(f"Status: {audit['status']}")
    print(f"Training gate: {audit['training_gate_status']}")
    print(f"Pair rows: {audit['pair_rows']}")
    print(f"Unresolved high vulnerabilities: {audit['unresolved_high_vulnerability_count']}")
    print(f"Wrote {args.output_dir}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
