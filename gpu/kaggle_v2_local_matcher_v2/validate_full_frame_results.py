#!/usr/bin/env python3
"""Validate every inventory-declared PF-ERI full-frame shard as one execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from full_frame_execution_common import (
    CANONICAL_COLUMNS,
    COMPLETED_SHARD_STATUSES,
    DIRECTIONAL_COLUMNS,
    PROVENANCE_COLUMNS,
    SHARD_OUTPUT_HASH_FILES,
    SHARD_ID_PATTERN,
    ExecutionPaths,
    ShardSpec,
    atomic_write_csv,
    atomic_write_json,
    load_inventory,
    read_csv,
    read_json,
    sha256_file,
)


REQUIRED_RESULT_FILES = (
    "run_audit.json",
    "shard_execution_binding.json",
    "canonical_measurements.csv",
    "directional_measurements.csv",
    "region_provenance.csv",
    "runtime_errors.json",
    "shard_output_checksums.json",
)
EXPECTED_DIRECTIONS = {"A_to_B", "B_to_A"}
BINDING_ARTIFACT_KEYS = (
    "inventory_sha256",
    "wrapper_sha256",
    "core_runner_sha256",
    "protocol_sha256",
    "freeze_record_sha256",
    "image_set_sha256",
    "weight_set_sha256",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(errors: list[str], code: str) -> None:
    if code not in errors:
        errors.append(code)


def _direction_map(rows: Iterable[dict[str, str]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        result[row.get("pair_execution_id", "")].append(row.get("direction", ""))
    return result


def _directions_are_exact(rows: list[dict[str, str]], expected_pair_ids: set[str]) -> bool:
    by_pair = _direction_map(rows)
    if set(by_pair) != expected_pair_ids:
        return False
    return all(
        len(directions) == 2 and set(directions) == EXPECTED_DIRECTIONS
        for directions in by_pair.values()
    )


def validate_shard(spec: ShardSpec, output_dir: Path) -> dict[str, Any]:
    """Validate one shard without accepting its own audit claims on trust."""
    errors: list[str] = []
    missing_files = [name for name in REQUIRED_RESULT_FILES if not (output_dir / name).is_file()]
    if missing_files:
        return {
            "shard_id": spec.shard_id,
            "partition_role": spec.role,
            "status": "FAIL",
            "error_codes": ["missing_shard_file"],
            "missing_files": missing_files,
            "expected_pair_count": spec.pair_count,
            "observed_canonical_count": 0,
            "observed_directional_count": 0,
            "observed_provenance_count": 0,
            "execution_fingerprint": None,
        }

    audit: dict[str, Any] = {}
    binding: dict[str, Any] = {}
    canonical: list[dict[str, str]] = []
    directional: list[dict[str, str]] = []
    provenance: list[dict[str, str]] = []
    canonical_fields: list[str] = []
    directional_fields: list[str] = []
    provenance_fields: list[str] = []
    runtime_errors: Any = None
    output_checksums: Any = None
    try:
        audit = read_json(output_dir / "run_audit.json")
        binding = read_json(output_dir / "shard_execution_binding.json")
        canonical, canonical_fields = read_csv(output_dir / "canonical_measurements.csv")
        directional, directional_fields = read_csv(output_dir / "directional_measurements.csv")
        provenance, provenance_fields = read_csv(output_dir / "region_provenance.csv")
        runtime_errors = read_json(output_dir / "runtime_errors.json")
        output_checksums = read_json(output_dir / "shard_output_checksums.json")
    except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError, TypeError):
        _append(errors, "unreadable_shard_file")

    if not isinstance(audit, dict):
        _append(errors, "invalid_run_audit")
        audit = {}
    if audit.get("status") not in COMPLETED_SHARD_STATUSES:
        _append(errors, "invalid_shard_status")
    if audit.get("pair_manifest_sha256") != spec.manifest_sha256:
        _append(errors, "audit_manifest_hash_mismatch")
    try:
        if int(audit.get("pair_count", -1)) != spec.pair_count:
            _append(errors, "audit_pair_count_mismatch")
        if int(audit.get("canonical_row_count", -1)) != len(canonical):
            _append(errors, "audit_canonical_count_mismatch")
        if int(audit.get("directional_row_count", -1)) != len(directional):
            _append(errors, "audit_directional_count_mismatch")
    except (TypeError, ValueError):
        _append(errors, "invalid_run_audit")
    if audit.get("error_codes") not in (None, []):
        _append(errors, "shard_audit_reports_errors")

    if canonical_fields != CANONICAL_COLUMNS:
        _append(errors, "canonical_schema_mismatch")
    if directional_fields != DIRECTIONAL_COLUMNS:
        _append(errors, "directional_schema_mismatch")
    if provenance_fields != PROVENANCE_COLUMNS:
        _append(errors, "provenance_schema_mismatch")
    if not isinstance(runtime_errors, list):
        _append(errors, "runtime_errors_schema_mismatch")
    if not isinstance(output_checksums, dict):
        _append(errors, "shard_output_checksums_schema_mismatch")
    elif (
        output_checksums.get("checksum_version") != "pferi_v2_shard_output_checksums_v1"
        or set(output_checksums.get("files", {})) != set(SHARD_OUTPUT_HASH_FILES)
    ):
        _append(errors, "shard_output_checksums_schema_mismatch")
    elif any(
        output_checksums["files"].get(name) != sha256_file(output_dir / name)
        for name in SHARD_OUTPUT_HASH_FILES
    ):
        _append(errors, "shard_output_checksum_mismatch")

    expected_pair_ids = set(spec.pair_ids)
    canonical_ids = [row.get("pair_execution_id", "") for row in canonical]
    if len(canonical_ids) != len(set(canonical_ids)):
        _append(errors, "duplicate_canonical_pair_id")
    if set(canonical_ids) != expected_pair_ids:
        _append(errors, "canonical_pair_set_mismatch")
    if tuple(canonical_ids) != spec.pair_ids:
        _append(errors, "canonical_pair_order_mismatch")
    if len(canonical) != spec.pair_count:
        _append(errors, "canonical_row_count_mismatch")

    if len(directional) != 2 * spec.pair_count:
        _append(errors, "directional_row_count_mismatch")
    if not _directions_are_exact(directional, expected_pair_ids):
        _append(errors, "directional_pair_direction_mismatch")
    if len(provenance) != 2 * spec.pair_count:
        _append(errors, "provenance_row_count_mismatch")
    if not _directions_are_exact(provenance, expected_pair_ids):
        _append(errors, "provenance_pair_direction_mismatch")

    if not isinstance(binding, dict):
        _append(errors, "invalid_execution_binding")
        binding = {}
    if binding.get("binding_version") != "pferi_v2_shard_execution_binding_v1":
        _append(errors, "binding_version_mismatch")
    if binding.get("shard_id") != spec.shard_id:
        _append(errors, "binding_shard_id_mismatch")
    if binding.get("pair_manifest_sha256") != spec.manifest_sha256:
        _append(errors, "binding_manifest_hash_mismatch")
    fingerprint = binding.get("execution_fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        _append(errors, "missing_execution_fingerprint")
        fingerprint = None
    binding_artifacts = {key: binding.get(key) for key in BINDING_ARTIFACT_KEYS}
    if any(not isinstance(value, str) or not value for value in binding_artifacts.values()):
        _append(errors, "incomplete_execution_binding")
    elif fingerprint is not None:
        canonical_binding = json.dumps(
            binding_artifacts, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if hashlib.sha256(canonical_binding).hexdigest() != fingerprint:
            _append(errors, "execution_fingerprint_mismatch")

    return {
        "shard_id": spec.shard_id,
        "partition_role": spec.role,
        "status": "PASS" if not errors else "FAIL",
        "error_codes": errors,
        "missing_files": [],
        "expected_pair_count": spec.pair_count,
        "observed_canonical_count": len(canonical),
        "observed_directional_count": len(directional),
        "observed_provenance_count": len(provenance),
        "canonical_pair_ids": canonical_ids,
        "execution_fingerprint": fingerprint,
    }


def validate_full_frame(specs: Sequence[ShardSpec], shard_results_root: Path) -> dict[str, Any]:
    """Validate global completeness, uniqueness, and execution consistency."""
    global_errors: list[str] = []
    shard_reports: list[dict[str, Any]] = []
    observed_pair_ids: list[str] = []
    fingerprints: set[str] = set()
    declared_shards = {spec.shard_id for spec in specs}

    if shard_results_root.is_dir():
        unexpected = sorted(
            path.name
            for path in shard_results_root.iterdir()
            if path.is_dir()
            and path.name not in declared_shards
            and SHARD_ID_PATTERN.fullmatch(path.name)
        )
    else:
        unexpected = []

    for spec in specs:
        output_dir = shard_results_root / spec.output_dir_name
        if not output_dir.is_dir():
            report = {
                "shard_id": spec.shard_id,
                "partition_role": spec.role,
                "status": "FAIL",
                "error_codes": ["missing_shard_result"],
                "missing_files": list(REQUIRED_RESULT_FILES),
                "expected_pair_count": spec.pair_count,
                "observed_canonical_count": 0,
                "observed_directional_count": 0,
                "observed_provenance_count": 0,
                "canonical_pair_ids": [],
                "execution_fingerprint": None,
            }
        else:
            report = validate_shard(spec, output_dir)
        shard_reports.append(report)
        for code in report["error_codes"]:
            _append(global_errors, code)
        observed_pair_ids.extend(report.get("canonical_pair_ids", []))
        fingerprint = report.get("execution_fingerprint")
        if fingerprint:
            fingerprints.add(fingerprint)

    if unexpected:
        _append(global_errors, "unexpected_shard_result")
    expected_pair_ids = [pair_id for spec in specs for pair_id in spec.pair_ids]
    if Counter(observed_pair_ids) != Counter(expected_pair_ids):
        _append(global_errors, "global_pair_multiset_mismatch")
    if len(observed_pair_ids) != len(set(observed_pair_ids)):
        _append(global_errors, "duplicate_pair_across_shards")
    if len(fingerprints) > 1:
        _append(global_errors, "mixed_execution_fingerprint")
    if specs and not fingerprints:
        _append(global_errors, "missing_global_execution_fingerprint")

    return {
        "validation_version": "pferi_v2_full_frame_global_validation_v1",
        "created_at_utc": now_utc(),
        "status": "PASS" if not global_errors else "FAIL",
        "error_codes": global_errors,
        "expected_shard_count": len(specs),
        "observed_shard_count": sum(report["status"] == "PASS" for report in shard_reports),
        "expected_pair_count": len(expected_pair_ids),
        "observed_canonical_row_count": len(observed_pair_ids),
        "observed_unique_pair_count": len(set(observed_pair_ids)),
        "execution_fingerprints": sorted(fingerprints),
        "unexpected_result_directories": unexpected,
        "shard_reports": shard_reports,
        "claim_boundary": (
            "PASS establishes engineering completeness, schema integrity, pair coverage, and "
            "single-execution binding only; it does not establish matcher accuracy or biological validity."
        ),
    }


def validate_full_execution(specs: Sequence[ShardSpec], paths: ExecutionPaths) -> dict[str, Any]:
    """Validate shard payloads plus the immutable fresh-run control chain."""
    report = validate_full_frame(specs, paths.shard_results_root)
    errors = list(report["error_codes"])
    required = (
        "matcher_freeze_record.json",
        "environment_report.json",
        "full_frame_smoke_test.json",
        "smoke_gate_binding.json",
        "execution_image_inventory.json",
        "model_weight_inventory.json",
        "execution_state.json",
    )
    documents: dict[str, dict[str, Any]] = {}
    for name in required:
        path = paths.control_state_dir / name
        try:
            value = read_json(path)
            if not isinstance(value, dict):
                raise TypeError(name)
            documents[name] = value
        except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
            _append(errors, "missing_or_invalid_execution_control")

    if len(documents) == len(required):
        state = documents["execution_state.json"]
        freeze = documents["matcher_freeze_record.json"]
        environment = documents["environment_report.json"]
        smoke = documents["full_frame_smoke_test.json"]
        smoke_binding = documents["smoke_gate_binding.json"]
        image_inventory = documents["execution_image_inventory.json"]
        weight_inventory = documents["model_weight_inventory.json"]
        declared = [spec.shard_id for spec in specs]
        if state.get("status") != "RUN_COMPLETE":
            _append(errors, "execution_not_run_complete")
        if state.get("run_mode") != "fresh_full_inventory":
            _append(errors, "invalid_execution_run_mode")
        if state.get("declared_shards") != declared:
            _append(errors, "execution_declared_shards_mismatch")
        if state.get("inventory_sha256") != sha256_file(paths.inventory_path):
            _append(errors, "execution_inventory_hash_mismatch")
        fingerprints = report.get("execution_fingerprints", [])
        if len(fingerprints) != 1 or state.get("execution_fingerprint") != fingerprints[0]:
            _append(errors, "execution_control_fingerprint_mismatch")
        if not image_inventory.get("image_set_sha256") or not weight_inventory.get("weight_set_sha256"):
            _append(errors, "incomplete_execution_inventory")
        if not isinstance(weight_inventory.get("weights"), list) or not weight_inventory["weights"]:
            _append(errors, "empty_model_weight_inventory")
        if freeze.get("environment") != environment or not environment.get("cuda"):
            _append(errors, "freeze_environment_mismatch")
        if smoke.get("status") != "PASS":
            _append(errors, "smoke_gate_not_pass")
        if specs:
            expected_smoke = {
                "binding_version": "pferi_v2_smoke_gate_binding_v1",
                "pair_manifest_sha256": specs[0].manifest_sha256,
                "execution_fingerprint": fingerprints[0] if len(fingerprints) == 1 else None,
                "smoke_report_sha256": sha256_file(paths.control_state_dir / "full_frame_smoke_test.json"),
            }
            if any(smoke_binding.get(key) != value for key, value in expected_smoke.items()):
                _append(errors, "smoke_gate_binding_mismatch")
        if len(fingerprints) == 1:
            expected_artifacts = {
                "inventory_sha256": sha256_file(paths.inventory_path),
                "wrapper_sha256": sha256_file(paths.runner_path),
                "core_runner_sha256": sha256_file(paths.control_root / "local_match_runner_v2.py"),
                "protocol_sha256": sha256_file(paths.control_root / "local_match_execution_protocol_v2.json"),
                "freeze_record_sha256": sha256_file(paths.control_state_dir / "matcher_freeze_record.json"),
                "image_set_sha256": str(image_inventory.get("image_set_sha256", "")),
                "weight_set_sha256": str(weight_inventory.get("weight_set_sha256", "")),
            }
            canonical = json.dumps(expected_artifacts, sort_keys=True, separators=(",", ":")).encode()
            if hashlib.sha256(canonical).hexdigest() != fingerprints[0]:
                _append(errors, "execution_artifact_binding_mismatch")

    report["validation_version"] = "pferi_v2_full_execution_global_validation_v1"
    report["error_codes"] = errors
    report["status"] = "PASS" if not errors else "FAIL"
    report["execution_control_validated"] = not any(
        code in errors for code in (
            "missing_or_invalid_execution_control",
            "execution_not_run_complete",
            "invalid_execution_run_mode",
            "execution_control_fingerprint_mismatch",
            "execution_artifact_binding_mismatch",
            "smoke_gate_binding_mismatch",
        )
    )
    return report


def write_validation_outputs(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output_dir / "full_frame_validation.json", report)
    rows = [
        {
            "shard_id": item["shard_id"],
            "partition_role": item["partition_role"],
            "status": item["status"],
            "expected_pair_count": item["expected_pair_count"],
            "observed_canonical_count": item["observed_canonical_count"],
            "observed_directional_count": item["observed_directional_count"],
            "observed_provenance_count": item["observed_provenance_count"],
            "execution_fingerprint": item.get("execution_fingerprint") or "",
            "error_codes": "|".join(item["error_codes"]),
        }
        for item in report["shard_reports"]
    ]
    atomic_write_csv(
        output_dir / "per_shard_validation.csv",
        [
            "shard_id",
            "partition_role",
            "status",
            "expected_pair_count",
            "observed_canonical_count",
            "observed_directional_count",
            "observed_provenance_count",
            "execution_fingerprint",
            "error_codes",
        ],
        rows,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    paths = ExecutionPaths.from_roots(
        control_root=args.control_root,
        image_root=Path("."),
        result_root=args.result_root,
        export_root=Path("."),
    )
    specs = load_inventory(paths.inventory_path, paths.manifest_root)
    report = validate_full_execution(specs, paths)
    write_validation_outputs(report, args.output_dir or paths.validation_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
