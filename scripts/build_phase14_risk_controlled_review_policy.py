#!/usr/bin/env python3
"""Evaluate Phase 14 risk-controlled review policies.

This is a candidate-pair policy evaluator, not a full gallery retrieval
benchmark. The Phase 14 pair table is a controlled sample, so CzechLynx known-ID
pairs can validate positive retention and false-candidate burden within the
sampled high-descriptor candidate set. Bobcat remains identity-unknown and is
reported only as transfer stress/review-burden distribution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFLICT_TABLE = (
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_conflict/phase14_2x2_descriptor_evidence_conflict_table.csv"
)
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_risk_controlled_review_policy"
POLICY_TABLE = OUT_DIR / "phase14_czechlynx_policy_evaluation.csv"
RANDOM_CONTROL = OUT_DIR / "phase14_czechlynx_random_matched_policy_control.csv"
RISK_COVERAGE = OUT_DIR / "phase14_czechlynx_policy_risk_coverage_curve.csv"
BOBCAT_TRANSFER = OUT_DIR / "phase14_bobcat_policy_transfer_stress.csv"
PARETO_TABLE = OUT_DIR / "phase14_czechlynx_policy_pareto_diagnostics.csv"
REPORT_MD = OUT_DIR / "phase14_risk_controlled_review_policy_report.md"
AUDIT_JSON = OUT_DIR / "phase14_risk_controlled_review_policy_audit.json"

RANDOM_SEED = 20260622
RANDOM_REPEATS = 500
HIGH_DESCRIPTOR_PERCENTILE = 0.90
PF_ERI_THRESHOLDS = [0.20, 0.30, 0.40, 0.50, 0.55, 0.60, 0.70]
QUALITY_THRESHOLDS = [0.20, 0.30, 0.40, 0.50, 0.55, 0.60, 0.70]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def fmt(value: Any, digits: int = 3) -> str:
    try:
        value = float(value)
    except Exception:
        return "NA"
    if not np.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"


def summarize_czech_policy(
    block: str,
    policy_id: str,
    policy_family: str,
    frame: pd.DataFrame,
    eligible_mask: pd.Series,
    retain_mask: pd.Series,
    threshold: float | str,
    note: str,
) -> dict[str, Any]:
    eligible = frame[eligible_mask].copy()
    retained = frame[eligible_mask & retain_mask].copy()
    deferred = frame[eligible_mask & ~retain_mask].copy()

    base_positive = int(eligible["same_identity"].eq("yes").sum())
    base_false = int(eligible["same_identity"].eq("no").sum())
    retained_positive = int(retained["same_identity"].eq("yes").sum())
    retained_false = int(retained["same_identity"].eq("no").sum())
    deferred_positive = int(deferred["same_identity"].eq("yes").sum())
    deferred_false = int(deferred["same_identity"].eq("no").sum())
    retained_total = int(len(retained))

    return {
        "pair_block": block,
        "policy_id": policy_id,
        "policy_family": policy_family,
        "threshold": threshold,
        "eligible_high_descriptor_pairs": int(len(eligible)),
        "eligible_positive_count": base_positive,
        "eligible_false_candidate_count": base_false,
        "retained_pairs": retained_total,
        "retained_pair_coverage": float(retained_total / max(len(eligible), 1)),
        "retained_positive_count": retained_positive,
        "retained_false_candidate_count": retained_false,
        "positive_retention": float(retained_positive / max(base_positive, 1)),
        "false_candidate_retention": float(retained_false / max(base_false, 1)),
        "false_candidate_rate_among_retained": float(retained_false / max(retained_total, 1)),
        "deferred_pairs": int(len(deferred)),
        "deferred_positive_count": deferred_positive,
        "deferred_false_candidate_count": deferred_false,
        "deferred_positive_rate": float(deferred_positive / max(len(deferred), 1)),
        "mean_retained_pair_comparability": float(numeric(retained, "pair_comparability_score").mean()) if retained_total else float("nan"),
        "mean_retained_descriptor_similarity": float(numeric(retained, "descriptor_similarity").mean()) if retained_total else float("nan"),
        "mean_retained_conflict_score": float(numeric(retained, "descriptor_evidence_conflict_score").mean()) if retained_total else float("nan"),
        "note": note,
    }


def build_czech_policies(conflict: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    czech = conflict[conflict["species_axis"].eq("czechlynx") & conflict["same_identity"].isin(["yes", "no"])].copy()
    czech["high_descriptor_candidate"] = numeric(czech, "descriptor_similarity_percentile_block") >= HIGH_DESCRIPTOR_PERCENTILE
    rows: list[dict[str, Any]] = []
    random_rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(RANDOM_SEED)

    for block, frame in czech.groupby("pair_block", sort=True):
        frame = frame.copy()
        eligible = frame["high_descriptor_candidate"]
        all_high = eligible.copy()
        rows.append(
            summarize_czech_policy(
                block,
                "raw_descriptor_top10",
                "descriptor_only",
                frame,
                eligible,
                all_high,
                "top10pct",
                "Retain every pair in the block-level top 10% descriptor similarity set.",
            )
        )

        for threshold in PF_ERI_THRESHOLDS:
            retain = eligible & (numeric(frame, "pair_comparability_score") >= threshold)
            policy_id = f"pf_eri_pair_comparability_ge_{threshold:.2f}"
            rows.append(
                summarize_czech_policy(
                    block,
                    policy_id,
                    "pf_eri_pair_comparability_gate",
                    frame,
                    eligible,
                    retain,
                    threshold,
                    "Retain high-descriptor pairs only when pair comparability meets threshold; otherwise defer/review.",
                )
            )

            # Matched random control: same retained count inside high-descriptor candidate set.
            eligible_indices = np.flatnonzero(eligible.to_numpy())
            target_n = int(retain.sum())
            random_metrics = []
            if len(eligible_indices) and target_n > 0:
                for repeat in range(RANDOM_REPEATS):
                    picked = rng.choice(eligible_indices, size=target_n, replace=False)
                    random_mask = pd.Series(False, index=frame.index)
                    random_mask.iloc[picked] = True
                    random_metrics.append(
                        summarize_czech_policy(
                            block,
                            f"random_matched_to_pf_eri_ge_{threshold:.2f}",
                            "random_matched_same_coverage",
                            frame,
                            eligible,
                            random_mask,
                            threshold,
                            f"Repeat {repeat + 1}; randomly retain same count as PF-ERI threshold policy.",
                        )
                    )
            if random_metrics:
                rand = pd.DataFrame(random_metrics)
                random_rows.append(
                    {
                        "pair_block": block,
                        "matched_policy": policy_id,
                        "threshold": threshold,
                        "random_repeats": RANDOM_REPEATS,
                        "target_retained_pairs": target_n,
                        "random_positive_retention_mean": float(rand["positive_retention"].mean()),
                        "random_positive_retention_ci95_low": float(rand["positive_retention"].quantile(0.025)),
                        "random_positive_retention_ci95_high": float(rand["positive_retention"].quantile(0.975)),
                        "random_false_candidate_retention_mean": float(rand["false_candidate_retention"].mean()),
                        "random_false_candidate_retention_ci95_low": float(rand["false_candidate_retention"].quantile(0.025)),
                        "random_false_candidate_retention_ci95_high": float(rand["false_candidate_retention"].quantile(0.975)),
                        "random_false_candidate_rate_retained_mean": float(rand["false_candidate_rate_among_retained"].mean()),
                        "random_false_candidate_rate_retained_ci95_low": float(rand["false_candidate_rate_among_retained"].quantile(0.025)),
                        "random_false_candidate_rate_retained_ci95_high": float(rand["false_candidate_rate_among_retained"].quantile(0.975)),
                    }
                )

        for threshold in QUALITY_THRESHOLDS:
            retain = eligible & (numeric(frame, "weakest_image_utility_score") >= threshold)
            rows.append(
                summarize_czech_policy(
                    block,
                    f"quality_weakest_image_ge_{threshold:.2f}",
                    "quality_only_gate",
                    frame,
                    eligible,
                    retain,
                    threshold,
                    "Retain high-descriptor pairs using weakest-image utility only; pair comparability is not used.",
                )
            )

        conflict_aware = eligible & (numeric(frame, "pair_comparability_score") >= 0.40) & (
            numeric(frame, "descriptor_evidence_conflict_score") < 0.75
        )
        rows.append(
            summarize_czech_policy(
                block,
                "pf_eri_conflict_aware_review_gate",
                "pf_eri_conflict_aware",
                frame,
                eligible,
                conflict_aware,
                "pair_ge_0.40_conflict_lt_0.75",
                "Retain high-descriptor pairs if pair comparability is reviewable and conflict is not high.",
            )
        )

    policy = pd.DataFrame(rows)
    random_control = pd.DataFrame(random_rows)
    risk_coverage = policy[policy["policy_family"].isin(["descriptor_only", "pf_eri_pair_comparability_gate", "quality_only_gate", "pf_eri_conflict_aware"])].copy()
    return policy, random_control, risk_coverage


def build_bobcat_transfer(conflict: pd.DataFrame) -> pd.DataFrame:
    bobcat = conflict[conflict["species_axis"].eq("bobcat")].copy()
    bobcat["high_descriptor_candidate"] = numeric(bobcat, "descriptor_similarity_percentile_block") >= HIGH_DESCRIPTOR_PERCENTILE
    rows: list[dict[str, Any]] = []
    for block, frame in bobcat.groupby("pair_block", sort=True):
        eligible = frame[frame["high_descriptor_candidate"]].copy()
        for threshold in PF_ERI_THRESHOLDS:
            retained = eligible[numeric(eligible, "pair_comparability_score") >= threshold]
            deferred = eligible[numeric(eligible, "pair_comparability_score") < threshold]
            high_conflict = eligible["descriptor_conflict_band"].eq("high_conflict")
            rows.append(
                {
                    "pair_block": block,
                    "policy_id": f"pf_eri_pair_comparability_ge_{threshold:.2f}",
                    "threshold": threshold,
                    "identity_validation_scope": "identity_unknown_bobcat_transfer_stress_only",
                    "eligible_high_descriptor_pairs": int(len(eligible)),
                    "retained_pairs": int(len(retained)),
                    "retained_pair_coverage": float(len(retained) / max(len(eligible), 1)),
                    "deferred_pairs": int(len(deferred)),
                    "mean_eligible_pair_comparability": float(numeric(eligible, "pair_comparability_score").mean()) if len(eligible) else float("nan"),
                    "mean_retained_pair_comparability": float(numeric(retained, "pair_comparability_score").mean()) if len(retained) else float("nan"),
                    "mean_eligible_conflict_score": float(numeric(eligible, "descriptor_evidence_conflict_score").mean()) if len(eligible) else float("nan"),
                    "high_conflict_count": int(high_conflict.sum()),
                    "high_conflict_rate": float(high_conflict.mean()) if len(eligible) else float("nan"),
                    "claim_boundary": "No bobcat false-match accuracy without verified individual labels.",
                }
            )
    return pd.DataFrame(rows)


def build_pareto_diagnostics(policy: pd.DataFrame) -> pd.DataFrame:
    considered = policy[
        policy["policy_family"].isin(
            ["descriptor_only", "pf_eri_pair_comparability_gate", "quality_only_gate", "pf_eri_conflict_aware"]
        )
    ].copy()
    rows: list[dict[str, Any]] = []
    for block, frame in considered.groupby("pair_block", sort=True):
        for _, candidate in frame.iterrows():
            dominators = []
            for _, other in frame.iterrows():
                if other["policy_id"] == candidate["policy_id"]:
                    continue
                no_worse = (
                    other["positive_retention"] >= candidate["positive_retention"]
                    and other["false_candidate_retention"] <= candidate["false_candidate_retention"]
                )
                strictly_better = (
                    other["positive_retention"] > candidate["positive_retention"]
                    or other["false_candidate_retention"] < candidate["false_candidate_retention"]
                )
                if no_worse and strictly_better:
                    dominators.append(str(other["policy_id"]))
            rows.append(
                {
                    "pair_block": block,
                    "policy_id": candidate["policy_id"],
                    "policy_family": candidate["policy_family"],
                    "retained_pair_coverage": float(candidate["retained_pair_coverage"]),
                    "positive_retention": float(candidate["positive_retention"]),
                    "false_candidate_retention": float(candidate["false_candidate_retention"]),
                    "false_candidate_rate_among_retained": float(candidate["false_candidate_rate_among_retained"]),
                    "pareto_dominated": bool(dominators),
                    "example_dominator_policy_ids": ";".join(dominators[:5]),
                }
            )
    return pd.DataFrame(rows)


def write_report(
    policy: pd.DataFrame,
    random_control: pd.DataFrame,
    bobcat_transfer: pd.DataFrame,
    pareto: pd.DataFrame,
) -> None:
    def row(block: str, policy_id: str) -> pd.Series:
        return policy[policy["pair_block"].eq(block) & policy["policy_id"].eq(policy_id)].iloc[0]

    high_raw = row("czechlynx_high_confidence_within", "raw_descriptor_top10")
    high_pf = row("czechlynx_high_confidence_within", "pf_eri_pair_comparability_ge_0.70")
    cross_raw = row("czechlynx_high_low_cross", "raw_descriptor_top10")
    cross_pf = row("czechlynx_high_low_cross", "pf_eri_pair_comparability_ge_0.40")
    low_raw = row("czechlynx_low_evidence_stress_within", "raw_descriptor_top10")
    low_pf = row("czechlynx_low_evidence_stress_within", "pf_eri_pair_comparability_ge_0.30")

    def random_row(block: str, matched_policy: str) -> pd.Series | None:
        subset = random_control[random_control["pair_block"].eq(block) & random_control["matched_policy"].eq(matched_policy)]
        if subset.empty:
            return None
        return subset.iloc[0]

    cross_rand = random_row("czechlynx_high_low_cross", "pf_eri_pair_comparability_ge_0.40")
    low_rand = random_row("czechlynx_low_evidence_stress_within", "pf_eri_pair_comparability_ge_0.30")

    bobcat_low = bobcat_transfer[
        bobcat_transfer["pair_block"].eq("bobcat_low_evidence_stress_within")
        & bobcat_transfer["policy_id"].eq("pf_eri_pair_comparability_ge_0.30")
    ].iloc[0]
    low_quality = row("czechlynx_low_evidence_stress_within", "quality_weakest_image_ge_0.40")
    cross_quality = row("czechlynx_high_low_cross", "quality_weakest_image_ge_0.40")
    low_pf_pareto = pareto[
        pareto["pair_block"].eq("czechlynx_low_evidence_stress_within")
        & pareto["policy_id"].eq("pf_eri_pair_comparability_ge_0.30")
    ].iloc[0]
    cross_pf_pareto = pareto[
        pareto["pair_block"].eq("czechlynx_high_low_cross")
        & pareto["policy_id"].eq("pf_eri_pair_comparability_ge_0.40")
    ].iloc[0]

    cross_random_text = (
        f"Matched random false-retention mean = {fmt(cross_rand['random_false_candidate_retention_mean'])}, "
        f"95% interval [{fmt(cross_rand['random_false_candidate_retention_ci95_low'])}, {fmt(cross_rand['random_false_candidate_retention_ci95_high'])}]."
        if cross_rand is not None
        else "Matched random control was unavailable for this threshold."
    )
    low_random_text = (
        f"Matched random false-retention mean = {fmt(low_rand['random_false_candidate_retention_mean'])}, "
        f"95% interval [{fmt(low_rand['random_false_candidate_retention_ci95_low'])}, {fmt(low_rand['random_false_candidate_retention_ci95_high'])}]."
        if low_rand is not None
        else "Matched random control was unavailable for this threshold."
    )

    text = f"""# Phase 14 Risk-Controlled Review Policy

