#!/usr/bin/env python3
"""Run Phase 8 Slice 3F downstream contamination sensitivity simulation."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from phase8_descriptor_disagreement_false_neighbor_confidence_control import build_mega_candidates
from phase8_pf_eri_deep_algorithm_v4_optimizer import (
    add_retrieval_confidence_features,
    assign_variant,
    policy_grid as v4_policy_grid,
)
from phase8_pf_eri_retrieval_control_v2_optimizer import (
    ANNOTATION_CSV,
    IDENTITY_CSV,
    MEGA_EMBEDDINGS_CSV,
    RESNET_EMBEDDINGS_CSV,
    align_inputs,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase8/downstream_sensitivity"
DOC_PATH = PROJECT_ROOT / "docs/phase8/phase8_slice3f_downstream_ecological_sensitivity_simulation_results.md"

INPUT_INVENTORY_CSV = OUTPUT_DIR / "phase8_slice3f_input_inventory.csv"
POLICY_METRICS_CSV = OUTPUT_DIR / "phase8_slice3f_policy_contamination_metrics.csv"
ASSUMPTION_SENSITIVITY_CSV = OUTPUT_DIR / "phase8_slice3f_reviewer_assumption_sensitivity.csv"
RANDOM_COMPARISON_CSV = OUTPUT_DIR / "phase8_slice3f_random_same_size_comparison.csv"
TRADEOFF_SUMMARY_CSV = OUTPUT_DIR / "phase8_slice3f_contamination_tradeoff_summary.csv"
FINAL_RECOMMENDATION_CSV = OUTPUT_DIR / "phase8_slice3f_final_recommendation.csv"

INPUTS_TO_INSPECT = [
    PROJECT_ROOT / "docs/phase8/phase8_post_3e_r_interpretation_and_claim_revision.md",
    PROJECT_ROOT / "docs/phase8/phase8_slice3f_downstream_ecological_sensitivity_simulation_plan.md",
    PROJECT_ROOT / "docs/phase8/phase8_slice3e_query_level_calibration_evaluation_results.md",
    PROJECT_ROOT / "docs/phase8/phase8_slice3e_reid_accuracy_evidence_selection_results.md",
    PROJECT_ROOT / "docs/phase8/phase8_slice3d_pf_eri_deep_algorithm_v4_results.md",
    PROJECT_ROOT / "docs/phase8/phase8_slice3c_utility_constrained_pf_eri_policy_selection_results.md",
    PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_query_calibration/phase8_slice3e_query_evaluation_policy_comparison.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_query_calibration/phase8_slice3e_query_final_recommendation.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/reid_accuracy_evidence_selection/phase8_slice3e_policy_comparison.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_retrieval_control_v2/phase8_pf_eri_retrieval_control_v2_recommended_assignments.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4/phase8_pf_eri_v4_recommended_assignments.csv",
    PROJECT_ROOT / "outputs/czechlynx/phase8/pf_eri_deep_algorithm_v4/phase8_pf_eri_v4_policy_grid.csv",
    PROJECT_ROOT / "data/interim/czechlynx/czechlynx_expanded_125x4_internal_with_ids.csv",
]

RANDOM_SEED = 20260615
RANDOM_REPEATS = 500
FALSE_ACCEPT_RATES = [0.05, 0.10, 0.20, 0.30, 0.50]
QUERY_COUNT = 500
TOP_K = 5

POLICY_LABELS = {
    "raw_megadescriptor_topk": "Raw MegaDescriptor top-k review baseline",
    "review_top1_only": "Raw MegaDescriptor top-1 only sensitivity",
    "candidate_f": "Candidate F review-control reference",
    "v4_0636": "v4_0636 operational refinement reference",
    "strict_pf_eri_reference": "Strict PF-ERI confidence-control reference",
    "random_same_size_candidate_f": "Random same-size control for Candidate F",
    "random_same_size_v4_0636": "Random same-size control for v4_0636",
    "random_same_size_strict_pf_eri_reference": "Random same-size control for strict PF-ERI reference",
}


def rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)) if path.is_absolute() else str(path)


def input_inventory(paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in paths:
        row: dict[str, object] = {
            "input_file": rel(path),
            "exists": "yes" if path.exists() else "no",
            "row_count": 0,
            "column_count": 0,
            "columns": "",
            "status": "missing",
        }
        if path.exists():
            if path.suffix.lower() == ".csv":
                df = pd.read_csv(path)
                row["row_count"] = int(len(df))
                row["column_count"] = int(len(df.columns))
                row["columns"] = ";".join(df.columns)
                row["status"] = "available_nonempty" if len(df) else "available_empty"
            else:
                text = path.read_text(encoding="utf-8")
                row["row_count"] = int(len(text.splitlines()))
                row["column_count"] = 0
                row["columns"] = ""
                row["status"] = "available_text"
        rows.append(row)
    return pd.DataFrame(rows)


def variant_policy(variant_id: str) -> dict[str, object]:
    for policy in v4_policy_grid():
        if policy["variant_id"] == variant_id:
            return policy
    raise ValueError(f"Missing v4 policy: {variant_id}")


def add_policy_columns(df: pd.DataFrame, policy_id: str, policy_family: str, policy_role: str) -> pd.DataFrame:
    out = df.copy()
    out["policy_id"] = policy_id
    out["policy_family"] = policy_family
    out["policy_label"] = POLICY_LABELS.get(policy_id, policy_id)
    out["policy_role"] = policy_role
    return out


def raw_topk_policy(candidates: pd.DataFrame, top_k: int = TOP_K) -> pd.DataFrame:
    df = candidates[candidates["rank"] <= top_k].copy()
    df["assignment"] = "review_candidate"
    df["detailed_assignment"] = "review_raw_topk"
    return add_policy_columns(df, "raw_megadescriptor_topk", "raw_descriptor_baseline", "raw_fixed_descriptor_review")


def top1_policy(candidates: pd.DataFrame) -> pd.DataFrame:
    df = candidates[candidates["rank"] == 1].copy()
    df["assignment"] = "review_candidate"
    df["detailed_assignment"] = "review_top1_only"
    return add_policy_columns(df, "review_top1_only", "raw_descriptor_sensitivity", "sensitivity_only")


def candidate_f_policy(candidates: pd.DataFrame) -> pd.DataFrame:
    df = assign_variant(candidates, variant_policy("v4_0001"))
    return add_policy_columns(df, "candidate_f", "pf_eri_review_control", "review_control_reference")


def v4_policy(candidates: pd.DataFrame, variant_id: str, policy_id: str, role: str) -> pd.DataFrame:
    df = assign_variant(candidates, variant_policy(variant_id))
    return add_policy_columns(df, policy_id, "pf_eri_v4_refinement", role)


def random_same_size_policy(target: pd.DataFrame, candidates: pd.DataFrame, policy_id: str, repeat: int, rng: np.random.Generator) -> pd.DataFrame:
    pool = candidates[candidates["rank"] <= TOP_K].copy()
    pool["assignment"] = "defer_candidate"
    pool["detailed_assignment"] = "random_defer"
    review_counts = target[target["assignment"] == "review_candidate"].groupby("query_idx").size()
    for query_idx, count in review_counts.items():
        idx = pool.index[pool["query_idx"] == query_idx].to_numpy()
        if len(idx) == 0 or count <= 0:
            continue
        chosen = rng.choice(idx, size=min(int(count), len(idx)), replace=False)
        pool.loc[chosen, "assignment"] = "review_candidate"
        pool.loc[chosen, "detailed_assignment"] = "random_review"
    out = add_policy_columns(pool, f"random_same_size_{policy_id}", "random_same_size_control", f"random_control_for_{policy_id}")
    out["target_policy_id"] = policy_id
    out["random_repeat"] = repeat
    return out


def finite_rate(value: float) -> float:
    if value is None or pd.isna(value):
        return math.nan
    return float(value)


def contamination_metrics(assigned: pd.DataFrame) -> dict[str, object]:
    review = assigned[assigned["assignment"] == "review_candidate"].copy()
    query_count = int(assigned["query_idx"].nunique())
    reviewed = int(len(review))
    false_reviewed = int((~review["same_identity"]).sum()) if reviewed else 0
    true_reviewed = int(review["same_identity"].sum()) if reviewed else 0
    true_total = int(assigned["same_identity"].sum())
    candidate_total = int(len(assigned))
    covered_queries = int(review["query_idx"].nunique())
    total_queries = max(query_count, QUERY_COUNT)
    false_burden = false_reviewed / total_queries if total_queries else math.nan
    unique_false_links = false_reviewed
    return {
        "policy_id": assigned["policy_id"].iloc[0],
        "policy_family": assigned["policy_family"].iloc[0],
        "policy_label": assigned["policy_label"].iloc[0],
        "policy_role": assigned["policy_role"].iloc[0],
        "query_count": total_queries,
        "candidate_pool_count": candidate_total,
        "reviewed_candidates": reviewed,
        "true_reviewed_candidates": true_reviewed,
        "false_reviewed_candidates": false_reviewed,
        "false_candidate_burden": false_burden,
        "review_workload": reviewed / total_queries if total_queries else math.nan,
        "candidate_retention": reviewed / candidate_total if candidate_total else math.nan,
        "query_coverage": covered_queries / total_queries if total_queries else math.nan,
        "positive_retention": true_reviewed / true_total if true_total else math.nan,
        "reviewed_candidate_precision": true_reviewed / reviewed if reviewed else math.nan,
        "false_candidate_rate_among_reviewed": false_reviewed / reviewed if reviewed else math.nan,
        "simulated_false_merge_proxy": unique_false_links,
        "false_split_proxy": max(true_total - true_reviewed, 0),
        "contamination_per_100_reviewed_candidates": (false_reviewed / reviewed * 100.0) if reviewed else math.nan,
    }


def add_raw_comparisons(metrics: pd.DataFrame) -> pd.DataFrame:
    out = metrics.copy()
    raw = out[out["policy_id"] == "raw_megadescriptor_topk"].iloc[0]
    for col in ["false_candidate_burden", "reviewed_candidates", "review_workload"]:
        out[f"{col}_reduction_vs_raw"] = float(raw[col]) - pd.to_numeric(out[col], errors="coerce")
    raw_removed = float(raw["reviewed_candidates"]) - pd.to_numeric(out["reviewed_candidates"], errors="coerce")
    risk_reduction = float(raw["false_candidate_burden"]) - pd.to_numeric(out["false_candidate_burden"], errors="coerce")
    out["risk_reduction_per_evidence_removed"] = risk_reduction / raw_removed.where(raw_removed > 0, np.nan)
    return out


def reviewer_sensitivity(policy_metrics: pd.DataFrame, false_accept_rates: list[float]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in policy_metrics.iterrows():
        for far in false_accept_rates:
            expected_false_accepts = float(row["false_reviewed_candidates"]) * far
            reviewed = float(row["reviewed_candidates"])
            rows.append(
                {
                    "policy_id": row["policy_id"],
                    "policy_family": row["policy_family"],
                    "policy_role": row["policy_role"],
                    "false_accept_rate": far,
                    "reviewed_candidates": int(row["reviewed_candidates"]),
                    "false_reviewed_candidates": int(row["false_reviewed_candidates"]),
                    "expected_false_accepts": expected_false_accepts,
                    "simulated_identity_record_contamination_rate": expected_false_accepts / reviewed if reviewed else math.nan,
                    "expected_false_merge_proxy": expected_false_accepts,
                    "expected_contamination_per_100_reviewed_candidates": expected_false_accepts / reviewed * 100.0 if reviewed else math.nan,
                    "query_coverage": row["query_coverage"],
                    "positive_retention": row["positive_retention"],
                    "note": "sensitivity_assumption_not_measured_human_behavior",
                }
            )
    return pd.DataFrame(rows)


def summarize_random(random_metrics: pd.DataFrame, policy_metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    metrics = [
        "false_candidate_burden",
        "reviewed_candidates",
        "false_reviewed_candidates",
        "simulated_false_merge_proxy",
        "contamination_per_100_reviewed_candidates",
        "query_coverage",
        "positive_retention",
        "candidate_retention",
        "review_workload",
    ]
    for target_policy_id, group in random_metrics.groupby("target_policy_id"):
        actual = policy_metrics[policy_metrics["policy_id"] == target_policy_id]
        if actual.empty:
            continue
        actual_row = actual.iloc[0]
        for metric in metrics:
            vals = pd.to_numeric(group[metric], errors="coerce").dropna()
            policy_value = finite_rate(actual_row[metric])
            if vals.empty or pd.isna(policy_value):
                continue
            rows.append(
                {
                    "target_policy_id": target_policy_id,
                    "metric": metric,
                    "random_repeat_count": int(group["random_repeat"].nunique()),
                    "random_mean": float(vals.mean()),
                    "random_std": float(vals.std(ddof=1)),
                    "random_p05": float(vals.quantile(0.05)),
                    "random_p50": float(vals.quantile(0.50)),
                    "random_p95": float(vals.quantile(0.95)),
                    "policy_value": policy_value,
                    "policy_minus_random_mean": float(policy_value - vals.mean()),
                    "policy_percentile_vs_random": float((vals <= policy_value).mean()),
                    "better_than_random_mean": "yes" if (
                        policy_value < vals.mean()
                        if metric in {
                            "false_candidate_burden",
                            "false_reviewed_candidates",
                            "simulated_false_merge_proxy",
                            "contamination_per_100_reviewed_candidates",
                            "review_workload",
                        }
                        else policy_value > vals.mean()
                    ) else "no",
                }
            )
    return pd.DataFrame(rows)


def contamination_decisions(policy_metrics: pd.DataFrame, random_summary: pd.DataFrame) -> pd.DataFrame:
    raw = policy_metrics[policy_metrics["policy_id"] == "raw_megadescriptor_topk"].iloc[0]
    rows: list[dict[str, object]] = []
    for policy_id in ["candidate_f", "v4_0636", "strict_pf_eri_reference"]:
        pol = policy_metrics[policy_metrics["policy_id"] == policy_id]
        if pol.empty:
            continue
        row = pol.iloc[0]
        burden_delta = float(raw["false_candidate_burden"] - row["false_candidate_burden"])
        rand = random_summary[(random_summary["target_policy_id"] == policy_id) & (random_summary["metric"] == "false_candidate_burden")]
        beats_random = "not_available"
        if not rand.empty:
            beats_random = str(rand.iloc[0]["better_than_random_mean"])
        rows.append(
            {
                "policy_id": policy_id,
                "false_candidate_burden": row["false_candidate_burden"],
                "false_candidate_burden_reduction_vs_raw": burden_delta,
                "beats_random_same_size_on_false_burden": beats_random,
                "query_coverage": row["query_coverage"],
                "positive_retention": row["positive_retention"],
                "interpretation": (
                    "lower_contamination_pressure_with_retention_tradeoff"
                    if burden_delta > 0 and beats_random == "yes"
                    else "not_stronger_than_random_same_size_on_primary_burden"
                ),
            }
        )
    return pd.DataFrame(rows)


def final_recommendation(tradeoff: pd.DataFrame) -> pd.DataFrame:
    candidate_ok = (
        not tradeoff[(tradeoff["policy_id"] == "candidate_f") & (tradeoff["beats_random_same_size_on_false_burden"] == "yes")].empty
    )
    v4_ok = not tradeoff[(tradeoff["policy_id"] == "v4_0636") & (tradeoff["beats_random_same_size_on_false_burden"] == "yes")].empty
    strict_ok = not tradeoff[(tradeoff["policy_id"] == "strict_pf_eri_reference") & (tradeoff["beats_random_same_size_on_false_burden"] == "yes")].empty
    support = "yes" if (candidate_ok or v4_ok or strict_ok) else "no"
    next_step = "manuscript_integration_with_conservative_claims" if support == "yes" else "retain_evidence_control_framing_without_downstream_value_claim"
    return pd.DataFrame(
        [
            {
                "decision_item": "slice3f_downstream_workflow_value_supported",
                "decision": support,
                "rationale": "At least one PF-ERI policy reduced simulated false-candidate burden versus raw review and random same-size controls."
                if support == "yes"
                else "No PF-ERI policy reduced simulated false-candidate burden beyond random same-size controls.",
            },
            {
                "decision_item": "candidate_f_reduced_simulated_contamination_pressure",
                "decision": "yes" if candidate_ok else "no",
                "rationale": "Candidate F is the coverage-preserving review-control reference; interpret beside positive retention.",
            },
            {
                "decision_item": "v4_0636_reduced_simulated_contamination_pressure",
                "decision": "yes" if v4_ok else "no",
                "rationale": "v4_0636 is the operational refinement reference; lower burden must be interpreted with lower retention.",
            },
            {
                "decision_item": "strict_pf_eri_reference_reduced_simulated_contamination_pressure",
                "decision": "yes" if strict_ok else "no",
                "rationale": "Strict PF-ERI is a confidence-control reference only, not the main operating policy.",
            },
            {
                "decision_item": "recommended_next_step",
                "decision": next_step,
                "rationale": "Slice 3F is a sensitivity simulation, not ecological estimation or field deployment validation.",
            },
        ]
    )


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "No rows available."
    safe = df.copy()
    safe = safe.where(pd.notna(safe), "")
    cols = list(safe.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in safe.iterrows():
        vals = [str(row[col]).replace("|", "\\|") for col in cols]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_results_doc(
    inventory: pd.DataFrame,
    policy_metrics: pd.DataFrame,
    assumption: pd.DataFrame,
    random_summary: pd.DataFrame,
    tradeoff: pd.DataFrame,
    final: pd.DataFrame,
    random_repeats: int,
) -> None:
    selected_metrics = policy_metrics[
        [
            "policy_id",
            "false_candidate_burden",
            "reviewed_candidates",
            "false_reviewed_candidates",
            "query_coverage",
            "positive_retention",
            "candidate_retention",
            "risk_reduction_per_evidence_removed",
        ]
    ].copy()
    selected_metrics = selected_metrics[selected_metrics["policy_id"].isin([
        "raw_megadescriptor_topk",
        "review_top1_only",
        "candidate_f",
        "v4_0636",
        "strict_pf_eri_reference",
    ])]
    random_false = random_summary[random_summary["metric"] == "false_candidate_burden"][
        [
            "target_policy_id",
            "random_repeat_count",
            "random_mean",
            "random_p05",
            "random_p50",
            "random_p95",
            "policy_value",
            "policy_minus_random_mean",
            "better_than_random_mean",
        ]
    ].copy()
    candidate_f = policy_metrics[policy_metrics["policy_id"] == "candidate_f"]
    v4 = policy_metrics[policy_metrics["policy_id"] == "v4_0636"]
    strict = policy_metrics[policy_metrics["policy_id"] == "strict_pf_eri_reference"]
    success = final.loc[final["decision_item"] == "slice3f_downstream_workflow_value_supported", "decision"].iloc[0]
    text = f"""# Phase 8 Slice 3F Downstream Ecological Sensitivity Simulation Results

