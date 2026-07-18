#!/usr/bin/env python3
"""Run outcome-free, nonbinding image-partition feasibility stress simulations for WS03."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_VERSION = "pferi_v2_nonbinding_image_partition_feasibility_scenarios_v1"
ACTIVE_ROLES = ("development", "calibration", "confirmation")
CANONICAL_REQUIRED_COLUMNS = {
    "canonical_pair_id",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "pair_availability_status",
    "pair_inclusion_status",
}
MEMBERSHIP_REQUIRED_COLUMNS = {"canonical_pair_id", "descriptor_name"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def recorded_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = sorted(required_columns - headers)
        if missing:
            raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")
        return list(reader)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def validate_scenarios(config: dict[str, Any]) -> None:
    if config.get("scenario_version") != SCENARIO_VERSION:
        raise ValueError("unexpected scenario version")
    if config.get("binding_status") != "nonbinding_feasibility_stress_test":
        raise ValueError("scenario config must be explicitly nonbinding")
    seeds = config.get("seeds")
    if not isinstance(seeds, list) or len(seeds) < 2 or len(seeds) != len(set(seeds)):
        raise ValueError("scenario config requires at least two unique seeds")
    scenarios = config.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenario config requires at least one scenario")
    seen_ids: set[str] = set()
    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id")
        if not scenario_id or scenario_id in seen_ids:
            raise ValueError("scenario IDs must be nonempty and unique")
        seen_ids.add(scenario_id)
        shares = scenario.get("image_role_shares", {})
        if set(shares) != set(ACTIVE_ROLES):
            raise ValueError(f"{scenario_id} does not specify exactly the active roles")
        if any(not isinstance(value, (int, float)) or value <= 0 for value in shares.values()):
            raise ValueError(f"{scenario_id} has invalid image role share")
        if abs(sum(shares.values()) - 1.0) > 1e-9:
            raise ValueError(f"{scenario_id} image role shares must sum to one")
    benchmarks = config.get("nonbinding_capacity_stress_benchmarks", {})
    if int(benchmarks.get("minimum_unique_canonical_pairs_per_active_role", 0)) < 1:
        raise ValueError("minimum unique canonical-pair benchmark must be positive")
    if int(benchmarks.get("minimum_descriptor_covered_canonical_pairs_per_active_role", 0)) < 1:
        raise ValueError("minimum descriptor-covered pair benchmark must be positive")


def allocate_image_roles(images: list[str], shares: dict[str, float], seed: int, scenario_id: str) -> dict[str, str]:
    shuffled = list(images)
    random.Random(f"{scenario_id}:{seed}").shuffle(shuffled)
    total = len(shuffled)
    development_count = int(total * shares["development"])
    calibration_count = int(total * shares["calibration"])
    boundaries = (development_count, development_count + calibration_count)
    assignment: dict[str, str] = {}
    for index, image_id in enumerate(shuffled):
        if index < boundaries[0]:
            assignment[image_id] = "development"
        elif index < boundaries[1]:
            assignment[image_id] = "calibration"
        else:
            assignment[image_id] = "confirmation"
    return assignment


def simulate_once(
    canonical_rows: list[dict[str, str]],
    pair_descriptors: dict[str, set[str]],
    images: list[str],
    scenario: dict[str, Any],
    seed: int,
    benchmarks: dict[str, Any],
) -> dict[str, Any]:
    scenario_id = str(scenario["scenario_id"])
    shares = scenario["image_role_shares"]
    assignment = allocate_image_roles(images, shares, seed, scenario_id)
    image_role_counts = Counter(assignment.values())
    role_pair_counts = Counter()
    descriptor_pair_counts = Counter()
    descriptor_overlap_counts = Counter()
    cross_role_pair_count = 0
    for row in canonical_rows:
        pair_id = row["canonical_pair_id"]
        left_role = assignment[row["endpoint_a_image_id"]]
        right_role = assignment[row["endpoint_b_image_id"]]
        if left_role != right_role:
            cross_role_pair_count += 1
            continue
        role_pair_counts[left_role] += 1
        descriptors = pair_descriptors[pair_id]
        for descriptor in descriptors:
            descriptor_pair_counts[(left_role, descriptor)] += 1
        if len(descriptors) > 1:
            descriptor_overlap_counts[left_role] += 1
    min_pairs = int(benchmarks["minimum_unique_canonical_pairs_per_active_role"])
    min_descriptor_pairs = int(benchmarks["minimum_descriptor_covered_canonical_pairs_per_active_role"])
    descriptors = sorted({descriptor for values in pair_descriptors.values() for descriptor in values})
    role_pair_capacity_pass = all(role_pair_counts[role] >= min_pairs for role in ACTIVE_ROLES)
    descriptor_capacity_pass = all(
        descriptor_pair_counts[(role, descriptor)] >= min_descriptor_pairs
        for role in ACTIVE_ROLES
        for descriptor in descriptors
    )
    output: dict[str, Any] = {
        "scenario_id": scenario_id,
        "seed": seed,
        "cross_role_pair_count": cross_role_pair_count,
        "retained_pair_count": sum(role_pair_counts.values()),
        "retained_pair_fraction": sum(role_pair_counts.values()) / len(canonical_rows),
        "role_pair_capacity_pass": role_pair_capacity_pass,
        "descriptor_capacity_pass": descriptor_capacity_pass,
        "all_nonbinding_capacity_benchmarks_pass": role_pair_capacity_pass and descriptor_capacity_pass,
    }
    for role in ACTIVE_ROLES:
        output[f"{role}_image_count"] = image_role_counts[role]
        output[f"{role}_canonical_pair_count"] = role_pair_counts[role]
        output[f"{role}_multi_descriptor_pair_count"] = descriptor_overlap_counts[role]
        for descriptor in descriptors:
            output[f"{role}__{descriptor}_canonical_pair_count"] = descriptor_pair_counts[(role, descriptor)]
    return output


def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("cannot calculate percentile of empty values")
    ordered = sorted(values)
    location = (len(ordered) - 1) * probability
    lower = int(location)
    upper = min(lower + 1, len(ordered) - 1)
    weight = location - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize_runs(runs: list[dict[str, Any]], scenario: dict[str, Any]) -> dict[str, Any]:
    keys = [key for key in runs[0] if key.endswith("_count") or key == "retained_pair_fraction"]
    summary: dict[str, Any] = {
        "scenario_id": scenario["scenario_id"],
        "scenario_description": scenario["description"],
        "development_image_share": scenario["image_role_shares"]["development"],
        "calibration_image_share": scenario["image_role_shares"]["calibration"],
        "confirmation_image_share": scenario["image_role_shares"]["confirmation"],
        "seed_count": len(runs),
        "all_runs_nonbinding_capacity_benchmarks_pass": all(
            bool(run["all_nonbinding_capacity_benchmarks_pass"]) for run in runs
        ),
        "failed_run_count": sum(not bool(run["all_nonbinding_capacity_benchmarks_pass"]) for run in runs),
    }
    for key in keys:
        values = [float(run[key]) for run in runs]
        summary[f"{key}__min"] = min(values)
        summary[f"{key}__median"] = statistics.median(values)
        summary[f"{key}__p05"] = percentile(values, 0.05)
        summary[f"{key}__p95"] = percentile(values, 0.95)
        summary[f"{key}__max"] = max(values)
    return summary


def build_report(audit: dict[str, Any]) -> str:
    summary = audit["scenario_summaries"]
    scenario_sentences = []
    for row in summary:
        scenario_sentences.append(
            f"The {row['scenario_id']} scenario retained a median of {row['retained_pair_count__median']:,.0f} canonical pairs "
            f"and excluded a median of {row['cross_role_pair_count__median']:,.0f} cross-role pairs across its {row['seed_count']} seeds."
        )
    return f"""# WS03 Nonbinding Image-Partition Feasibility Stress Test

