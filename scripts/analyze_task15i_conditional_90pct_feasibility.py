#!/usr/bin/env python3
"""Freeze a conditional 90-percent component-design feasibility analysis."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
CONTRACT = ROOT / "schemas/pferi_v2/task15i_conditional_90pct_feasibility_contract_v1.json"
TASK15I_RECORD = (
    MODEL_ROOT
    / "2026-07-25_task15i_independent_redevelopment_design_freeze_v1"
    / "independent_redevelopment_design_record.json"
)
OUTPUT = (
    MODEL_ROOT / "2026-07-25_task15i_conditional_90pct_feasibility_analysis_v1"
)
Z_95_TWO_SIDED = 1.959963984540054


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normal_cdf(value: float) -> float:
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError("refusing to write an empty scenario table")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_checksum_manifest(directory: Path) -> list[str]:
    manifest = directory / "CHECKSUMS.sha256"
    if not manifest.is_file():
        return ["missing:CHECKSUMS.sha256"]
    failures: list[str] = []
    declared: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        declared.add(relative)
        path = directory / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
        elif sha256(path) != expected:
            failures.append(f"sha256:{relative}")
    actual = {
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() and path.name != "CHECKSUMS.sha256"
    }
    failures.extend(f"inventory:{item}" for item in sorted(actual ^ declared))
    return failures


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("status") != "FROZEN_OUTCOME_FREE_CONDITIONAL_ANALYSIS":
        raise RuntimeError("conditional analysis contract is not frozen")
    return contract


def validate_task15i_record() -> dict[str, Any]:
    record = json.loads(TASK15I_RECORD.read_text(encoding="utf-8"))
    if record.get("status") != "FROZEN_OUTCOME_FREE_INDEPENDENT_REDEVELOPMENT_DESIGN":
        raise RuntimeError("Task15I design record is not the required outcome-free freeze")
    if record.get("new_development_outcomes_opened") is not False:
        raise RuntimeError("Task15I record unexpectedly opened outcomes")
    return record


def build_scenarios(
    *,
    component_counts: tuple[int, ...] | list[int],
    pairs_per_component: int,
    true_increments: tuple[float, ...] | list[float],
    paired_loss_sd: float,
    intracomponent_correlation: float,
    practical_increment: float,
    confidence_level: float = 0.95,
) -> list[dict[str, Any]]:
    if confidence_level != 0.95:
        raise ValueError("this frozen analysis supports a two-sided 95% bound only")
    if pairs_per_component <= 0 or not 0 <= intracomponent_correlation < 1:
        raise ValueError("invalid component-design assumptions")
    rows: list[dict[str, Any]] = []
    for components in component_counts:
        if components <= 1:
            raise ValueError("at least two components are required")
        pair_count = int(components * pairs_per_component)
        design_effect = 1 + (pairs_per_component - 1) * intracomponent_correlation
        effective_pair_count = pair_count / design_effect
        standard_error = paired_loss_sd / math.sqrt(effective_pair_count)
        for true_increment in true_increments:
            standardized_gap = (true_increment - practical_increment) / standard_error
            rows.append(
                {
                    "component_count": int(components),
                    "pairs_per_component": int(pairs_per_component),
                    "analyzable_pair_count": pair_count,
                    "design_effect": design_effect,
                    "effective_pair_count": effective_pair_count,
                    "paired_loss_difference_sd": paired_loss_sd,
                    "intracomponent_correlation": intracomponent_correlation,
                    "practical_brier_increment": practical_increment,
                    "synthetic_true_brier_increment": true_increment,
                    "standard_error": standard_error,
                    "point_threshold_success_probability": normal_cdf(standardized_gap),
                    "lower_confidence_bound_success_probability": normal_cdf(
                        standardized_gap - Z_95_TWO_SIDED
                    ),
                }
            )
    return rows


def minimum_design(
    rows: Iterable[dict[str, Any]],
    *,
    true_increment: float,
    probability_key: str,
    required_probability: float,
) -> dict[str, Any]:
    matching = [
        row
        for row in rows
        if math.isclose(row["synthetic_true_brier_increment"], true_increment)
        and row[probability_key] >= required_probability
    ]
    if not matching:
        raise RuntimeError("no scenario meets the conditional target")
    return min(
        matching,
        key=lambda row: (row["analyzable_pair_count"], row["component_count"]),
    )


def report_text(record: dict[str, Any]) -> str:
    screen = record["recommended_90pct_screen_design"]
    lower = record["recommended_90pct_confirmation_like_design"]
    return f"""# Task 15I Conditional 90% Feasibility Analysis

Status: `{record["status"]}`

## What 90% means here

This analysis does not estimate a 90% probability that PF-ERI will pass. It estimates conditional operating characteristics under a declared synthetic true Brier increment of 0.01, a paired-loss-difference standard deviation of 0.12, and intracomponent correlation of 0.10. The actual effect is unknown, and no real outcome was read to estimate it.

## Development-screen target

