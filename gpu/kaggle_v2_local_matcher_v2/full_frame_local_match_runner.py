#!/usr/bin/env python3
"""Resumable computational wrapper around the frozen PF-ERI v2 local matcher."""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path

import local_match_runner_v2 as core


PROVENANCE_COLUMNS = [
    "pair_execution_id",
    "direction",
    "region_source",
    "target_region_source",
    "retry_level",
    "fallback_reason",
    "keypoint_count_A",
    "keypoint_count_B",
    "raw_output_type",
    "raw_output_keys",
    "raw_output_shapes",
    "normalized_match_count",
    "ransac_input_shape",
    "ransac_inlier_count",
]
PAIR_COLUMNS = ["pair_execution_id", "left_asset_filename", "right_asset_filename"]


def read_pairs(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or []) != PAIR_COLUMNS:
            raise ValueError(f"pair manifest schema must be exactly {PAIR_COLUMNS}")
        rows = list(reader)
    pair_ids = [row["pair_execution_id"] for row in rows]
    if not rows or len(pair_ids) != len(set(pair_ids)):
        raise ValueError("pair manifest must contain unique nonempty rows")
    return rows


def verify_control_gate(control_dir: Path) -> None:
    freeze_path = control_dir / core.FREEZE
    smoke_path = control_dir / "full_frame_smoke_test.json"
    if not freeze_path.is_file():
        raise RuntimeError("missing matcher freeze record")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("contract_sha256") != core.sha(core.CONTRACT):
        raise RuntimeError("freeze hash verification failed")
    if not smoke_path.is_file() or json.loads(smoke_path.read_text(encoding="utf-8")).get("status") != "PASS":
        raise RuntimeError("mandatory full-frame smoke gate not passed")