## Scope

This simulation evaluates whether the frozen outcome-free CzechLynx candidate graph can support later non-overlapping image partitions. It does not create a development, calibration, or confirmation split. The image shares, seeds, and capacity thresholds used here are nonbinding stress scenarios rather than a sample-size decision, sampling rule, or formal allocation. No identity truth, review outcome, feature value, model output, or threshold was read.

## Methods

For each scenario and seed, the simulation assigned every candidate image to exactly one temporary role. A canonical pair was retained only if both endpoints received the same role; otherwise it was counted as a cross-role pair that a future real split would have to exclude. Descriptor coverage was counted once per canonical pair and descriptor family, so duplicate directional memberships were not treated as independent observations. The stress benchmark required each active role to retain at least {audit['benchmarks']['minimum_unique_canonical_pairs_per_active_role']:,} unique canonical pairs and at least {audit['benchmarks']['minimum_descriptor_covered_canonical_pairs_per_active_role']:,} descriptor-covered canonical pairs per descriptor family. Those values are capacity checks only and do not prescribe the later labelled sample size.

## Results

The candidate universe contained {audit['input_counts']['image_count']:,} images, {audit['input_counts']['canonical_pair_count']:,} eligible canonical pairs, and {audit['input_counts']['descriptor_family_count']} descriptor families. {' '.join(scenario_sentences)} All configured nonbinding scenarios {'met' if audit['all_scenarios_pass_nonbinding_capacity_benchmarks'] else 'did not meet'} the stated capacity benchmarks in every simulated seed.

## Interpretation and limitation