## Scope

This analysis evaluates candidate-pair review policies on the Phase 14 descriptor-conflict table. It is not a full gallery retrieval benchmark. CzechLynx known-ID pairs validate positive retention and false-candidate burden in sampled high-descriptor candidate pairs. Bobcat remains identity-unknown and is reported only as transfer stress.

## Policy Setup

The eligible candidate pool is the block-level top 10% descriptor-similarity pairs. Policies then decide whether to retain/review a candidate or defer it based on PF-ERI pair comparability or quality-only controls.

Compared policies:

- `raw_descriptor_top10`: retain all top-descriptor candidates.
- `pf_eri_pair_comparability_ge_*`: retain top-descriptor candidates only if pair comparability passes a threshold.
- `quality_weakest_image_ge_*`: quality-only control using weakest-image utility.
- `random_matched_same_coverage`: random control retaining the same number of high-descriptor pairs as PF-ERI.

## CzechLynx Known-ID Results

### High-Confidence Within Block

Raw descriptor top 10% retained {int(high_raw['retained_pairs'])} pairs with positive retention {fmt(high_raw['positive_retention'])}, false-candidate retention {fmt(high_raw['false_candidate_retention'])}, and retained false-candidate rate {fmt(high_raw['false_candidate_rate_among_retained'])}.