## 1. Purpose

Slice 3F implements a conservative CzechLynx downstream identity-record contamination sensitivity simulation. It tests whether PF-ERI's supported false-candidate burden reduction could reduce simulated downstream contamination pressure.

## 2. Post-3E-R Rationale

Slice 3E-R showed that held-out fixed-descriptor Re-ID accuracy improvement was not robust. The supported value entering this slice is false-candidate review-burden reduction, not improved identity discrimination.

## 3. Sensitivity Simulation Boundary

This is a sensitivity simulation, not ecological estimation. PF-ERI is not a Re-ID model. It does not estimate abundance, occupancy, survival, movement, or population size. It does not claim field deployment readiness and does not identify true individual animals.

## 4. Input Inventory

Inspected inputs: `{len(inventory)}`.

Missing inputs: `{int((inventory['exists'] == 'no').sum())}`.

## 5. Policies Compared

- `raw_megadescriptor_topk`: raw fixed-descriptor review baseline.
- `review_top1_only`: raw top-1 sensitivity baseline.
- `candidate_f`: review-control reference.
- `v4_0636`: operational refinement reference.
- `strict_pf_eri_reference`: strict confidence-control reference.
- random same-size controls for PF-ERI policies.

## 6. Candidate Truth Mapping

Candidate truth was mapped internally using CzechLynx working identities:

