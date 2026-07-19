#!/usr/bin/env python3
"""Shared immutable contracts for PF-ERI full-frame execution tooling."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


PAIR_COLUMNS = ["pair_execution_id", "left_asset_filename", "right_asset_filename"]
DIRECTIONAL_COLUMNS = [
    "pair_execution_id",
    "direction",
    "source_asset_filename",
    "target_asset_filename",
    "local_match_coverage_fraction",
    "value_status",
    "failure_code",
    "source_region_area_px",
    "target_region_area_px",
    "inlier_count",
    "runtime_seconds",
    "manual_rescue_count",
]
CANONICAL_COLUMNS = [
    "pair_execution_id",
    "local_match_coverage_fraction",
    "value_status",
    "failure_code",
    "a_to_b_coverage_fraction",
    "b_to_a_coverage_fraction",
    "pair_runtime_seconds",
    "manual_rescue_count",
]
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
COMPLETED_SHARD_STATUSES = {"PASS", "PARTIAL"}
SHARD_OUTPUT_HASH_FILES = (
    "canonical_measurements.csv",
    "directional_measurements.csv",
    "region_provenance.csv",
    "runtime_errors.json",
    "run_audit.json",
    "shard_execution_binding.json",
)
SHARD_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*_shard_[0-9]{3,}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def _atomic_replace(path: Path, writer: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, value: Any) -> None:
    def writer(handle: Any) -> None:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")

    _atomic_replace(path, writer)


def atomic_write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    def writer(handle: Any) -> None:
        csv_writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        csv_writer.writeheader()
        csv_writer.writerows(rows)

    _atomic_replace(path, writer)


@dataclass(frozen=True)
class ExecutionPaths:
    control_root: Path
    image_root: Path
    result_root: Path
    export_root: Path

    @classmethod
    def from_roots(
        cls,
        *,
        control_root: Path,
        image_root: Path,
        result_root: Path,
        export_root: Path,
    ) -> "ExecutionPaths":
        return cls(
            control_root=Path(control_root),
            image_root=Path(image_root),
            result_root=Path(result_root),
            export_root=Path(export_root),
        )

    @property
    def inventory_path(self) -> Path:
        return self.control_root / "shard_inventory.json"

    @property
    def manifest_root(self) -> Path:
        return self.control_root / "public_pair_manifests"

    @property
    def runner_path(self) -> Path:
        return self.control_root / "full_frame_local_match_runner.py"

    @property
    def control_state_dir(self) -> Path:
        return self.result_root / "_control"

    @property
    def shard_results_root(self) -> Path:
        return self.result_root / "shards"

    @property
    def validation_root(self) -> Path:
        return self.result_root / "validation"

    @property
    def merged_root(self) -> Path:
        return self.result_root / "merged"

    @property
    def final_export_zip(self) -> Path:
        return self.export_root / "PF_ERI_FINAL_EXPORT.zip"


@dataclass(frozen=True)
class ShardSpec:
    shard_id: str
    role: str
    manifest_path: Path
    pair_count: int
    manifest_sha256: str
    pair_ids: tuple[str, ...]

    @property
    def output_dir_name(self) -> str:
        return self.shard_id


def _validate_asset_filename(value: str, *, shard_id: str) -> None:
    path = Path(value)
    if not value or path.name != value or value in {".", ".."}:
        raise ValueError(f"unsafe asset filename in {shard_id}: {value!r}")


def load_inventory(inventory_path: Path, manifest_root: Path) -> list[ShardSpec]:
    inventory = read_json(inventory_path)
    if not isinstance(inventory, list) or not inventory:
        raise ValueError("shard inventory must be a nonempty JSON list")
    seen_shards: set[str] = set()
    seen_pairs: set[str] = set()
    seen_unordered_image_pairs: set[tuple[str, str]] = set()
    specs: list[ShardSpec] = []
    for entry in inventory:
        if not isinstance(entry, dict):
            raise ValueError("shard inventory entry must be an object")
        required = {"shard_id", "pair_count", "manifest_sha256"}
        if not required.issubset(entry):
            raise ValueError(f"shard inventory entry lacks fields: {sorted(required - set(entry))}")
        shard_id = str(entry["shard_id"])
        if shard_id in seen_shards:
            raise ValueError(f"duplicate shard_id: {shard_id}")
        if not SHARD_ID_PATTERN.fullmatch(shard_id):
            raise ValueError(f"invalid shard_id: {shard_id}")
        seen_shards.add(shard_id)
        manifest_path = manifest_root / f"{shard_id}.csv"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"inventory manifest is missing: {manifest_path}")
        expected_hash = str(entry["manifest_sha256"])
        actual_hash = sha256_file(manifest_path)
        if actual_hash != expected_hash:
            raise ValueError(
                f"manifest SHA256 mismatch for {shard_id}: expected {expected_hash}, found {actual_hash}"
            )
        rows, fields = read_csv(manifest_path)
        if fields != PAIR_COLUMNS:
            raise ValueError(f"manifest schema mismatch for {shard_id}: {fields}")
        expected_count = int(entry["pair_count"])
        if len(rows) != expected_count or expected_count <= 0:
            raise ValueError(
                f"manifest row count mismatch for {shard_id}: expected {expected_count}, found {len(rows)}"
            )
        pair_ids = tuple(row["pair_execution_id"] for row in rows)
        if any(not pair_id for pair_id in pair_ids) or len(pair_ids) != len(set(pair_ids)):
            raise ValueError(f"blank or duplicate pair_execution_id inside {shard_id}")
        overlap = seen_pairs.intersection(pair_ids)
        if overlap:
            raise ValueError(f"pair_execution_id occurs in multiple shards: {sorted(overlap)[:3]}")
        seen_pairs.update(pair_ids)
        for row in rows:
            _validate_asset_filename(row["left_asset_filename"], shard_id=shard_id)
            _validate_asset_filename(row["right_asset_filename"], shard_id=shard_id)
            unordered_image_pair = tuple(sorted((
                row["left_asset_filename"],
                row["right_asset_filename"],
            )))
            if unordered_image_pair in seen_unordered_image_pairs:
                raise ValueError(
                    f"unordered image pair occurs more than once across inventory: {unordered_image_pair}"
                )
            seen_unordered_image_pairs.add(unordered_image_pair)
        role = shard_id.split("_shard_", 1)[0]
        specs.append(
            ShardSpec(
                shard_id=shard_id,
                role=role,
                manifest_path=manifest_path,
                pair_count=expected_count,
                manifest_sha256=expected_hash,
                pair_ids=pair_ids,
            )
        )
    return specs