Using PF-ERI pair comparability >= 0.70 retained {int(high_pf['retained_pairs'])} pairs, positive retention {fmt(high_pf['positive_retention'])}, false-candidate retention {fmt(high_pf['false_candidate_retention'])}, and retained false-candidate rate {fmt(high_pf['false_candidate_rate_among_retained'])}. In the clean block, strict PF-ERI gating reduces coverage and is not clearly beneficial for false-rate reduction; this is expected because high-confidence pairs are already reviewable.

### High-Low Cross Block

Raw descriptor top 10% retained {int(cross_raw['retained_pairs'])} pairs with positive retention {fmt(cross_raw['positive_retention'])}, false-candidate retention {fmt(cross_raw['false_candidate_retention'])}, and retained false-candidate rate {fmt(cross_raw['false_candidate_rate_among_retained'])}.

PF-ERI pair comparability >= 0.40 retained {int(cross_pf['retained_pairs'])} pairs, positive retention {fmt(cross_pf['positive_retention'])}, false-candidate retention {fmt(cross_pf['false_candidate_retention'])}, and retained false-candidate rate {fmt(cross_pf['false_candidate_rate_among_retained'])}. {cross_random_text}

The nearest quality-only comparison at weakest-image utility >= 0.40 retained {int(cross_quality['retained_pairs'])} pairs, positive retention {fmt(cross_quality['positive_retention'])}, false-candidate retention {fmt(cross_quality['false_candidate_retention'])}, and retained false-candidate rate {fmt(cross_quality['false_candidate_rate_among_retained'])}. PF-ERI at 0.40 is Pareto dominated = `{bool(cross_pf_pareto['pareto_dominated'])}` in this block.

