#!/usr/bin/env python3
"""Run exactly the shards declared by the frozen inventory, with resume state."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from full_frame_execution_common import (
    CANONICAL_COLUMNS,
    COMPLETED_SHARD_STATUSES,
    DIRECTIONAL_COLUMNS,
    PROVENANCE_COLUMNS,
    SHARD_OUTPUT_HASH_FILES,
    ExecutionPaths,
    ShardSpec,
    atomic_write_json,
    load_inventory,
    read_csv,
    read_json,
    sha256_file,
)


CompletionChecker = Callable[[ShardSpec, Path], bool]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ExecutionPlan:
    declared_shards: tuple[str, ...]
    completed_shards: tuple[str, ...]
    pending_shards: tuple[str, ...]
    scheduled_shards: tuple[str, ...] = ()
    max_shards_per_run: int | None = None


def conservative_completion_check(
    spec: ShardSpec,
    output_dir: Path,
    *,
    expected_fingerprint: str | None = None,
) -> bool:
    """Return true only for a structurally complete shard with the expected manifest."""
    try:
        audit = read_json(output_dir / "run_audit.json")
        binding = read_json(output_dir / "shard_execution_binding.json")
        if audit.get("status") not in COMPLETED_SHARD_STATUSES:
            return False
        if audit.get("pair_manifest_sha256") != spec.manifest_sha256:
            return False
        if int(audit.get("pair_count", -1)) != spec.pair_count:
            return False
        if binding.get("binding_version") != "pferi_v2_shard_execution_binding_v1":
            return False
        if binding.get("shard_id") != spec.shard_id:
            return False
        if binding.get("pair_manifest_sha256") != spec.manifest_sha256:
            return False
        if not binding.get("execution_fingerprint"):
            return False
        if expected_fingerprint is not None and binding.get("execution_fingerprint") != expected_fingerprint:
            return False
        canonical, canonical_fields = read_csv(output_dir / "canonical_measurements.csv")
        directional, directional_fields = read_csv(output_dir / "directional_measurements.csv")
        provenance, provenance_fields = read_csv(output_dir / "region_provenance.csv")
        runtime_errors = read_json(output_dir / "runtime_errors.json")
        checksums = read_json(output_dir / "shard_output_checksums.json")
        if checksums.get("checksum_version") != "pferi_v2_shard_output_checksums_v1":
            return False
        if set(checksums.get("files", {})) != set(SHARD_OUTPUT_HASH_FILES):
            return False
        if any(
            checksums["files"].get(name) != sha256_file(output_dir / name)
            for name in SHARD_OUTPUT_HASH_FILES
        ):
            return False
        expected_pairs = set(spec.pair_ids)
        directional_keys = {
            (row["pair_execution_id"], row["direction"]) for row in directional
        }
        provenance_keys = {
            (row["pair_execution_id"], row["direction"]) for row in provenance
        }
        expected_keys = {
            (pair_id, direction)
            for pair_id in expected_pairs
            for direction in ("A_to_B", "B_to_A")
        }
        return (
            canonical_fields == CANONICAL_COLUMNS
            and directional_fields == DIRECTIONAL_COLUMNS
            and provenance_fields == PROVENANCE_COLUMNS
            and isinstance(runtime_errors, list)
            and len(canonical) == spec.pair_count
            and len(directional) == 2 * spec.pair_count
            and len(provenance) == 2 * spec.pair_count
            and [row["pair_execution_id"] for row in canonical] == list(spec.pair_ids)
            and directional_keys == expected_keys
            and provenance_keys == expected_keys
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _binding_matches(spec: ShardSpec, output_dir: Path, expected_fingerprint: str) -> bool:
    try:
        binding = read_json(output_dir / "shard_execution_binding.json")
        return (
            isinstance(binding, dict)
            and binding.get("binding_version") == "pferi_v2_shard_execution_binding_v1"
            and binding.get("shard_id") == spec.shard_id
            and binding.get("pair_manifest_sha256") == spec.manifest_sha256
            and binding.get("execution_fingerprint") == expected_fingerprint
        )
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return False


def safe_resume_check(spec: ShardSpec, output_dir: Path, expected_fingerprint: str) -> bool:
    """Accept only checkpoints already bound to the current execution."""
    if not output_dir.exists():
        return True
    if not output_dir.is_dir() or output_dir.is_symlink():
        return False
    members = list(output_dir.iterdir())
    if not members:
        return True
    if not _binding_matches(spec, output_dir, expected_fingerprint):
        return False
    checkpoint_dir = output_dir / "pair_checkpoints"
    if not checkpoint_dir.exists():
        return True
    if not checkpoint_dir.is_dir() or checkpoint_dir.is_symlink():
        return False
    expected_pairs = set(spec.pair_ids)
    for checkpoint in checkpoint_dir.iterdir():
        if not checkpoint.is_file() or checkpoint.suffix != ".json":
            return False
        if checkpoint.stem not in expected_pairs:
            return False
        try:
            payload = read_json(checkpoint)
            directional = payload.get("directional")
            provenance = payload.get("provenance")
            if (
                payload.get("pair_execution_id") != checkpoint.stem
                or not isinstance(directional, list)
                or len(directional) != 2
                or {row.get("direction") for row in directional} != {"A_to_B", "B_to_A"}
                or not isinstance(payload.get("canonical"), dict)
                or not isinstance(provenance, list)
                or len(provenance) != 2
                or not isinstance(payload.get("runtime_errors"), list)
            ):
                return False
        except (AttributeError, json.JSONDecodeError, TypeError, ValueError):
            return False
    return True


def build_image_inventory(specs: Sequence[ShardSpec], image_root: Path) -> dict[str, Any]:
    """Hash every inventory-referenced input once, before any model invocation."""
    filenames: set[str] = set()
    for spec in specs:
        rows, _ = read_csv(spec.manifest_path)
        for row in rows:
            filenames.add(row["left_asset_filename"])
            filenames.add(row["right_asset_filename"])
    records = []
    for filename in sorted(filenames):
        path = image_root / filename
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"referenced image missing or not a regular file: {path}")
        records.append(
            {
                "asset_filename": filename,
                "size_bytes": path.stat().st_size,
                "content_sha256": sha256_file(path),
            }
        )
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "inventory_version": "pferi_v2_execution_image_inventory_v1",
        "referenced_image_count": len(records),
        "image_set_sha256": hashlib.sha256(canonical).hexdigest(),
        "images": records,
    }


def control_artifact_hashes(paths: ExecutionPaths) -> dict[str, str]:
    candidates = (
        paths.inventory_path,
        paths.runner_path,
        paths.control_root / "local_match_runner_v2.py",
        paths.control_root / "local_match_execution_protocol_v2.json",
    )
    return {
        path.name: sha256_file(path)
        for path in candidates
        if path.is_file() and not path.is_symlink()
    }


def validate_result_root_compatibility(
    paths: ExecutionPaths,
    specs: Sequence[ShardSpec],
    image_inventory: dict[str, Any],
) -> None:
    state_path = paths.control_state_dir / "execution_state.json"
    stored_image_path = paths.control_state_dir / "execution_image_inventory.json"
    if not state_path.is_file():
        has_orphaned_control = any(
            path.name != "execution_image_inventory.json"
            for path in paths.control_state_dir.iterdir()
        )
        has_orphaned_shards = any(paths.shard_results_root.iterdir())
        if has_orphaned_control or has_orphaned_shards:
            raise RuntimeError(
                "incompatible RESULT_ROOT: persisted outputs exist without a fresh-run execution state"
            )
        return
    try:
        state = read_state(state_path)
        expected_shards = [spec.shard_id for spec in specs]
        if state.get("run_mode") != "fresh_full_inventory":
            raise RuntimeError("run mode mismatch")
        if state.get("inventory_sha256") != sha256_file(paths.inventory_path):
            raise RuntimeError("inventory hash mismatch")
        if state.get("declared_shards") != expected_shards:
            raise RuntimeError("declared shard order mismatch")
        if state.get("control_artifact_sha256") != control_artifact_hashes(paths):
            raise RuntimeError("control artifact hash mismatch")
        if stored_image_path.is_file():
            stored_image = read_json(stored_image_path)
            if stored_image.get("image_set_sha256") != image_inventory.get("image_set_sha256"):
                raise RuntimeError("image inventory hash mismatch")
    except (AttributeError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as error:
        raise RuntimeError(f"incompatible RESULT_ROOT: {error}") from error


def validate_freeze_record(paths: ExecutionPaths) -> dict[str, Any]:
    freeze_path = paths.control_state_dir / "matcher_freeze_record.json"
    record = read_json(freeze_path)
    if not isinstance(record, dict):
        raise RuntimeError("matcher freeze record is not a JSON object")
    expected = {
        "contract_sha256": sha256_file(paths.control_root / "local_match_execution_protocol_v2.json"),
        "runner_sha256": sha256_file(paths.control_root / "local_match_runner_v2.py"),
        "full_frame_wrapper_sha256": sha256_file(paths.runner_path),
    }
    mismatches = [key for key, value in expected.items() if record.get(key) != value]
    if mismatches:
        raise RuntimeError(f"stale freeze record; hash mismatch for: {','.join(mismatches)}")
    if not isinstance(record.get("weight_sha256"), dict) or not record["weight_sha256"]:
        raise RuntimeError("freeze record lacks model weight checksums")
    environment = record.get("environment")
    if not isinstance(environment, dict) or not environment.get("cuda"):
        raise RuntimeError("GPU/CUDA was not recorded by freeze; refusing unintended CPU execution")
    import torch
    import torchvision

    current_environment = {
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "cuda": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "lightglue_version": getattr(__import__("lightglue"), "__version__", "unknown"),
    }
    environment_mismatches = [
        key for key, value in current_environment.items() if environment.get(key) != value
    ]
    if environment_mismatches:
        raise RuntimeError(
            "current runtime differs from frozen environment: " + ",".join(environment_mismatches)
        )
    return record


def build_model_weight_inventory(checkpoint_root: Path) -> dict[str, Any]:
    files = sorted(path for path in checkpoint_root.glob("*") if path.is_file() and not path.is_symlink())
    if not files:
        raise RuntimeError(f"model checkpoint cache is empty: {checkpoint_root}")
    records = [
        {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "content_sha256": sha256_file(path),
        }
        for path in files
    ]
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "inventory_version": "pferi_v2_model_weight_inventory_v1",
        "weight_file_count": len(records),
        "weight_set_sha256": hashlib.sha256(canonical).hexdigest(),
        "weights": records,
    }


def torch_checkpoint_root() -> Path:
    import torch

    return Path(torch.hub.get_dir()) / "checkpoints"


def write_model_weight_inventory(paths: ExecutionPaths) -> None:
    atomic_write_json(
        paths.control_state_dir / "model_weight_inventory.json",
        build_model_weight_inventory(torch_checkpoint_root()),
    )


def verify_model_weight_inventory(paths: ExecutionPaths) -> bool:
    try:
        stored = read_json(paths.control_state_dir / "model_weight_inventory.json")
        if not isinstance(stored, dict) or not isinstance(stored.get("weights"), list):
            return False
        checkpoint_root = torch_checkpoint_root()
        for item in stored["weights"]:
            path = checkpoint_root / item["filename"]
            if (
                not path.is_file()
                or path.is_symlink()
                or path.stat().st_size != int(item["size_bytes"])
                or sha256_file(path) != item["content_sha256"]
            ):
                return False
        canonical = json.dumps(stored["weights"], sort_keys=True, separators=(",", ":")).encode("utf-8")
        return stored.get("weight_set_sha256") == hashlib.sha256(canonical).hexdigest()
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def execution_artifacts(paths: ExecutionPaths) -> dict[str, str]:
    image_inventory = read_json(paths.control_state_dir / "execution_image_inventory.json")
    weight_inventory = read_json(paths.control_state_dir / "model_weight_inventory.json")
    if not isinstance(image_inventory, dict) or not image_inventory.get("image_set_sha256"):
        raise RuntimeError("execution image inventory is missing or invalid")
    if not isinstance(weight_inventory, dict) or not weight_inventory.get("weight_set_sha256"):
        raise RuntimeError("model weight inventory is missing or invalid")
    return {
        "inventory_sha256": sha256_file(paths.inventory_path),
        "wrapper_sha256": sha256_file(paths.runner_path),
        "core_runner_sha256": sha256_file(paths.control_root / "local_match_runner_v2.py"),
        "protocol_sha256": sha256_file(paths.control_root / "local_match_execution_protocol_v2.json"),
        "freeze_record_sha256": sha256_file(paths.control_state_dir / "matcher_freeze_record.json"),
        "image_set_sha256": str(image_inventory["image_set_sha256"]),
        "weight_set_sha256": str(weight_inventory["weight_set_sha256"]),
    }


def execution_fingerprint(paths: ExecutionPaths) -> str:
    artifacts = execution_artifacts(paths)
    canonical = json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_execution_binding(paths: ExecutionPaths, spec: ShardSpec) -> dict[str, object]:
    """Bind a shard to the exact control artifacts used for this invocation."""
    artifacts = execution_artifacts(paths)
    return {
        "binding_version": "pferi_v2_shard_execution_binding_v1",
        "shard_id": spec.shard_id,
        "pair_manifest_sha256": spec.manifest_sha256,
        "execution_fingerprint": execution_fingerprint(paths),
        **artifacts,
    }


def write_execution_binding(paths: ExecutionPaths, spec: ShardSpec) -> None:
    atomic_write_json(
        paths.shard_results_root / spec.output_dir_name / "shard_execution_binding.json",
        build_execution_binding(paths, spec),
    )


def write_shard_output_checksums(output_dir: Path) -> None:
    atomic_write_json(
        output_dir / "shard_output_checksums.json",
        {
            "checksum_version": "pferi_v2_shard_output_checksums_v1",
            "files": {
                name: sha256_file(output_dir / name)
                for name in SHARD_OUTPUT_HASH_FILES
            },
        },
    )


def smoke_binding_is_valid(paths: ExecutionPaths, spec: ShardSpec) -> bool:
    smoke_path = paths.control_state_dir / "full_frame_smoke_test.json"
    binding_path = paths.control_state_dir / "smoke_gate_binding.json"
    try:
        smoke = read_json(smoke_path)
        binding = read_json(binding_path)
        return verify_model_weight_inventory(paths) and (
            smoke.get("status") == "PASS"
            and binding.get("binding_version") == "pferi_v2_smoke_gate_binding_v1"
            and binding.get("pair_manifest_sha256") == spec.manifest_sha256
            and binding.get("execution_fingerprint") == execution_fingerprint(paths)
            and binding.get("smoke_report_sha256") == sha256_file(smoke_path)
        )
    except (FileNotFoundError, json.JSONDecodeError, RuntimeError, TypeError, ValueError):
        return False


def write_smoke_binding(paths: ExecutionPaths, spec: ShardSpec) -> None:
    smoke_path = paths.control_state_dir / "full_frame_smoke_test.json"
    if read_json(smoke_path).get("status") != "PASS":
        raise RuntimeError("cannot bind a smoke report that did not pass")
    atomic_write_json(
        paths.control_state_dir / "smoke_gate_binding.json",
        {
            "binding_version": "pferi_v2_smoke_gate_binding_v1",
            "pair_manifest_sha256": spec.manifest_sha256,
            "execution_fingerprint": execution_fingerprint(paths),
            "smoke_report_sha256": sha256_file(smoke_path),
        },
    )


def build_execution_plan(
    specs: Sequence[ShardSpec],
    shard_results_root: Path,
    *,
    completion_checker: CompletionChecker = conservative_completion_check,
    max_shards_per_run: int | None = None,
) -> ExecutionPlan:
    if max_shards_per_run is not None and max_shards_per_run <= 0:
        raise ValueError("max_shards_per_run must be a positive integer")
    completed: list[str] = []
    pending: list[str] = []
    for spec in specs:
        output_dir = shard_results_root / spec.output_dir_name
        if completion_checker(spec, output_dir):
            completed.append(spec.shard_id)
        else:
            pending.append(spec.shard_id)
    scheduled = pending if max_shards_per_run is None else pending[:max_shards_per_run]
    return ExecutionPlan(
        declared_shards=tuple(spec.shard_id for spec in specs),
        completed_shards=tuple(completed),
        pending_shards=tuple(pending),
        scheduled_shards=tuple(scheduled),
        max_shards_per_run=max_shards_per_run,
    )


def run_status(plan: ExecutionPlan) -> str:
    if plan.pending_shards:
        return "BATCH_COMPLETE"
    return "RUN_COMPLETE"


def shard_command(
    *,
    python_executable: str,
    paths: ExecutionPaths,
    spec: ShardSpec,
) -> list[str]:
    return [
        python_executable,
        str(paths.runner_path),
        "run-shard",
        "--pair-manifest",
        str(spec.manifest_path),
        "--image-dir",
        str(paths.image_root),
        "--control-dir",
        str(paths.control_state_dir),
        "--output-dir",
        str(paths.shard_results_root / spec.output_dir_name),
    ]


def write_state(path: Path, state: dict[str, object]) -> None:
    atomic_write_json(path, state)


def read_state(path: Path) -> dict[str, object]:
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError("execution state must be a JSON object")
    return value


def _run_command(command: Sequence[str], log_path: Path, *, cwd: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    with log_path.open("w", encoding="utf-8") as log:
        if process.stdout is not None:
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
    return int(process.wait())


def _plan_state_fields(plan: ExecutionPlan) -> dict[str, object]:
    return {
        "max_shards_per_run": plan.max_shards_per_run,
        "declared_shards": list(plan.declared_shards),
        "completed_shards": list(plan.completed_shards),
        "pending_shards": list(plan.pending_shards),
        "scheduled_shards": list(plan.scheduled_shards),
    }


def execute(
    *,
    paths: ExecutionPaths,
    python_executable: str,
    dry_run: bool,
    max_shards_per_run: int = 1,
) -> dict[str, object]:
    specs = load_inventory(paths.inventory_path, paths.manifest_root)
    if max_shards_per_run <= 0:
        raise ValueError("max_shards_per_run must be a positive integer")
    if not paths.runner_path.is_file():
        raise FileNotFoundError(f"runner missing: {paths.runner_path}")
    if not paths.image_root.is_dir():
        raise FileNotFoundError(f"image directory missing: {paths.image_root}")
    paths.control_state_dir.mkdir(parents=True, exist_ok=True)
    paths.shard_results_root.mkdir(parents=True, exist_ok=True)
    state_path = paths.control_state_dir / "execution_state.json"
    logs_dir = paths.control_state_dir / "logs"

    image_inventory = build_image_inventory(specs, paths.image_root)
    validate_result_root_compatibility(paths, specs, image_inventory)
    atomic_write_json(paths.control_state_dir / "execution_image_inventory.json", image_inventory)

    freeze_path = paths.control_state_dir / "matcher_freeze_record.json"
    if dry_run:
        plan = build_execution_plan(
            specs,
            paths.shard_results_root,
            max_shards_per_run=max_shards_per_run,
            completion_checker=conservative_completion_check,
        )
        state = {
            "state_version": "pferi_v2_full_frame_fresh_run_state_v1",
            "run_mode": "fresh_full_inventory",
            "status": "DRY_RUN_PASS",
            "project_status_preview": run_status(plan),
            "completion_assurance": "structural_only_dry_run_no_model_loaded",
            "updated_at_utc": now_utc(),
            "inventory_path": str(paths.inventory_path),
            "inventory_sha256": sha256_file(paths.inventory_path),
            "control_artifact_sha256": control_artifact_hashes(paths),
            "declared_shards": [spec.shard_id for spec in specs],
            "declared_shard_count": len(specs),
            "declared_pair_count": sum(spec.pair_count for spec in specs),
            "image_set_sha256": image_inventory["image_set_sha256"],
            "failed_shards": [],
            **_plan_state_fields(plan),
        }
        write_state(state_path, state)
        return state

    if not freeze_path.is_file():
        command = [
            python_executable,
            str(paths.runner_path),
            "freeze",
            "--control-dir",
            str(paths.control_state_dir),
        ]
        if _run_command(command, logs_dir / "freeze.log", cwd=paths.control_root) != 0:
            raise RuntimeError("matcher freeze failed; see freeze.log")
    if freeze_path.is_file():
        validate_freeze_record(paths)
    smoke_spec = next((spec for spec in specs if spec.pair_count >= 5), None)
    if smoke_spec is None:
        raise RuntimeError("inventory has no shard with at least five pairs for the mandatory smoke gate")
    if smoke_spec is not None and not smoke_binding_is_valid(paths, smoke_spec):
        command = [
            python_executable,
            str(paths.runner_path),
            "smoke",
            "--pair-manifest",
            str(smoke_spec.manifest_path),
            "--image-dir",
            str(paths.image_root),
            "--control-dir",
            str(paths.control_state_dir),
        ]
        if _run_command(command, logs_dir / "smoke.log", cwd=paths.control_root) != 0:
            raise RuntimeError("mandatory smoke gate failed; see smoke.log")
        write_model_weight_inventory(paths)
        write_smoke_binding(paths, smoke_spec)

    if not smoke_binding_is_valid(paths, smoke_spec):
        raise RuntimeError("mandatory smoke gate is not valid for this fresh execution")
    expected_fingerprint = execution_fingerprint(paths)
    current_completion_checker: CompletionChecker = lambda spec, output_dir: (
        conservative_completion_check(
            spec, output_dir, expected_fingerprint=expected_fingerprint
        )
    )
    plan = build_execution_plan(
        specs,
        paths.shard_results_root,
        max_shards_per_run=max_shards_per_run,
        completion_checker=current_completion_checker,
    )

    specs_by_id = {spec.shard_id: spec for spec in specs}
    stale_shards = []
    for shard_id in plan.pending_shards:
        spec = specs_by_id[shard_id]
        output_dir = paths.shard_results_root / spec.output_dir_name
        has_output = output_dir.exists() and (
            not output_dir.is_dir() or any(output_dir.iterdir())
        )
        if has_output and not safe_resume_check(spec, output_dir, expected_fingerprint):
            stale_shards.append(shard_id)
    weight_inventory_path = paths.control_state_dir / "model_weight_inventory.json"
    stored_weight_inventory = read_json(weight_inventory_path) if weight_inventory_path.is_file() else {}
    if not isinstance(stored_weight_inventory, dict):
        stored_weight_inventory = {}
    state: dict[str, object] = {
        "state_version": "pferi_v2_full_frame_fresh_run_state_v1",
        "run_mode": "fresh_full_inventory",
        "status": "FAIL" if stale_shards else "IN_PROGRESS",
        "updated_at_utc": now_utc(),
        "inventory_path": str(paths.inventory_path),
        "inventory_sha256": sha256_file(paths.inventory_path),
        "control_artifact_sha256": control_artifact_hashes(paths),
        "runner_path": str(paths.runner_path),
        "runner_sha256": sha256_file(paths.runner_path),
        "execution_fingerprint": expected_fingerprint,
        "image_set_sha256": image_inventory["image_set_sha256"],
        "weight_set_sha256": stored_weight_inventory.get("weight_set_sha256"),
        "control_root": str(paths.control_root),
        "image_root": str(paths.image_root),
        "result_root": str(paths.result_root),
        "declared_shards": [spec.shard_id for spec in specs],
        "declared_shard_count": len(specs),
        "declared_pair_count": sum(spec.pair_count for spec in specs),
        "failed_shards": list(stale_shards),
        "stale_or_unbound_shards": list(stale_shards),
        **_plan_state_fields(plan),
    }
    write_state(state_path, state)
    if stale_shards:
        raise RuntimeError(
            "stale or unbound shard output requires a new RESULT_ROOT or explicit clean rerun: "
            + ",".join(stale_shards)
        )

    launched_shards: list[str] = []
    for shard_id in plan.scheduled_shards:
        spec = specs_by_id[shard_id]
        output_dir = paths.shard_results_root / spec.output_dir_name
        output_dir.mkdir(parents=True, exist_ok=True)
        write_execution_binding(paths, spec)
        command = shard_command(
            python_executable=python_executable,
            paths=paths,
            spec=spec,
        )
        return_code = _run_command(
            command,
            logs_dir / f"{shard_id}.log",
            cwd=paths.control_root,
        )
        if return_code == 0:
            write_shard_output_checksums(output_dir)
        if return_code != 0 or not conservative_completion_check(
            spec,
            output_dir,
            expected_fingerprint=expected_fingerprint,
        ):
            state["failed_shards"] = [*state["failed_shards"], shard_id]
            state["status"] = "FAIL"
            state["updated_at_utc"] = now_utc()
            write_state(state_path, state)
            raise RuntimeError(f"shard failed validation: {shard_id}")
        launched_shards.append(shard_id)
        state["completed_shards"] = [*state["completed_shards"], shard_id]
        state["pending_shards"] = [item for item in state["pending_shards"] if item != shard_id]
        state["updated_at_utc"] = now_utc()
        write_state(state_path, state)

    final_plan = build_execution_plan(
        specs,
        paths.shard_results_root,
        max_shards_per_run=max_shards_per_run,
        completion_checker=current_completion_checker,
    )
    state.update(_plan_state_fields(final_plan))
    state["launched_shards_this_run"] = launched_shards
    state["status"] = run_status(final_plan)
    state["updated_at_utc"] = now_utc()
    write_state(state_path, state)
    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument(
        "--max-shards-per-run",
        type=int,
        default=1,
        help="maximum pending eligible shards launched in this invocation",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = ExecutionPaths.from_roots(
        control_root=args.control_root,
        image_root=args.image_root,
        result_root=args.result_root,
        export_root=args.export_root,
    )
    state = execute(
        paths=paths,
        python_executable=args.python_executable,
        dry_run=args.dry_run,
        max_shards_per_run=args.max_shards_per_run,
    )
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0 if state["status"] in {
        "DRY_RUN_PASS",
        "BATCH_COMPLETE",
        "RUN_COMPLETE",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