```text
true candidate = query and candidate share the same working identity
false candidate = query and candidate have different working identities
```

Identity labels were used only for validation/simulation truth. No raw paths, original IDs, working IDs, locations, trap IDs, GPS fields, raw dates, or per-identity histories are exported.

## 7. Reviewer False-Acceptance Assumption Grid

False-acceptance rates:

```text
{', '.join(f'{x:.2f}' for x in FALSE_ACCEPT_RATES)}
```

These are not measured human behavior. They are sensitivity assumptions.

## 8. Random Same-Size Control Design

Random same-size controls were generated per PF-ERI policy by matching each policy's reviewed-candidate count per query. Random repeats: `{random_repeats}`.

## 9. Primary Metrics and Formulas

```text
false_candidate_burden = false_reviewed_candidates / covered query universe
expected_false_accepts = false_reviewed_candidates * false_accept_rate
simulated_identity_record_contamination_rate = expected_false_accepts / reviewed_candidates
risk_reduction_per_evidence_removed =
  (false_burden_raw - false_burden_policy) /
  max(1, raw_reviewed_candidates - policy_reviewed_candidates)
```

False merge proxy is the expected accepted false candidate links connecting different working identities. It is a proxy, not a field ecological rate.

## 10. Main Contamination Results

{markdown_table(selected_metrics.round(4))}