### Low-Evidence Stress Within Block

Raw descriptor top 10% retained {int(low_raw['retained_pairs'])} pairs with positive retention {fmt(low_raw['positive_retention'])}, false-candidate retention {fmt(low_raw['false_candidate_retention'])}, and retained false-candidate rate {fmt(low_raw['false_candidate_rate_among_retained'])}.

PF-ERI pair comparability >= 0.30 retained {int(low_pf['retained_pairs'])} pairs, positive retention {fmt(low_pf['positive_retention'])}, false-candidate retention {fmt(low_pf['false_candidate_retention'])}, and retained false-candidate rate {fmt(low_pf['false_candidate_rate_among_retained'])}. {low_random_text}

The quality-only threshold weakest-image utility >= 0.40 retained {int(low_quality['retained_pairs'])} pairs, positive retention {fmt(low_quality['positive_retention'])}, false-candidate retention {fmt(low_quality['false_candidate_retention'])}, and retained false-candidate rate {fmt(low_quality['false_candidate_rate_among_retained'])}. This quality-only policy dominates PF-ERI >= 0.30 in the low-evidence within block: PF-ERI dominated = `{bool(low_pf_pareto['pareto_dominated'])}`.

## Bobcat Transfer Stress

For bobcat low-evidence stress, PF-ERI pair comparability >= 0.30 retained {int(bobcat_low['retained_pairs'])} of {int(bobcat_low['eligible_high_descriptor_pairs'])} high-descriptor pairs, coverage {fmt(bobcat_low['retained_pair_coverage'])}, with high-conflict rate {fmt(bobcat_low['high_conflict_rate'])}. This is a review-burden and transfer-stress result only, not bobcat false-match validation.

