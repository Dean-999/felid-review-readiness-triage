#!/usr/bin/env python3
"""Deterministically merge validated PF-ERI shard outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from full_frame_execution_common import (
    CANONICAL_COLUMNS,
    DIRECTIONAL_COLUMNS,
    PROVENANCE_COLUMNS,
    ExecutionPaths,
    ShardSpec,
    atomic_write_csv,
    atomic_write_json,
    load_inventory,
    read_csv,
    read_json,
    sha256_file,
)
from validate_full_frame_results import validate_full_frame


MERGE_PREFIX_COLUMNS = ["shard_id", "partition_role"]
DIRECTION_ORDER = {"A_to_B": 0, "B_to_A": 1}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validation_digest(report: dict[str, Any]) -> str:
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ordered_rows(
    rows: list[dict[str, str]],
    pair_ids: tuple[str, ...],
    *,
    directional: bool,
) -> list[dict[str, str]]:
    pair_order = {pair_id: index for index, pair_id in enumerate(pair_ids)}
    if directional:
        return sorted(
            rows,
            key=lambda row: (
                pair_order[row["pair_execution_id"]],
                DIRECTION_ORDER[row["direction"]],
            ),
        )
    return sorted(rows, key=lambda row: pair_order[row["pair_execution_id"]])


def _with_partition(row: dict[str, Any], spec: ShardSpec) -> dict[str, Any]:
    return {"shard_id": spec.shard_id, "partition_role": spec.role, **row}


def merge_full_frame(
    specs: Sequence[ShardSpec],
    shard_results_root: Path,
    merged_root: Path,
    validation_report: dict[str, Any],
) -> dict[str, Any]:
    """Merge only a currently valid, single-bound execution in declared order."""
    if validation_report.get("status") != "PASS":
        raise RuntimeError("merge requires global validation PASS")
    current_validation = validate_full_frame(specs, shard_results_root)
    if current_validation.get("status") != "PASS":
        raise RuntimeError(
            "merge requires global validation PASS against current files: "
            + ",".join(current_validation.get("error_codes", []))
        )
    if (
        validation_report.get("expected_pair_count") != current_validation.get("expected_pair_count")
        or validation_report.get("execution_fingerprints")
        != current_validation.get("execution_fingerprints")
    ):
        raise RuntimeError("provided validation report is stale or belongs to another execution")

    canonical_merged: list[dict[str, Any]] = []
    directional_merged: list[dict[str, Any]] = []
    provenance_merged: list[dict[str, Any]] = []
    runtime_errors_merged: list[dict[str, Any]] = []
    shard_audit_rows: list[dict[str, Any]] = []

    for spec in specs:
        shard_dir = shard_results_root / spec.output_dir_name
        canonical, _ = read_csv(shard_dir / "canonical_measurements.csv")
        directional, _ = read_csv(shard_dir / "directional_measurements.csv")
        provenance, _ = read_csv(shard_dir / "region_provenance.csv")
        runtime_errors = read_json(shard_dir / "runtime_errors.json")
        run_audit = read_json(shard_dir / "run_audit.json")
        binding = read_json(shard_dir / "shard_execution_binding.json")

        canonical_merged.extend(
            _with_partition(row, spec)
            for row in _ordered_rows(canonical, spec.pair_ids, directional=False)
        )
        directional_merged.extend(
            _with_partition(row, spec)
            for row in _ordered_rows(directional, spec.pair_ids, directional=True)
        )
        provenance_merged.extend(
            _with_partition(row, spec)
            for row in _ordered_rows(provenance, spec.pair_ids, directional=True)
        )
        runtime_errors_merged.extend(
            _with_partition(item, spec) for item in runtime_errors if isinstance(item, dict)
        )
        shard_audit_rows.append({
            "shard_id": spec.shard_id,
            "partition_role": spec.role,
            "manifest_sha256": spec.manifest_sha256,
            "execution_fingerprint": binding.get("execution_fingerprint", ""),
            "status": run_audit.get("status", ""),
            "pair_count": run_audit.get("pair_count", ""),
            "successful_pair_count": run_audit.get("successful_pair_count", ""),
            "valid_measurement_rate": run_audit.get("valid_measurement_rate", ""),
            "failure_distribution_json": json.dumps(
                run_audit.get("failure_distribution", {}), sort_keys=True, separators=(",", ":")
            ),
        })

    merged_root.mkdir(parents=True, exist_ok=True)
    canonical_path = merged_root / "canonical_measurements.csv"
    directional_path = merged_root / "directional_measurements.csv"
    provenance_path = merged_root / "region_provenance.csv"
    runtime_errors_path = merged_root / "runtime_errors.json"
    shard_audit_index_path = merged_root / "shard_audit_index.csv"
    atomic_write_csv(
        canonical_path,
        MERGE_PREFIX_COLUMNS + CANONICAL_COLUMNS,
        canonical_merged,
    )
    atomic_write_csv(
        directional_path,
        MERGE_PREFIX_COLUMNS + DIRECTIONAL_COLUMNS,
        directional_merged,
    )
    atomic_write_csv(
        provenance_path,
        MERGE_PREFIX_COLUMNS + PROVENANCE_COLUMNS,
        provenance_merged,
    )
    atomic_write_json(runtime_errors_path, runtime_errors_merged)
    atomic_write_csv(
        shard_audit_index_path,
        [
            "shard_id",
            "partition_role",
            "manifest_sha256",
            "execution_fingerprint",
            "status",
            "pair_count",
            "successful_pair_count",
            "valid_measurement_rate",
            "failure_distribution_json",
        ],
        shard_audit_rows,
    )

    audit = {
        "merge_version": "pferi_v2_full_frame_merge_v1",
        "created_at_utc": now_utc(),
        "status": "PASS",
        "source_validation_sha256": _validation_digest(current_validation),
        "execution_fingerprints": current_validation["execution_fingerprints"],
        "shard_count": len(specs),
        "canonical_row_count": len(canonical_merged),
        "directional_row_count": len(directional_merged),
        "provenance_row_count": len(provenance_merged),
        "runtime_error_count": len(runtime_errors_merged),
        "shard_audit_row_count": len(shard_audit_rows),
        "output_sha256": {
            canonical_path.name: sha256_file(canonical_path),
            directional_path.name: sha256_file(directional_path),
            provenance_path.name: sha256_file(provenance_path),
            runtime_errors_path.name: sha256_file(runtime_errors_path),
            shard_audit_index_path.name: sha256_file(shard_audit_index_path),
        },
    }
    atomic_write_json(merged_root / "merge_audit.json", audit)
    return audit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    paths = ExecutionPaths.from_roots(
        control_root=args.control_root,
        image_root=Path("."),
        result_root=args.result_root,
        export_root=Path("."),
    )
    specs = load_inventory(paths.inventory_path, paths.manifest_root)
    validation_path = args.validation_report or paths.validation_root / "full_frame_validation.json"
    audit = merge_full_frame(
        specs,
        paths.shard_results_root,
        args.output_dir or paths.merged_root,
        read_json(validation_path),
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