## 11. Random Baseline Comparison

{markdown_table(random_false.round(4))}

## 12. Candidate F Interpretation

{markdown_table(candidate_f[['policy_id', 'false_candidate_burden', 'reviewed_candidates', 'query_coverage', 'positive_retention', 'candidate_retention']].round(4))}

Candidate F remains the review-control reference because it preserves stronger coverage and positive retention. It should not be described as a Re-ID accuracy-improvement policy.

## 13. v4_0636 Interpretation

{markdown_table(v4[['policy_id', 'false_candidate_burden', 'reviewed_candidates', 'query_coverage', 'positive_retention', 'candidate_retention']].round(4))}

`v4_0636` is the operational refinement reference. Lower contamination pressure must be interpreted with its lower positive-retention and coverage tradeoff.

## 14. Strict PF-ERI Reference Interpretation

{markdown_table(strict[['policy_id', 'false_candidate_burden', 'reviewed_candidates', 'query_coverage', 'positive_retention', 'candidate_retention']].round(4))}

The strict PF-ERI reference is a confidence-control sensitivity layer, not the main operating policy.

## 15. Utility Policy Interpretation

Utility policies were not promoted as final policies in this slice. They remain sensitivity layers only, not identity scores or safety scores.

## 16. Whether PF-ERI Reduces Simulated Downstream Contamination Pressure

