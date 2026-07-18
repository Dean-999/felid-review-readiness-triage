#!/usr/bin/env python3
"""Audit the accepted PF-ERI v2 four-stage allocation without reading outcomes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "pferi_v2_four_stage_sample_allocation_contract_v1"
EXPECTED_STATUS = "accepted_pre_outcome_allocation_sampling_execution_pending"
ANALYTICAL_ROLES = (
    "development",
    "calibration",
    "mechanism_confirmation",
    "deployment_confirmation",
)


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


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def validate_contract(contract: dict[str, Any]) -> dict[str, int]:
    if contract.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("unexpected contract version")
    if contract.get("status") != EXPECTED_STATUS:
        raise ValueError("allocation contract must remain explicitly pre-outcome and sampling-execution-pending")
    if contract.get("v2_outcome_access") != "none":
        raise ValueError("allocation contract must declare zero v2 outcome access")

    image_roles = contract.get("image_information_roles")
    expected_image_roles = {"development": 1000, "calibration": 1000, "confirmation": 1000}
    if image_roles != expected_image_roles or sum(image_roles.values()) != 3000:
        raise ValueError("image information roles must equal the accepted 1000/1000/1000 allocation")
    if contract.get("candidate_universe", {}).get("image_count") != 3000:
        raise ValueError("candidate image total must equal 3000")

    completion = contract.get("planning_completion_fraction")
    if not isinstance(completion, (int, float)) or not math.isclose(float(completion), 0.90):
        raise ValueError("planning completion fraction must equal the accepted 0.90")
    roles = contract.get("analytical_roles")
    if not isinstance(roles, dict) or set(roles) != set(ANALYTICAL_ROLES):
        raise ValueError("analytical roles must match the accepted four-stage design")

    expected_targets = {
        "development": 400,
        "calibration": 400,
        "mechanism_confirmation": 400,
        "deployment_confirmation": 800,
    }
    expected_information_roles = {
        "development": "development",
        "calibration": "calibration",
        "mechanism_confirmation": "confirmation",
        "deployment_confirmation": "confirmation",
    }
    planned_total = 0
    analyzable_total = 0
    for role in ANALYTICAL_ROLES:
        details = roles[role]
        target = details.get("target_analyzable_pairs")
        planned = details.get("planned_collection_pairs")
        if target != expected_targets[role]:
            raise ValueError(f"{role} target analyzable pairs do not match the accepted design")
        expected_planned = math.ceil(target / float(completion))
        if planned != expected_planned:
            raise ValueError(f"{role} planned collection pairs must equal ceil(target/completion)")
        if details.get("image_information_role") != expected_information_roles[role]:
            raise ValueError(f"{role} is mapped to the wrong image information role")
        analyzable_total += target
        planned_total += planned

    totals = contract.get("totals", {})
    if analyzable_total != 2000 or totals.get("target_analyzable_pairs") != analyzable_total:
        raise ValueError("target analyzable pair total must equal 2000")
    if planned_total != 2224 or totals.get("planned_collection_pairs") != planned_total:
        raise ValueError("planned collection pair total must equal 2224")
    if totals.get("first_pass_judgements_if_every_pair_is_double_reviewed") != 2 * planned_total:
        raise ValueError("double-review first-pass judgement total is inconsistent")

    separation = contract.get("separation_rules", {})
    if separation.get("image_role_crossing_allowed") is not False:
        raise ValueError("image role crossing must be prohibited")
    if separation.get("canonical_pair_role_crossing_allowed") is not False:
        raise ValueError("canonical pair role crossing must be prohibited")
    if separation.get("mechanism_and_deployment_pair_overlap_allowed") is not False:
        raise ValueError("mechanism and deployment pair overlap must be prohibited")
    if separation.get("confirmation_outcomes_may_influence_development_or_calibration") is not False:
        raise ValueError("confirmation outcomes must not influence development or calibration")
    if separation.get("both_confirmation_samples_released_only_after_common_freeze") is not True:
        raise ValueError("both confirmation samples must be released only after a common freeze")

    claim_boundary = str(contract.get("claim_boundary", "")).lower()
    if "does not create an official split" not in claim_boundary or "model performance" not in claim_boundary:
        raise ValueError("contract claim boundary must block split and model-performance claims")
    remaining = contract.get("remaining_freeze_gates")
    if not isinstance(remaining, list) or not remaining:
        raise ValueError("remaining freeze gates must stay explicit")

    return {
        "development": int(roles["development"]["planned_collection_pairs"]),
        "calibration": int(roles["calibration"]["planned_collection_pairs"]),
        "confirmation": int(roles["mechanism_confirmation"]["planned_collection_pairs"])
        + int(roles["deployment_confirmation"]["planned_collection_pairs"]),
    }


def read_equal_thirds_capacity(path: Path) -> dict[str, int]:
    required = {
        "scenario_id",
        "development_image_count__min",
        "calibration_image_count__min",
        "confirmation_image_count__min",
        "development_canonical_pair_count__min",
        "calibration_canonical_pair_count__min",
        "confirmation_canonical_pair_count__min",
    }
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"capacity summary is missing columns: {', '.join(missing)}")
        matches = [row for row in reader if row["scenario_id"] == "equal_image_thirds"]
    if len(matches) != 1:
        raise ValueError("capacity summary must contain exactly one equal_image_thirds row")
    row = matches[0]
    image_counts = {role: int(float(row[f"{role}_image_count__min"])) for role in ("development", "calibration", "confirmation")}
    if image_counts != {"development": 1000, "calibration": 1000, "confirmation": 1000}:
        raise ValueError("archived equal-thirds image counts do not match the accepted design")
    return {
        role: int(float(row[f"{role}_canonical_pair_count__min"]))
        for role in ("development", "calibration", "confirmation")
    }


def build_audit(contract_path: Path, capacity_summary_path: Path) -> dict[str, Any]:
    contract = read_json(contract_path)
    requirements = validate_contract(contract)
    capacities = read_equal_thirds_capacity(capacity_summary_path)
    checks: dict[str, dict[str, Any]] = {}
    for role in ("development", "calibration", "confirmation"):
        required = requirements[role]
        available = capacities[role]
        checks[role] = {
            "required_planned_pairs": required,
            "archived_minimum_within_role_canonical_pairs": available,
            "capacity_margin_pairs": available - required,
            "capacity_multiple": available / required,
            "pass": available >= required,
        }
    all_pass = all(details["pass"] for details in checks.values())
    return {
        "audit_version": "pferi_v2_ws04_four_stage_allocation_readiness_audit_v1",
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": "PASS_CAPACITY_ONLY" if all_pass else "FAIL_CAPACITY",
        "v2_outcome_access": "none",
        "authorizes_official_split_or_outcome_packet": False,
        "claim_boundary": (
            "This outcome-free audit checks arithmetic and archived graph capacity only. It does not establish power, "
            "representativeness, reviewer completion, label reliability, model performance, calibration, a sampling seed, "
            "a locked partition, or permission to create an outcome packet."
        ),
        "accepted_design": {
            "image_information_roles": contract["image_information_roles"],
            "planning_completion_fraction": contract["planning_completion_fraction"],
            "target_analyzable_pairs": contract["totals"]["target_analyzable_pairs"],
            "planned_collection_pairs": contract["totals"]["planned_collection_pairs"],
            "first_pass_judgements_if_every_pair_is_double_reviewed": contract["totals"][
                "first_pass_judgements_if_every_pair_is_double_reviewed"
            ],
        },
        "capacity_checks": checks,
        "input_artifacts": {
            "allocation_contract": {"path": recorded_path(contract_path), "sha256": sha256(contract_path)},
            "archived_capacity_summary": {"path": recorded_path(capacity_summary_path), "sha256": sha256(capacity_summary_path)},
        },
        "remaining_freeze_gates": contract["remaining_freeze_gates"],
        "next_authorized_action": (
            "Complete and audit the frozen within-role automatic pair measurements and post-allocation capacity gates. "
            "Do not create formal outcome packets until every remaining gate passes."
        ),
    }


def build_report(audit: dict[str, Any]) -> str:
    checks = audit["capacity_checks"]
    rows = "\n".join(
        f"| {role} | {details['required_planned_pairs']:,} | {details['archived_minimum_within_role_canonical_pairs']:,} | "
        f"{details['capacity_margin_pairs']:,} | {'PASS' if details['pass'] else 'FAIL'} |"
        for role, details in checks.items()
    )
    return f"""# PF-ERI v2 Four-Stage Allocation Readiness Audit

