#!/usr/bin/env python3
"""Run an outcome-free, graph-aware power/workload sensitivity analysis for PF-ERI v2.

The program uses the frozen canonical-pair graph but never reads outcome labels, model
predictions, reviewer logs, identity truth, or feature values.  It is deliberately a
nonbinding sensitivity exercise: its synthetic paired-loss model shows which assumptions
would make a future Brier-score confirmation precise enough, rather than estimating that
future model's effect.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_VERSION = "pferi_v2_nonbinding_power_cost_sensitivity_scenarios_v1"
BOUNDARY = "nonbinding_pre_outcome_sensitivity"
CANONICAL_REQUIRED = {
    "canonical_pair_id",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "pair_availability_status",
    "pair_inclusion_status",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_path(path: Path) -> str:
    """Use a project-relative path in production and retain external test inputs verbatim."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def positive_numbers(values: object, name: str, allow_zero: bool = False) -> list[float]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{name} must be a nonempty list")
    converted = [float(value) for value in values]
    if any((value < 0 if allow_zero else value <= 0) for value in converted):
        raise ValueError(f"{name} contains an invalid value")
    return converted


def validate_config(config: dict[str, Any]) -> None:
    if config.get("scenario_version") != SCENARIO_VERSION:
        raise ValueError("Unexpected scenario_version")
    if config.get("binding_status") != BOUNDARY:
        raise ValueError("Simulation must remain explicitly nonbinding")
    if "official_seed" in config or "official_target" in config:
        raise ValueError("A nonbinding simulation cannot contain an official target or seed")
    for key in ("claim_boundary", "primary_estimand"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f"{key} must be a nonempty explanatory string")
    if int(config.get("graph_draws_per_design_point", 0)) < 100:
        raise ValueError("At least 100 graph draws are required")
    if not 0 < float(config.get("confidence_level", 0)) < 1:
        raise ValueError("confidence_level must lie strictly between zero and one")
    model = config.get("statistical_model")
    if not isinstance(model, dict):
        raise ValueError("Missing statistical_model")
    positive_numbers(model.get("practical_brier_increment_scenarios"), "practical increments")
    positive_numbers(model.get("true_brier_increment_scenarios"), "true increments")
    positive_numbers(model.get("paired_loss_difference_sd_scenarios"), "paired loss SD")
    fractions = positive_numbers(model.get("image_variance_fraction_scenarios"), "image variance fractions", allow_zero=True)
    if any(value >= 1 for value in fractions):
        raise ValueError("image variance fractions must be below one")
    counts = [int(value) for value in model.get("confirmation_analyzable_pair_counts", [])]
    if not counts or any(value < 2 for value in counts):
        raise ValueError("confirmation pair counts must be integers of at least two")
    workload = config.get("completion_and_workload_scenarios")
    if not isinstance(workload, dict):
        raise ValueError("Missing completion_and_workload_scenarios")
    completion = positive_numbers(workload.get("completion_rates"), "completion rates")
    if any(value > 1 for value in completion):
        raise ValueError("completion rates cannot exceed one")
    profiles = workload.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("At least one workload profile is required")
    for profile in profiles:
        if not isinstance(profile, dict) or not str(profile.get("profile_id", "")):
            raise ValueError("Every workload profile needs a profile_id")
        if float(profile.get("first_pass_minutes_per_pair", 0)) <= 0:
            raise ValueError("first-pass minutes must be positive")
        if not 0 <= float(profile.get("adjudication_rate", -1)) <= 1:
            raise ValueError("adjudication rate must lie between zero and one")
        if float(profile.get("adjudication_minutes_per_pair", 0)) <= 0:
            raise ValueError("adjudication minutes must be positive")
    runtime = config.get("feature_runtime_context")
    if not isinstance(runtime, dict) or float(runtime.get("local_match_pair_runtime_p95_seconds", 0)) <= 0:
        raise ValueError("feature_runtime_context must contain a positive local-match p95 runtime")