Decision:

```text
{success}
```

{markdown_table(tradeoff.round(4))}

## 17. Coverage and Positive-Retention Tradeoffs

Coverage and positive retention are reported beside all contamination metrics. Policies with lower contamination pressure but low positive retention should be interpreted as confidence-control or workload-control references rather than replacements for review-control policy.

## 18. Limitations

- CzechLynx-only sensitivity simulation.
- Reviewer false-acceptance rates are assumptions, not measured human behavior.
- No site-use, movement, occupancy, abundance, survival, or population metrics are estimated.
- Random same-size controls reduce easier-workload artifacts but do not provide external validation.
- Identity labels are internal validation labels only.

## 19. Claims Supported

If the decision above is `yes`, Slice 3F supports this bounded claim:

```text
PF-ERI false-candidate burden reduction can reduce simulated downstream identity-record contamination pressure in CzechLynx under conservative sensitivity assumptions.
```

## 20. Claims Forbidden

- Do not claim PF-ERI estimates population size.
- Do not claim PF-ERI improves occupancy, abundance, survival, movement, or field ecological estimates.
- Do not claim PF-ERI identifies true individual animals.
- Do not claim PF-ERI is ready for field deployment.
- Do not claim PF-ERI is validated across felids.
- Do not claim PF-ERI is validated for Mainland Clouded Leopard or Marbled Cat.
- Do not claim PF-ERI is a new Re-ID model.
- Do not claim PF-ERI robustly improves fixed-descriptor Re-ID accuracy.