## Interpretation

PF-ERI should be framed as a risk-controlled review policy, not as a replacement descriptor or automatic identity classifier. The most useful behavior appears in mixed evidence-axis candidate pools, where pair comparability can reduce retained false candidates among high-descriptor pairs. In the most severe low-evidence within block, quality-only control is currently stronger than PF-ERI alone. The next modeling step should therefore optimize a Pareto frontier and test a PF-ERI + quality hybrid, rather than choose a single universal threshold or claim PF-ERI always beats quality filtering.

## Outputs

- `{rel(POLICY_TABLE)}`
- `{rel(RANDOM_CONTROL)}`
- `{rel(RISK_COVERAGE)}`
- `{rel(BOBCAT_TRANSFER)}`
- `{rel(PARETO_TABLE)}`
"""
    REPORT_MD.write_text(text, encoding="utf-8")


def main() -> int:
    if not CONFLICT_TABLE.exists():
        raise FileNotFoundError(f"Missing descriptor-conflict table: {CONFLICT_TABLE}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conflict = pd.read_csv(CONFLICT_TABLE, low_memory=False)
    required = {
        "species_axis",
        "pair_block",
        "same_identity",
        "descriptor_similarity_percentile_block",
        "pair_comparability_score",
        "weakest_image_utility_score",
        "descriptor_evidence_conflict_score",
        "descriptor_conflict_band",
    }
    missing = required - set(conflict.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    policy, random_control, risk_coverage = build_czech_policies(conflict)
    bobcat_transfer = build_bobcat_transfer(conflict)
    pareto = build_pareto_diagnostics(policy)

    policy.to_csv(POLICY_TABLE, index=False)
    random_control.to_csv(RANDOM_CONTROL, index=False)
    risk_coverage.to_csv(RISK_COVERAGE, index=False)
    bobcat_transfer.to_csv(BOBCAT_TRANSFER, index=False)
    pareto.to_csv(PARETO_TABLE, index=False)
    write_report(policy, random_control, bobcat_transfer, pareto)

    audit = {
        "status": "complete",
        "inputs": {"descriptor_conflict_table": rel(CONFLICT_TABLE)},
        "outputs": {
            "policy_table": rel(POLICY_TABLE),
            "random_control": rel(RANDOM_CONTROL),
            "risk_coverage": rel(RISK_COVERAGE),
            "bobcat_transfer": rel(BOBCAT_TRANSFER),
            "pareto": rel(PARETO_TABLE),
            "report": rel(REPORT_MD),
            "audit": rel(AUDIT_JSON),
        },
        "row_counts": {
            "descriptor_conflict_table": int(len(conflict)),
            "policy_table": int(len(policy)),
            "random_control": int(len(random_control)),
            "risk_coverage": int(len(risk_coverage)),
            "bobcat_transfer": int(len(bobcat_transfer)),
            "pareto": int(len(pareto)),
        },
        "policy_design": {
            "high_descriptor_percentile": HIGH_DESCRIPTOR_PERCENTILE,
            "pf_eri_thresholds": PF_ERI_THRESHOLDS,
            "quality_thresholds": QUALITY_THRESHOLDS,
            "random_repeats": RANDOM_REPEATS,
            "random_seed": RANDOM_SEED,
        },
        "scientific_boundary": {
            "analysis_type": "controlled sampled candidate-pair review policy, not full gallery retrieval benchmark",
            "bobcat": "identity_unknown; transfer stress only",
            "czechlynx": "known-ID sampled positive/negative pair validation",
        },
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