def freeze(control_dir: Path) -> dict[str, object]:
    if (control_dir / core.FREEZE).exists():
        raise FileExistsError("freeze record already exists; refusing to replace it")
    record = core.freeze(control_dir)
    record["full_frame_wrapper_sha256"] = core.sha(Path(__file__))
    record["scope"] = "full_post_allocation_within_role_frame"
    (control_dir / core.FREEZE).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def smoke(pair_manifest: Path, image_dir: Path, control_dir: Path) -> dict[str, object]:
    freeze_path = control_dir / core.FREEZE
    if not freeze_path.is_file():
        raise RuntimeError("freeze must run before smoke")
    freeze_record = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze_record.get("contract_sha256") != core.sha(core.CONTRACT):
        raise RuntimeError("freeze hash verification failed")
    pairs = read_pairs(pair_manifest)[:5]
    if len(pairs) != 5:
        raise RuntimeError("smoke manifest has fewer than five pairs")
    params = json.loads(core.CONTRACT.read_text(encoding="utf-8"))["parameters"]
    models = core._models(params)
    records = []
    failures = []
    for pair in pairs:
        for direction, source_key, target_key in (
            ("A_to_B", "left_asset_filename", "right_asset_filename"),
            ("B_to_A", "right_asset_filename", "left_asset_filename"),
        ):
            runtime_errors: list[dict[str, object]] = []
            source = image_dir / pair[source_key]
            target = image_dir / pair[target_key]
            if not source.is_file() or not target.is_file():
                raise FileNotFoundError(f"smoke image missing for {pair['pair_execution_id']}")
            row, provenance = core.measure_direction_v2(
                pair["pair_execution_id"], direction, source, target, models, params, runtime_errors
            )
            attempt_diagnostics = [
                item for item in runtime_errors if item.get("failure_code") != "model_runtime_error"
            ]
            interface_failure = row["failure_code"] in {"image_decode_failure", "model_runtime_error"}
            if interface_failure:
                failures.append(f"{pair['pair_execution_id']}:{direction}:{row['failure_code']}")
            records.append(
                {
                    "pair_execution_id": pair["pair_execution_id"],
                    "direction": direction,
                    "decode_success": row["failure_code"] != "image_decode_failure",
                    "failure_code": row["failure_code"],
                    "provenance": provenance,
                    "attempt_diagnostics": attempt_diagnostics,
                    "runtime_errors": runtime_errors,
                }
            )
    result = {
        "status": "PASS" if not failures else "FAIL",
        "pair_count": 5,
        "direction_count": 10,
        "interface_failures": failures,
        "records": records,
        "claim_boundary": (
            "Smoke PASS verifies execution interfaces on five full-frame pairs. Scientific insufficient-match "
            "or insufficient-inlier outcomes remain valid failure measurements and do not become runtime errors."
        ),
    }
    control_dir.mkdir(parents=True, exist_ok=True)
    (control_dir / "full_frame_smoke_test.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def atomic_checkpoint(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run_shard(pair_manifest: Path, image_dir: Path, control_dir: Path, output_dir: Path) -> dict[str, object]:
    verify_control_gate(control_dir)
    pairs = read_pairs(pair_manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = output_dir / "pair_checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    params = json.loads(core.CONTRACT.read_text(encoding="utf-8"))["parameters"]
    models = core._models(params)
    for index, pair in enumerate(pairs, start=1):
        checkpoint = checkpoint_dir / f"{pair['pair_execution_id']}.json"
        if checkpoint.is_file():
            continue
        left = image_dir / pair["left_asset_filename"]
        right = image_dir / pair["right_asset_filename"]
        if not left.is_file() or not right.is_file():
            raise FileNotFoundError(f"missing image for {pair['pair_execution_id']}")
        runtime_errors: list[dict[str, object]] = []
        a_to_b, provenance_a = core.measure_direction_v2(
            pair["pair_execution_id"], "A_to_B", left, right, models, params, runtime_errors
        )
        b_to_a, provenance_b = core.measure_direction_v2(
            pair["pair_execution_id"], "B_to_A", right, left, models, params, runtime_errors
        )
        payload = {
            "pair_execution_id": pair["pair_execution_id"],
            "directional": [a_to_b, b_to_a],
            "canonical": core.canonicalize(pair["pair_execution_id"], a_to_b, b_to_a),
            "provenance": [provenance_a, provenance_b],
            "runtime_errors": runtime_errors,
        }
        atomic_checkpoint(checkpoint, payload)
        if index % 25 == 0 or index == len(pairs):
            print(f"checkpointed {index}/{len(pairs)}")
    return finalize_shard(pair_manifest, control_dir, output_dir)


def finalize_shard(pair_manifest: Path, control_dir: Path, output_dir: Path) -> dict[str, object]:
    verify_control_gate(control_dir)
    pairs = read_pairs(pair_manifest)
    checkpoints = output_dir / "pair_checkpoints"
    directional = []
    canonical = []
    provenance = []
    runtime_errors = []
    for pair in pairs:
        path = checkpoints / f"{pair['pair_execution_id']}.json"
        if not path.is_file():
            raise RuntimeError(f"missing pair checkpoint: {pair['pair_execution_id']}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("pair_execution_id") != pair["pair_execution_id"]:
            raise RuntimeError("checkpoint pair ID mismatch")
        directional.extend(payload["directional"])
        canonical.append(payload["canonical"])
        provenance.extend(payload["provenance"])
        runtime_errors.extend(payload["runtime_errors"])
    core.write_csv(output_dir / "directional_measurements.csv", core.DIRECTIONAL_COLUMNS, directional)
    core.write_csv(output_dir / "canonical_measurements.csv", core.CANONICAL_COLUMNS, canonical)
    core.write_csv(output_dir / "region_provenance.csv", PROVENANCE_COLUMNS, provenance)
    (output_dir / "runtime_errors.json").write_text(json.dumps(runtime_errors, indent=2) + "\n", encoding="utf-8")
    valid = [row for row in canonical if row["value_status"] == "not_missing"]
    errors = []
    if len(directional) != 2 * len(pairs):
        errors.append("directional_row_count_mismatch")
    if len(canonical) != len(pairs):
        errors.append("canonical_row_count_mismatch")
    if len(provenance) != 2 * len(pairs):
        errors.append("provenance_row_count_mismatch")
    status = "PASS" if not errors and len(valid) == len(pairs) else "PARTIAL" if not errors else "FAIL"
    audit = {
        "status": status,
        "pair_manifest_sha256": core.sha(pair_manifest),
        "pair_count": len(pairs),
        "directional_row_count": len(directional),
        "canonical_row_count": len(canonical),
        "successful_pair_count": len(valid),
        "valid_measurement_rate": len(valid) / len(pairs),
        "failure_distribution": dict(Counter(
            row["failure_code"] for row in canonical if row["value_status"] != "not_missing"
        )),
        "error_codes": errors,
        "freeze_hash_verification": "PASS",
        "scientific_pass_interpretation": (
            "PARTIAL is an acceptable completed execution when row-count and freeze checks pass but some pairs "
            "have pre-specified scientific failure codes. It is not evidence that PF-ERI performance passed."
        ),
    }
    (output_dir / "run_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze_parser = commands.add_parser("freeze")
    freeze_parser.add_argument("--control-dir", type=Path, required=True)
    smoke_parser = commands.add_parser("smoke")
    smoke_parser.add_argument("--pair-manifest", type=Path, required=True)
    smoke_parser.add_argument("--image-dir", type=Path, required=True)
    smoke_parser.add_argument("--control-dir", type=Path, required=True)
    run_parser = commands.add_parser("run-shard")
    run_parser.add_argument("--pair-manifest", type=Path, required=True)
    run_parser.add_argument("--image-dir", type=Path, required=True)
    run_parser.add_argument("--control-dir", type=Path, required=True)
    run_parser.add_argument("--output-dir", type=Path, required=True)
    finalize_parser = commands.add_parser("finalize-shard")
    finalize_parser.add_argument("--pair-manifest", type=Path, required=True)
    finalize_parser.add_argument("--control-dir", type=Path, required=True)
    finalize_parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        result = freeze(args.control_dir)
    elif args.command == "smoke":
        result = smoke(args.pair_manifest, args.image_dir, args.control_dir)
    elif args.command == "run-shard":
        result = run_shard(args.pair_manifest, args.image_dir, args.control_dir, args.output_dir)
    else:
        result = finalize_shard(args.pair_manifest, args.control_dir, args.output_dir)
    print(json.dumps(result, indent=2))
    if result.get("status") == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