def load_eligible_edges(path: Path) -> tuple[np.ndarray, list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not CANONICAL_REQUIRED.issubset(rows[0]):
        raise ValueError("Canonical manifest has missing required columns")
    eligible = [
        row for row in rows
        if row["pair_availability_status"] == "available" and row["pair_inclusion_status"] == "eligible"
    ]
    pair_ids = [row["canonical_pair_id"] for row in eligible]
    if len(pair_ids) != len(set(pair_ids)):
        raise ValueError("Canonical manifest contains duplicate eligible pair IDs")
    nodes = sorted({endpoint for row in eligible for endpoint in (row["endpoint_a_image_id"], row["endpoint_b_image_id"])})
    node_index = {node: index for index, node in enumerate(nodes)}
    edges = np.array(
        [(node_index[row["endpoint_a_image_id"]], node_index[row["endpoint_b_image_id"]]) for row in eligible],
        dtype=np.int32,
    )
    if np.any(edges[:, 0] == edges[:, 1]):
        raise ValueError("Canonical manifest contains an eligible self-pair")
    return edges, nodes


def design_effects(
    edges: np.ndarray,
    node_count: int,
    sample_count: int,
    image_variance_fraction: float,
    graph_draws: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return graph-aware design effects for random canonical-pair subgraphs.

    For synthetic loss difference D_e = delta + sigma*sqrt(rho/2)(u_a+u_b)
    + sigma*sqrt(1-rho)epsilon_e, this is the exact conditional variance inflation
    of the pair mean relative to sigma^2 / n for the selected graph.
    """
    if sample_count > len(edges):
        raise ValueError("Requested analysis count exceeds the eligible canonical-pair universe")
    if image_variance_fraction == 0:
        return np.ones(graph_draws, dtype=float)
    effects = np.empty(graph_draws, dtype=float)
    for draw in range(graph_draws):
        chosen = edges[rng.choice(len(edges), size=sample_count, replace=False)]
        degree = np.bincount(chosen.ravel(), minlength=node_count)
        effects[draw] = (1 - image_variance_fraction) + (image_variance_fraction / 2) * float(np.dot(degree, degree)) / sample_count
    return effects


def normal_cdf(values: np.ndarray) -> np.ndarray:
    distribution = NormalDist()
    return np.array([distribution.cdf(float(value)) for value in values], dtype=float)


def simulate_power_rows(edges: np.ndarray, nodes: list[str], config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    model = config["statistical_model"]
    counts = [int(value) for value in model["confirmation_analyzable_pair_counts"]]
    rhos = [float(value) for value in model["image_variance_fraction_scenarios"]]
    draws = int(config["graph_draws_per_design_point"])
    z = NormalDist().inv_cdf(1 - (1 - float(config["confidence_level"])) / 2)
    rng = np.random.default_rng(int(config["simulation_seed"]))
    effect_cache: dict[tuple[int, float], np.ndarray] = {}
    graph_rows: list[dict[str, Any]] = []
    for count in counts:
        for rho in rhos:
            effects = design_effects(edges, len(nodes), count, rho, draws, rng)
            effect_cache[(count, rho)] = effects
            effective = count / effects
            graph_rows.append({
                "confirmation_analyzable_pair_count": count,
                "image_variance_fraction": rho,
                "graph_draw_count": draws,
                "design_effect_mean": float(np.mean(effects)),
                "design_effect_median": float(np.median(effects)),
                "design_effect_p05": float(np.quantile(effects, 0.05)),
                "design_effect_p95": float(np.quantile(effects, 0.95)),
                "effective_pair_count_mean": float(np.mean(effective)),
                "effective_pair_count_p05": float(np.quantile(effective, 0.05)),
            })
    rows: list[dict[str, Any]] = []
    for count in counts:
        for rho in rhos:
            effects = effect_cache[(count, rho)]
            for sd in [float(value) for value in model["paired_loss_difference_sd_scenarios"]]:
                standard_errors = sd * np.sqrt(effects / count)
                for practical in [float(value) for value in model["practical_brier_increment_scenarios"]]:
                    for true_increment in [float(value) for value in model["true_brier_increment_scenarios"]]:
                        standardized_margin = (true_increment - practical) / standard_errors
                        conditional_power = 1 - normal_cdf(z - standardized_margin)
                        rows.append({
                            "confirmation_analyzable_pair_count": count,
                            "image_variance_fraction": rho,
                            "paired_loss_difference_sd": sd,
                            "practical_brier_increment": practical,
                            "synthetic_true_brier_increment": true_increment,
                            "graph_draw_count": draws,
                            "confidence_level": float(config["confidence_level"]),
                            "power_estimate": float(np.mean(conditional_power)),
                            "graph_draw_power_sd": float(np.std(conditional_power, ddof=1)),
                            "graph_draw_power_mc_se": float(np.std(conditional_power, ddof=1) / math.sqrt(draws)),
                            "mean_design_effect": float(np.mean(effects)),
                            "mean_effective_pair_count": float(np.mean(count / effects)),
                            "interpretation_boundary": "Synthetic outcome-free sensitivity result; not a v2 effect estimate or sample-size decision.",
                        })
    return rows, graph_rows


def workload_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    model = config["statistical_model"]
    workload = config["completion_and_workload_scenarios"]
    pair_runtime = float(config["feature_runtime_context"]["local_match_pair_runtime_p95_seconds"])
    rows: list[dict[str, Any]] = []
    for analyzable in [int(value) for value in model["confirmation_analyzable_pair_counts"]]:
        for completion_rate in [float(value) for value in workload["completion_rates"]]:
            collected = math.ceil(analyzable / completion_rate)
            for profile in workload["profiles"]:
                first_pass = 2 * collected * float(profile["first_pass_minutes_per_pair"])
                adjudication = collected * float(profile["adjudication_rate"]) * float(profile["adjudication_minutes_per_pair"])
                rows.append({
                    "confirmation_analyzable_pair_count": analyzable,
                    "completion_rate_assumption": completion_rate,
                    "collected_pair_count_needed": collected,
                    "nonresponse_reserve_pair_count": collected - analyzable,
                    "workload_profile": profile["profile_id"],
                    "first_pass_reviewer_minutes": first_pass,
                    "expected_adjudication_reviewer_minutes": adjudication,
                    "total_reviewer_minutes": first_pass + adjudication,
                    "total_reviewer_hours": (first_pass + adjudication) / 60,
                    "local_match_compute_minutes_at_p95": collected * pair_runtime / 60,
                    "interpretation_boundary": "Illustrative workload only; no measured reviewer time, staff availability, money cost, or policy loss is claimed.",
                })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path.name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def make_figure(power_rows: list[dict[str, Any]], output: Path) -> dict[str, float]:
    available_practical = sorted({float(row["practical_brier_increment"]) for row in power_rows})
    available_true = sorted({float(row["synthetic_true_brier_increment"]) for row in power_rows})
    available_sd = sorted({float(row["paired_loss_difference_sd"]) for row in power_rows})
    practical = min(available_practical, key=lambda value: abs(value - 0.01))
    true_increment = min(available_true, key=lambda value: abs(value - 0.02))
    paired_sd = min(available_sd, key=lambda value: abs(value - 0.12))
    selected = [
        row for row in power_rows
        if row["practical_brier_increment"] == practical
        and row["synthetic_true_brier_increment"] == true_increment
        and row["paired_loss_difference_sd"] == paired_sd
    ]
    if not selected:
        raise ValueError("Plot subset is unavailable")
    fig, axis = plt.subplots(figsize=(7.2, 4.8))
    for rho in sorted({float(row["image_variance_fraction"]) for row in selected}):
        subset = sorted((row for row in selected if float(row["image_variance_fraction"]) == rho), key=lambda row: int(row["confirmation_analyzable_pair_count"]))
        axis.plot(
            [row["confirmation_analyzable_pair_count"] for row in subset],
            [row["power_estimate"] for row in subset],
            marker="o",
            label=f"image variance fraction = {rho:.02f}",
        )
    axis.axhline(0.8, color="#555555", linestyle="--", linewidth=1, label="0.80 reference only")
    axis.set_xlabel("Analyzable confirmation pairs")
    axis.set_ylabel(f"Synthetic probability that 95% lower bound exceeds {practical:.3f}")
    axis.set_ylim(0, 1.02)
    axis.set_title(f"Outcome-free graph-dependence sensitivity\n(true increment {true_increment:.3f}; paired-loss SD {paired_sd:.3f})")
    axis.legend(frameon=False, fontsize=8)
    axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=220)
    plt.close(fig)
    return {
        "practical_brier_increment": practical,
        "synthetic_true_brier_increment": true_increment,
        "paired_loss_difference_sd": paired_sd,
    }


def prose_report(config: dict[str, Any], power_rows: list[dict[str, Any]], graph_rows: list[dict[str, Any]], workload: list[dict[str, Any]], figure_context: dict[str, float]) -> str:
    available_rhos = sorted({float(row["image_variance_fraction"]) for row in power_rows})
    report_rho = min(available_rhos, key=lambda value: abs(value - 0.05))
    moderate = [
        row for row in power_rows
        if row["practical_brier_increment"] == figure_context["practical_brier_increment"]
        and row["synthetic_true_brier_increment"] == figure_context["synthetic_true_brier_increment"]
        and row["paired_loss_difference_sd"] == figure_context["paired_loss_difference_sd"]
        and row["image_variance_fraction"] == report_rho
    ]
    moderate = sorted(moderate, key=lambda row: row["confirmation_analyzable_pair_count"])
    first, last = moderate[0], moderate[-1]
    graph_example = min(
        graph_rows,
        key=lambda row: abs(int(row["confirmation_analyzable_pair_count"]) - 400) + abs(float(row["image_variance_fraction"]) - 0.1) * 1000,
    )
    workload_low = min(
        workload,
        key=lambda row: abs(int(row["confirmation_analyzable_pair_count"]) - 400) + abs(float(row["completion_rate_assumption"]) - 0.95) * 1000 + float(row["total_reviewer_minutes"]) / 10000,
    )
    workload_high = min(
        workload,
        key=lambda row: abs(int(row["confirmation_analyzable_pair_count"]) - 400) + abs(float(row["completion_rate_assumption"]) - 0.85) * 1000 - float(row["total_reviewer_minutes"]) / 10000,
    )
    return f"""# Workstream 04 Task 02: Nonbinding Graph-Aware Power and Workload Sensitivity

## Purpose and boundary

This outcome-free analysis examines how a future PF-ERI v2 confirmation result would depend on explicit assumptions about the practical Brier-score increment, variability of paired Brier-loss differences, shared-image dependence, analyzable confirmation size, completion, and reviewer workload. It does not fit a model, read a reviewability label, choose a sample size, or provide an effect estimate. The analysis uses {len(power_rows)} synthetic power scenarios and {config['graph_draws_per_design_point']} random subgraphs for each graph-design point. Its role is to show which assumptions would have to be accepted before an official target or seed can be defensibly frozen.

## Statistical construction

The simulated estimand is Brier(active control) minus Brier(full automatic-evidence model), so positive values favor the full model. For a selected canonical-pair subgraph, the synthetic paired-loss difference includes an independent pair term and two image-endpoint terms. The stated image-variance fraction is the proportion of marginal variance attributable jointly to the two endpoints; consequently, pairs sharing one image are correlated even though every canonical pair is counted once. The graph-specific design effect is calculated from the selected endpoints rather than assuming independent rows. For each scenario, the reported probability is the probability that the lower endpoint of a two-sided 95% normal-approximation graph-aware interval exceeds the stated practical increment. This is an intentionally transparent planning approximation, not the final confirmation interval or a guarantee of statistical power.

## Sensitivity result

In the plotted illustrative row, the practical increment is {figure_context['practical_brier_increment']:.3f}, the synthetic true increment is {figure_context['synthetic_true_brier_increment']:.3f}, and the paired-loss-difference standard deviation is {figure_context['paired_loss_difference_sd']:.3f}. With an image-variance fraction of {report_rho:.2f}, the synthetic probability rises from {first['power_estimate']:.3f} at {first['confirmation_analyzable_pair_count']} analyzable confirmation pairs to {last['power_estimate']:.3f} at {last['confirmation_analyzable_pair_count']} pairs. This pattern is conditional on the synthetic values, not an estimate that PF-ERI will achieve the stated increment. At the available graph design point closest to 400 selected pairs and an image-variance fraction of 0.10, the median graph design effect is {graph_example['design_effect_median']:.3f}, corresponding to a mean effective pair count of {graph_example['effective_pair_count_mean']:.1f}; this quantifies why a naive independent-row calculation would overstate precision.

## Workload result

The workload table separately converts analyzable-pair targets into collected-pair reserves under transparent completion and timing illustrations. At the available low-workload design point nearest to 400 analyzable pairs and 95% completion, the calculation requires {workload_low['collected_pair_count_needed']} collected pairs and {workload_low['total_reviewer_hours']:.1f} total reviewer hours. At the corresponding high-workload design point nearest to 400 pairs and 85% completion, it requires {workload_high['collected_pair_count_needed']} collected pairs and {workload_high['total_reviewer_hours']:.1f} reviewer hours. These are not field measurements; they show the operational consequences of values that still need to be measured or accepted before collection. The automatically measured local-match p95 runtime is retained only as a separate compute-workload context and is not converted into money or a claimed workflow benefit.

## Interpretation and next decision

The analysis establishes that the frozen graph can be used to evaluate dependence-sensitive design scenarios, but it does not determine which row is scientifically or operationally correct. The default 400 mechanism plus 800 deployment-pair design is therefore neither endorsed nor rejected by this output. Before an official simulation can recommend a target, the project owner must freeze the minimum practical Brier increment and decision rule, select a justified dependence and variability scenario or data-collection pilot, document reviewer availability and measured timing, choose a completion reserve, and state one principal transparent budget or loss region. Only then can a dated version of this framework make a numerical recommendation; that later artifact must still precede all v2 outcome review.
"""


def run_simulation(canonical_path: Path, config_path: Path, output_dir: Path) -> dict[str, Any]:
    config = load_json(config_path)
    validate_config(config)
    edges, nodes = load_eligible_edges(canonical_path)
    power_rows, graph_rows = simulate_power_rows(edges, nodes, config)
    workload = workload_rows(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "power_sensitivity_results.csv", power_rows)
    write_csv(output_dir / "graph_design_effect_summary.csv", graph_rows)
    write_csv(output_dir / "collection_workload_sensitivity.csv", workload)
    figure_context = make_figure(power_rows, output_dir / "power_sensitivity_illustration.png")
    (output_dir / "power_cost_sensitivity_report.md").write_text(
        prose_report(config, power_rows, graph_rows, workload, figure_context), encoding="utf-8"
    )
    audit = {
        "audit_version": "pferi_v2_workstream_04_nonbinding_power_cost_sensitivity_audit_v1",
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": "NONBINDING_SENSITIVITY_COMPLETE_NOT_READY_TO_FREEZE",
        "binding_status": config["binding_status"],
        "decision_scope": "Outcome-free statistical and workload sensitivity only. No official target, seed, stratum quota, reviewer packet, or outcome-review permission is produced.",
        "source_manifest": {
            "path_relative_to_project_root": audit_path(canonical_path),
            "sha256": sha256(canonical_path),
            "eligible_canonical_pair_count": int(len(edges)),
            "image_count": int(len(nodes)),
        },
        "scenario_config": {
            "path_relative_to_project_root": audit_path(config_path),
            "sha256": sha256(config_path),
            "scenario_version": config["scenario_version"],
            "nonofficial_simulation_seed": config["simulation_seed"],
        },
        "outputs": {
            "power_scenario_count": len(power_rows),
            "graph_design_point_count": len(graph_rows),
            "workload_scenario_count": len(workload),
            "figure": "power_sensitivity_illustration.png",
        },
        "v2_outcome_access": "none; no v2 reviewability label, reviewer log, model prediction, calibration result, or confirmation result was read.",
        "unresolved_freeze_inputs": [
            "minimum practical Brier increment and final decision rule",
            "final paired-loss variability and graph-dependence justification",
            "completion reserve based on a reviewer-operation record",
            "reviewer availability and measured first-pass/adjudication times",
            "one principal transparent cost or budget region and relative policy losses",
            "official target, strata, and sampling seed",
        ],
        "claim_boundary": config["claim_boundary"],
    }
    (output_dir / "power_cost_sensitivity_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--canonical-pairs",
        type=Path,
        default=ROOT / "outputs/pferi_v2/dual_descriptor_queue/canonical_pairs.csv",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "schemas/pferi_v2/nonbinding_power_cost_sensitivity_scenarios_v1.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs/pferi_v2/dual_sample_confirmation/2026-07-14_nonbinding_power_cost_sensitivity_v1",
    )
    args = parser.parse_args()
    audit = run_simulation(args.canonical_pairs.resolve(), args.config.resolve(), args.output_dir.resolve())
    print(f"{audit['status']}: {args.output_dir}")


if __name__ == "__main__":
    main()