For the development screen, success means that the design-weighted P3-minus-P5 point estimate reaches 0.005. Under the declared synthetic assumptions, the smallest independence-first design exceeding 90% is {screen["component_count"]} components and {screen["analyzable_pair_count"]} pairs, with four pairs per component. Its effective pair count is {screen["effective_pair_count"]:.1f}, and its conditional success probability is {screen["point_threshold_success_probability"]:.4f}. This is an increase from the frozen 300-component, 1,200-pair Task15I design. Adoption would require a new prelabel contract and a new independent sampling feasibility audit.

## Confirmation-like target

For comparison, requiring the nominal two-sided 95% lower confidence bound to exceed 0.005 at the same synthetic true increment requires {lower["component_count"]} components and {lower["analyzable_pair_count"]} pairs. Its conditional lower-bound success probability is {lower["lower_confidence_bound_success_probability"]:.4f}. This much larger requirement shows why a development screen and a confirmation criterion should not be conflated.

## Practical implication

The path that can honestly target more than 90% for the development screen is to collect at least 400 genuinely independent new endpoint-image components and 1,600 analyzable pairs, while retaining fixed lambda 100, the feature definitions, pair and image disjointness, capped component size, capped endpoint degree, and blinded outcome procedure. More pairs generated from the same images do not create the required independent replication. This is still conditional on a true increment of 0.01. If the true increment is smaller than 0.005, no amount of sample-size planning can make the predeclared 0.005 threshold likely to pass without changing the scientific question.

## Boundary

This result cannot amend the frozen Task15I contract, open calibration, or authorize new outcome collection. It identifies the scale that a subsequent independent-design amendment would need to justify before any new label is opened.
"""


def freeze(output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing analysis: {output}")
    contract = load_contract()
    task15i = validate_task15i_record()
    assumptions = contract["assumptions"]
    rows = build_scenarios(
        component_counts=tuple(assumptions["component_counts"]),
        pairs_per_component=int(assumptions["pairs_per_component"]),
        true_increments=tuple(assumptions["synthetic_true_brier_increments"]),
        paired_loss_sd=float(assumptions["paired_loss_difference_sd"]),
        intracomponent_correlation=float(assumptions["intracomponent_correlation"]),
        practical_increment=float(assumptions["practical_brier_increment"]),
        confidence_level=float(assumptions["confidence_level"]),
    )
    screen_target = contract["targets"]["screen"]
    lower_target = contract["targets"]["confirmation_like"]
    screen = minimum_design(
        rows,
        true_increment=float(screen_target["synthetic_true_brier_increment"]),
        probability_key=str(screen_target["metric"]),
        required_probability=float(screen_target["required_probability"]),
    )
    lower = minimum_design(
        rows,
        true_increment=float(lower_target["synthetic_true_brier_increment"]),
        probability_key=str(lower_target["metric"]),
        required_probability=float(lower_target["required_probability"]),
    )
    record = {
        "record_version": "pferi_v2_task15i_conditional_90pct_feasibility_record_v1",
        "status": "FROZEN_CONDITIONAL_90PCT_FEASIBILITY_ANALYSIS",
        "outcomes_accessed": False,
        "actual_model_pass_probability_estimated": False,
        "conditional_not_actual_pass_probability": True,
        "calibration_authorized": False,
        "adoption_requires_new_contract_version": True,
        "source_task15i_status": task15i["status"],
        "assumptions": assumptions,
        "recommended_90pct_screen_design": screen,
        "recommended_90pct_confirmation_like_design": lower,
        "required_collection_conditions": [
            "at least 400 image-disjoint and pair-disjoint new endpoint-image components",
            "at least 1600 analyzable pairs with no more than four nominal pairs per component",
            "fixed lambda 100 for P3 and P5",
            "blinded outcome collection and frozen component-disjoint folds",
            "no reuse of existing stage images or pairs",
        ],
        "claim_boundary": contract["claim_boundary"],
        "source_sha256": {
            "contract": sha256(CONTRACT),
            "task15i_record": sha256(TASK15I_RECORD),
        },
    }
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        write_json(stage / "conditional_90pct_contract_frozen.json", contract)
        write_csv(stage / "conditional_90pct_scenarios.csv", rows)
        write_json(stage / "conditional_90pct_feasibility_record.json", record)
        (stage / "CONDITIONAL_90PCT_FEASIBILITY_REPORT.md").write_text(
            report_text(record), encoding="utf-8"
        )
        shutil.copy2(Path(__file__), stage / "analysis_builder_snapshot.py")
        audit = {
            "audit_version": "pferi_v2_task15i_conditional_90pct_feasibility_audit_v1",
            "status": "PASS",
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "outcomes_accessed": False,
            "conditional_not_actual_pass_probability": True,
            "recommended_90pct_screen_design": screen,
            "recommended_90pct_confirmation_like_design": lower,
            "calibration_authorized": False,
        }
        write_json(stage / "conditional_90pct_feasibility_audit.json", audit)
        targets = sorted(
            path
            for path in stage.rglob("*")
            if path.is_file() and path.name != "CHECKSUMS.sha256"
        )
        (stage / "CHECKSUMS.sha256").write_text(
            "".join(
                f"{sha256(path)}  {path.relative_to(stage)}\n" for path in targets
            ),
            encoding="utf-8",
        )
        shutil.move(str(stage), output)
    return audit


def main() -> int:
    try:
        print(json.dumps(freeze(), indent=2, sort_keys=True))
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
