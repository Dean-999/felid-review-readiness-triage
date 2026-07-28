#!/usr/bin/env python3
"""Run the locked Task17 primary confirmation analysis exactly once."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "schemas/pferi_v2/task17_confirmation_outcome_analysis_contract_v1.json"
OUTPUT = ROOT / "outputs/pferi_v2/models/confirmation/final_analysis"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def commitment_digest(rows: list[dict[str, str]]) -> str:
    keys = (
        "canonical_pair_id",
        "final_three_category_label",
        "review_ready_label",
        "not_ready_or_uncertain_label",
        "final_label_source",
    )
    text = "\n".join("|".join(row[key] for key in keys) for row in sorted(rows, key=lambda item: item["canonical_pair_id"]))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dyadic_interval(
    deltas: np.ndarray, weights: np.ndarray, endpoint_pairs: list[tuple[str, str]], z_critical: float
) -> dict[str, float]:
    if len(deltas) == 0 or len(deltas) != len(weights) or len(deltas) != len(endpoint_pairs):
        raise ValueError("incompatible dyadic analysis inputs")
    if not np.isfinite(deltas).all() or not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError("non-finite deltas or non-positive weights")
    normalized = weights / weights.sum()
    estimate = float(np.dot(normalized, deltas))
    influence = normalized * (deltas - estimate)
    endpoint_sums: dict[str, float] = {}
    for (endpoint_a, endpoint_b), value in zip(endpoint_pairs, influence):
        if endpoint_a == endpoint_b:
            raise ValueError("self-pair is invalid for dyadic variance")
        endpoint_sums[endpoint_a] = endpoint_sums.get(endpoint_a, 0.0) + float(value)
        endpoint_sums[endpoint_b] = endpoint_sums.get(endpoint_b, 0.0) + float(value)
    variance = float(sum(value * value for value in endpoint_sums.values()) - np.dot(influence, influence))
    if variance < -1e-15:
        raise RuntimeError("negative dyadic sandwich variance")
    variance = max(0.0, variance)
    standard_error = math.sqrt(variance)
    independent_standard_error = math.sqrt(float(np.dot(influence, influence)))
    return {
        "estimate": estimate,
        "variance": variance,
        "standard_error": standard_error,
        "lower_95": estimate - z_critical * standard_error,
        "upper_95": estimate + z_critical * standard_error,
        "independent_row_se_diagnostic": independent_standard_error,
        "dyadic_to_independent_se_ratio": standard_error / independent_standard_error if independent_standard_error else 0.0,
    }


def resolve_sources(contract: dict[str, Any]) -> dict[str, Path]:
    return {name: ROOT / value for name, value in contract["sources"].items()}


def validate_and_prepare(contract: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sources = resolve_sources(contract)
    missing = [str(path.relative_to(ROOT)) for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing Task17 inputs: {missing}")
    mismatched_hashes = {
        name: {"expected": contract["frozen_sha256"][name], "observed": sha256(path)}
        for name, path in sources.items()
        if sha256(path) != contract["frozen_sha256"][name]
    }
    if mismatched_hashes:
        raise RuntimeError(f"Task17 frozen input hash mismatch: {mismatched_hashes}")

    task15m = read_json(sources["task15m_contract"])
    execution = read_json(sources["task15n_execution_freeze"])
    outcome_audit = read_json(sources["final_outcome_audit"])
    eligibility = contract["eligibility"]
    task15m_primary = task15m["primary_confirmation_analysis"]
    if (
        task15m_primary["positive_direction"] != contract["primary_analysis"]["positive_direction"]
        or float(task15m_primary["minimum_practical_increment"]) != float(contract["primary_analysis"]["minimum_practical_increment"])
        or "dyadic cluster-robust sandwich" not in task15m_primary["interval"]
        or "physical image" not in task15m_primary["interval"]
    ):
        raise RuntimeError("Task15M primary analysis binding mismatch")
    if execution.get("status") != "PASS_TASK15M_EXECUTION_VALIDATION" or execution.get("confirmation_outcomes_accessed") is not False:
        raise RuntimeError("Task15N execution freeze does not permit this analysis entry")
    if outcome_audit.get("status") != "PASS" or not outcome_audit.get("formal_outcome_use_authorized") or not outcome_audit.get("model_analysis_authorized"):
        raise RuntimeError("accepted final human outcomes are unavailable for model analysis")

    supported = read_csv(sources["supported_pair_manifest"])
    predictions = read_csv(sources["calibrated_predictions"])
    linkage = read_csv(sources["legacy_linkage"])
    formal = read_csv(sources["formal_sampling_manifest"])
    outcomes = read_csv(sources["final_adjudicated_outcomes"])
    commitments = read_json(sources["sealed_outcome_commitments"])
    deployment_outcomes = [row for row in outcomes if row["formal_sampling_stage"] == eligibility["formal_sampling_stage"]]
    expected_commitment = commitments["locked_stages"][eligibility["formal_sampling_stage"]]["outcome_commitment_sha256"]
    if len(deployment_outcomes) != eligibility["candidate_pair_count"] or expected_commitment != eligibility["outcome_commitment_sha256"] or commitment_digest(deployment_outcomes) != expected_commitment:
        raise RuntimeError("sealed deployment outcome commitment mismatch")
    if len(supported) != eligibility["supported_pair_count"] or len({row["canonical_pair_id"] for row in supported}) != len(supported):
        raise RuntimeError("supported-pair inventory mismatch")

    linkage_by_task = {row["task15m_confirmation_pair_id"]: row["historical_canonical_pair_id"] for row in linkage}
    formal_by_id = {row["canonical_pair_id"]: row for row in formal}
    outcome_by_id = {row["canonical_pair_id"]: row for row in deployment_outcomes}
    if len(linkage_by_task) != eligibility["candidate_pair_count"] or len(formal_by_id) < eligibility["candidate_pair_count"]:
        raise RuntimeError("linkage or formal sampling inventory mismatch")
    prediction_by_pair: dict[str, dict[str, float]] = {}
    for row in predictions:
        prediction_by_pair.setdefault(row["canonical_pair_id"], {})[row["model_id"]] = float(row["calibrated_probability_not_ready_or_uncertain"])

    records: list[dict[str, Any]] = []
    for supported_row in supported:
        task_id = supported_row["canonical_pair_id"]
        historical_id = linkage_by_task.get(task_id)
        sample = formal_by_id.get(historical_id or "")
        outcome = outcome_by_id.get(historical_id or "")
        model_predictions = prediction_by_pair.get(task_id, {})
        if historical_id is None or sample is None or outcome is None or set(model_predictions) != {"P3", "P5"}:
            raise RuntimeError(f"incomplete supported-pair linkage: {task_id}")
        if sample["formal_sampling_stage"] != eligibility["formal_sampling_stage"] or outcome[eligibility["outcome_label_column"]] not in {"0", "1"}:
            raise RuntimeError(f"invalid deployment outcome linkage: {task_id}")
        if (sample["endpoint_a_image_id"], sample["endpoint_b_image_id"]) != (outcome["endpoint_a_image_id"], outcome["endpoint_b_image_id"]):
            raise RuntimeError(f"physical endpoint mismatch: {task_id}")
        outcome_value = float(outcome[eligibility["outcome_label_column"]])
        p3, p5 = model_predictions["P3"], model_predictions["P5"]
        if not (0.0 <= p3 <= 1.0 and 0.0 <= p5 <= 1.0):
            raise RuntimeError(f"invalid calibrated probability: {task_id}")
        records.append(
            {
                "task15m_confirmation_pair_id": task_id,
                "historical_canonical_pair_id": historical_id,
                "endpoint_a_image_id": sample["endpoint_a_image_id"],
                "endpoint_b_image_id": sample["endpoint_b_image_id"],
                "first_order_inclusion_probability": float(sample["first_order_inclusion_probability"]),
                "not_ready_or_uncertain_label": outcome_value,
                "p3_calibrated_probability": p3,
                "p5_calibrated_probability": p5,
                "p3_brier_loss": (outcome_value - p3) ** 2,
                "p5_brier_loss": (outcome_value - p5) ** 2,
                "delta_brier_p3_minus_p5": (outcome_value - p3) ** 2 - (outcome_value - p5) ** 2,
            }
        )
    if len({row["historical_canonical_pair_id"] for row in records}) != len(records):
        raise RuntimeError("supported pairs do not map one-to-one to historical outcomes")
    provenance = {
        "source_sha256": {name: sha256(path) for name, path in sources.items()},
        "deployment_outcome_commitment_sha256": expected_commitment,
        "deployment_outcome_row_count": len(deployment_outcomes),
        "supported_pair_count": len(records),
        "unsupported_pair_count": eligibility["unsupported_pair_count"],
    }
    return records, provenance


def analyze(contract: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records, provenance = validate_and_prepare(contract)
    weights = np.asarray([1.0 / row["first_order_inclusion_probability"] for row in records], dtype=float)
    deltas = np.asarray([row["delta_brier_p3_minus_p5"] for row in records], dtype=float)
    endpoint_pairs = [(row["endpoint_a_image_id"], row["endpoint_b_image_id"]) for row in records]
    primary = contract["primary_analysis"]
    interval = dyadic_interval(deltas, weights, endpoint_pairs, float(primary["z_critical"]))
    normalized = weights / weights.sum()
    p3_brier = float(np.dot(normalized, np.asarray([row["p3_brier_loss"] for row in records])))
    p5_brier = float(np.dot(normalized, np.asarray([row["p5_brier_loss"] for row in records])))
    degrees = Counter(endpoint for pair in endpoint_pairs for endpoint in pair)
    lower = interval["lower_95"]
    threshold = float(primary["minimum_practical_increment"])
    status = "PASS_PRIMARY_CONFIRMATION" if lower > threshold else "FAIL_PRIMARY_CONFIRMATION"
    scientific_disposition = (
        "V2_CONFIRMED_WITH_BOUNDARIES" if status == "PASS_PRIMARY_CONFIRMATION" else
        "V2_MIXED_PRIMARY_INCREMENT_NOT_CONFIRMED" if interval["estimate"] > threshold else
        "V2_NOT_CONFIRMED_PRIMARY_INCREMENT_NOT_MET"
    )
    report = {
        "analysis_version": "pferi_v2_task17_confirmation_outcome_analysis_v1",
        "status": status,
        "scientific_disposition": scientific_disposition,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "claim_boundary": "This result evaluates the frozen P3/P5 calibrated predictions only on the 252 supported Task15M pairs. It does not establish identity accuracy, universal deployment utility, or automatic identity assignment.",
        "provenance": provenance,
        "sample": {
            "candidate_pair_count": contract["eligibility"]["candidate_pair_count"],
            "supported_pair_count": len(records),
            "unsupported_pair_count": contract["eligibility"]["unsupported_pair_count"],
            "unique_physical_endpoint_count": len(degrees),
            "maximum_physical_endpoint_degree": max(degrees.values()),
            "outcome_label_counts": dict(Counter(int(row["not_ready_or_uncertain_label"]) for row in records)),
        },
        "estimand": {
            "definition": primary["estimand"],
            "p3_weighted_brier": p3_brier,
            "p5_weighted_brier": p5_brier,
            "point_estimate": interval["estimate"],
            "minimum_practical_increment": threshold,
        },
        "interval": {
            "method": primary["interval"],
            **{key: interval[key] for key in ("standard_error", "lower_95", "upper_95", "independent_row_se_diagnostic", "dyadic_to_independent_se_ratio")},
        },
        "decision_rule": primary["success_rule"],
        "models_refit": False,
        "calibration_parameters_recomputed": False,
        "outcome_analysis_performed_once": True,
    }
    return report, records


def write_records(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def checksums(directory: Path) -> None:
    files = sorted(path for path in directory.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    (directory / "CHECKSUMS.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(directory)}\n" for path in files), encoding="utf-8"
    )


def freeze(output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    contract = read_json(CONTRACT)
    report, records = analyze(contract)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".task17_analysis.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        shutil.copy2(CONTRACT, stage / "task17_confirmation_outcome_analysis_contract.json")
        write_json(stage / "task17_confirmation_outcome_analysis.json", report)
        write_records(stage / "task17_pair_level_brier_losses.csv", records)
        estimand = report["estimand"]
        interval = report["interval"]
        (stage / "TASK17_CONFIRMATION_OUTCOME_ANALYSIS_REPORT.md").write_text(
            "# Task17 Confirmation Outcome Analysis\n\n"
            f"Status: **{report['status']}**\n\n"
            f"The frozen Hajek-weighted P3-minus-P5 Brier increment is `{estimand['point_estimate']:.9f}`. "
            f"The dyadic cluster-robust 95% interval is `[{interval['lower_95']:.9f}, {interval['upper_95']:.9f}]`; "
            f"the frozen lower-bound threshold is `{estimand['minimum_practical_increment']:.3f}`.\n",
            encoding="utf-8",
        )
        checksums(stage)
        shutil.move(str(stage), str(output))
    return report


def main() -> int:
    try:
        print(json.dumps(freeze(), indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