## 21. Recommended Next Step

{final.loc[final['decision_item'] == 'recommended_next_step', 'decision'].iloc[0]}

## 22. Confirmation

No training, no external data download, no frozen-data edit, no staging, and no commit were performed.
"""
    DOC_PATH.write_text(text, encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    inventory = input_inventory(INPUTS_TO_INSPECT)
    inventory.to_csv(INPUT_INVENTORY_CSV, index=False)

    metadata, similarities = align_inputs(args)
    candidates = build_mega_candidates(metadata, similarities, max_k=20)
    candidates = add_retrieval_confidence_features(candidates, similarities)

    policies = [
        raw_topk_policy(candidates),
        top1_policy(candidates),
        candidate_f_policy(candidates),
        v4_policy(candidates, "v4_0636", "v4_0636", "operational_refinement_reference"),
        v4_policy(candidates, "v4_0018", "strict_pf_eri_reference", "strict_confidence_control_reference"),
    ]
    policy_metrics = pd.DataFrame([contamination_metrics(policy) for policy in policies])
    policy_metrics = add_raw_comparisons(policy_metrics)

    rng = np.random.default_rng(args.random_seed)
    random_rows: list[dict[str, object]] = []
    for policy in policies:
        pid = policy["policy_id"].iloc[0]
        if pid not in {"candidate_f", "v4_0636", "strict_pf_eri_reference"}:
            continue
        for repeat in range(1, args.random_repeats + 1):
            random_policy = random_same_size_policy(policy, candidates, pid, repeat, rng)
            metrics = contamination_metrics(random_policy)
            metrics["target_policy_id"] = pid
            metrics["random_repeat"] = repeat
            random_rows.append(metrics)
    random_metrics = pd.DataFrame(random_rows)
    random_summary = summarize_random(random_metrics, policy_metrics)
    assumption = reviewer_sensitivity(policy_metrics, FALSE_ACCEPT_RATES)
    tradeoff = contamination_decisions(policy_metrics, random_summary)
    final = final_recommendation(tradeoff)

    policy_metrics.to_csv(POLICY_METRICS_CSV, index=False)
    assumption.to_csv(ASSUMPTION_SENSITIVITY_CSV, index=False)
    random_summary.to_csv(RANDOM_COMPARISON_CSV, index=False)
    tradeoff.to_csv(TRADEOFF_SUMMARY_CSV, index=False)
    final.to_csv(FINAL_RECOMMENDATION_CSV, index=False)
    write_results_doc(inventory, policy_metrics, assumption, random_summary, tradeoff, final, args.random_repeats)

    print("Phase 8 Slice 3F downstream sensitivity simulation complete")
    print(f"output_dir: {OUTPUT_DIR}")
    print(f"random_repeats: {args.random_repeats}")
    print(f"decision: {final.loc[final['decision_item'] == 'slice3f_downstream_workflow_value_supported', 'decision'].iloc[0]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-csv", type=Path, default=IDENTITY_CSV)
    parser.add_argument("--annotation-csv", type=Path, default=ANNOTATION_CSV)
    parser.add_argument("--megadescriptor-embeddings-csv", type=Path, default=MEGA_EMBEDDINGS_CSV)
    parser.add_argument("--resnet50-embeddings-csv", type=Path, default=RESNET_EMBEDDINGS_CSV)
    parser.add_argument("--random-repeats", type=int, default=RANDOM_REPEATS)
    parser.add_argument("--random-seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