The result shows only graph-capacity feasibility: a disjoint-image split can leave a large enough within-role pair pool under the tested stress configurations. It does not establish that any configuration is scientifically optimal, representative, identity-disjoint, or ready for outcome review. Random image assignment also cannot guarantee future balance over laterality, quality, illumination, camera/site, or known identity. The formal allocation must still be selected by the later power-and-cost analysis, fixed with a new official seed, validated with the Workstream 03 partition contract, and audited against the authorized identity graph before it can be locked.
"""


def run_simulation(
    canonical_pairs_path: Path,
    memberships_path: Path,
    scenario_config_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    config = json.loads(scenario_config_path.read_text(encoding="utf-8"))
    validate_scenarios(config)
    canonical_all = read_csv(canonical_pairs_path, CANONICAL_REQUIRED_COLUMNS)
    canonical_rows = [
        row
        for row in canonical_all
        if row["pair_availability_status"] == "available" and row["pair_inclusion_status"] == "eligible"
    ]
    canonical_ids = {row["canonical_pair_id"] for row in canonical_rows}
    images = sorted({row["endpoint_a_image_id"] for row in canonical_rows} | {row["endpoint_b_image_id"] for row in canonical_rows})
    membership_rows = read_csv(memberships_path, MEMBERSHIP_REQUIRED_COLUMNS)
    pair_descriptors: dict[str, set[str]] = defaultdict(set)
    missing_membership_pairs = 0
    for row in membership_rows:
        pair_id = row["canonical_pair_id"]
        if pair_id not in canonical_ids:
            missing_membership_pairs += 1
            continue
        pair_descriptors[pair_id].add(row["descriptor_name"])
    pairs_without_descriptor = sorted(pair_id for pair_id in canonical_ids if not pair_descriptors[pair_id])
    if missing_membership_pairs or pairs_without_descriptor:
        raise ValueError(
            f"membership reconciliation failed: missing_membership_pairs={missing_membership_pairs}, "
            f"pairs_without_descriptor={len(pairs_without_descriptor)}"
        )
    all_runs: list[dict[str, Any]] = []
    scenario_summaries: list[dict[str, Any]] = []
    for scenario in config["scenarios"]:
        runs = [
            simulate_once(canonical_rows, pair_descriptors, images, scenario, int(seed), config["nonbinding_capacity_stress_benchmarks"])
            for seed in config["seeds"]
        ]
        all_runs.extend(runs)
        scenario_summaries.append(summarize_runs(runs, scenario))
    output_dir.mkdir(parents=True, exist_ok=True)
    run_fields = list(all_runs[0])
    summary_fields = list(scenario_summaries[0])
    write_csv(output_dir / "nonbinding_partition_feasibility_runs.csv", all_runs, run_fields)
    write_csv(output_dir / "nonbinding_partition_feasibility_summary.csv", scenario_summaries, summary_fields)
    audit = {
        "audit_version": "pferi_v2_ws03_nonbinding_image_partition_feasibility_audit_v1",
        "status": "PASS" if all(row["all_runs_nonbinding_capacity_benchmarks_pass"] for row in scenario_summaries) else "FAIL",
        "binding_status": "nonbinding_feasibility_stress_test",
        "claim_boundary": (
            "This outcome-free stress simulation does not create or authorize a split, official seed, sample-size decision, "
            "outcome review, or partition_locked decision."
        ),
        "input_artifacts": {
            "canonical_pairs": {"path": recorded_path(canonical_pairs_path), "sha256": sha256(canonical_pairs_path)},
            "candidate_memberships": {"path": recorded_path(memberships_path), "sha256": sha256(memberships_path)},
            "scenario_config": {"path": recorded_path(scenario_config_path), "sha256": sha256(scenario_config_path)},
        },
        "input_counts": {
            "image_count": len(images),
            "canonical_pair_count": len(canonical_rows),
            "membership_row_count": len(membership_rows),
            "descriptor_family_count": len({descriptor for values in pair_descriptors.values() for descriptor in values}),
        },
        "benchmarks": config["nonbinding_capacity_stress_benchmarks"],
        "seed_count_per_scenario": len(config["seeds"]),
        "scenario_summaries": scenario_summaries,
        "all_scenarios_pass_nonbinding_capacity_benchmarks": all(
            row["all_runs_nonbinding_capacity_benchmarks_pass"] for row in scenario_summaries
        ),
        "next_boundary": (
            "Use the later power-and-cost analysis to select an official allocation, sample size, and seed. Then generate "
            "real manifests and validate zero image/pair crossing plus the restricted identity sensitivity condition."
        ),
    }
    (output_dir / "nonbinding_partition_feasibility_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "nonbinding_partition_feasibility_report.md").write_text(build_report(audit), encoding="utf-8")
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--canonical-pairs",
        type=Path,
        default=ROOT / "outputs/pferi_v2/dual_descriptor_queue/canonical_pairs.csv",
    )
    parser.add_argument(
        "--memberships",
        type=Path,
        default=ROOT / "outputs/pferi_v2/dual_descriptor_queue/candidate_memberships.csv",
    )
    parser.add_argument(
        "--scenario-config",
        type=Path,
        default=ROOT / "schemas/pferi_v2/nonbinding_image_partition_feasibility_scenarios_v1.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs/pferi_v2/information_partitioning/2026-07-14_nonbinding_partition_feasibility_v1",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = run_simulation(
        args.canonical_pairs.resolve(), args.memberships.resolve(), args.scenario_config.resolve(), args.output_dir.resolve()
    )
    print(audit["status"])
    print(json.dumps(audit["scenario_summaries"], indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