Status: **{audit['status']}**

This audit read no v2 outcome. It checks the accepted allocation arithmetic against the minimum within-role canonical-pair counts observed in the archived equal-image-thirds graph stress test.

| Image information role | Planned pair requirement | Archived minimum capacity | Margin | Result |
|---|---:|---:|---:|---|
{rows}

The accepted programme targets 2,000 analyzable canonical pairs and prepares 2,224 unique unordered pairs under a 0.90 planning completion fraction. If every prepared pair receives two first-pass reviews, that is 4,448 first-pass judgements before any adjudication.

## Scientific boundary

{audit['claim_boundary']}

## Next gate

{audit['next_authorized_action']}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=ROOT / "schemas/pferi_v2/four_stage_sample_allocation_contract_v1.json",
    )
    parser.add_argument(
        "--capacity-summary",
        type=Path,
        default=ROOT
        / "outputs/pferi_v2/information_partitioning/2026-07-14_nonbinding_partition_feasibility_v1/nonbinding_partition_feasibility_summary.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT
        / "outputs/pferi_v2/dual_sample_confirmation/2026-07-15_four_stage_allocation_readiness_v1",
    )
    args = parser.parse_args()
    audit = build_audit(args.contract.resolve(), args.capacity_summary.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = args.output_dir / "four_stage_allocation_readiness_audit.json"
    report_path = args.output_dir / "four_stage_allocation_readiness_report.md"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(build_report(audit), encoding="utf-8")
    print(f"{audit['status']}: {audit_path}")
    if audit["status"] != "PASS_CAPACITY_ONLY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
