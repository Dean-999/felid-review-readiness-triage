#!/usr/bin/env python3
"""Audit whether a new, outcome-free Task 15I redevelopment reservoir is usable.

This audit deliberately does not select pairs or open labels. It only verifies
that a candidate reservoir has enough image-disjoint, measurable, stratified
pair structure to justify a new prelabel redevelopment contract.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_IMAGES = (
    ROOT
    / "data/candidate-reservoirs/photo-selection-candidate-pools"
    / "lynx_external_heterogeneous_supplement"
    / "lynx_external_heterogeneous_supplement_download_manifest.csv"
)
DEFAULT_EXISTING_MANIFESTS = tuple(
    sorted((ROOT / "data/frozen/pferi_v2").glob("*/manifest.csv"))
)
DEFAULT_OUTPUT = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development"
    / "2026-07-25_task15i_independent_redevelopment_capacity_audit/iterations/v7"
)

SOURCE_ID_FIELDS = (
    "source_candidate_id",
    "candidate_id",
    "canonical_photo_id",
    "photo_id",
)
SOURCE_URI_FIELDS = ("source_image_uri", "image_uri", "canonical_image_key")
SOURCE_SHA_FIELDS = ("sha256", "final_freeze_sha256", "final_freeze_source_sha256")
PAIR_ENDPOINT_A = "endpoint_a_candidate_image_id"
PAIR_ENDPOINT_B = "endpoint_b_candidate_image_id"
REQUIRED_PAIR_STRATA = (
    "descriptor_support_category",
    "best_rank_band",
    "development_evidence_state",
    "endpoint_quality_measurement_failure",
    "local_match_measurement_failure",
)


@dataclass(frozen=True)
class CapacityRequirements:
    component_target: int = 400
    pair_target: int = 1600
    min_pairs_per_component: int = 4
    max_pairs_per_component: int = 8
    max_endpoint_degree: int = 6
    outer_fold_count: int = 5
    min_components_per_outer_fold: int = 80


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def file_fingerprint(path: Path) -> dict[str, str]:
    try:
        display_path = str(path.relative_to(ROOT))
    except ValueError:
        display_path = str(path)
    return {"path": display_path, "sha256": sha256(path)}


def resolve_candidate_path(value: str, manifest: Path) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        return raw
    repository_path = ROOT / raw
    return repository_path if repository_path.exists() else manifest.parent / raw


def values(rows: Iterable[dict[str, str]], fields: Iterable[str]) -> set[str]:
    return {
        row[field].strip()
        for row in rows
        for field in fields
        if row.get(field, "").strip()
    }


def existing_reservoir_fingerprints(
    manifest_paths: Iterable[Path],
) -> tuple[set[str], set[str], set[str], list[dict[str, str]]]:
    identifiers: set[str] = set()
    uris: set[str] = set()
    hashes: set[str] = set()
    fingerprints: list[dict[str, str]] = []
    for path in manifest_paths:
        rows = read_csv(path)
        identifiers.update(values(rows, SOURCE_ID_FIELDS))
        uris.update(values(rows, SOURCE_URI_FIELDS))
        hashes.update(values(rows, SOURCE_SHA_FIELDS))
        fingerprints.append(file_fingerprint(path))
    return identifiers, uris, hashes, fingerprints


class DisjointSet:
    def __init__(self, nodes: Iterable[str]) -> None:
        self.parent = {node: node for node in nodes}

    def find(self, node: str) -> str:
        parent = self.parent[node]
        if parent != node:
            self.parent[node] = self.find(parent)
        return self.parent[node]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def pair_graph_audit(
    pair_rows: list[dict[str, str]],
    candidate_image_ids: set[str],
    requirements: CapacityRequirements,
) -> dict[str, Any]:
    if not pair_rows:
        return {"available": False, "reason": "missing_candidate_pair_manifest"}
    missing_columns = [
        column
        for column in (
            "candidate_pair_id",
            PAIR_ENDPOINT_A,
            PAIR_ENDPOINT_B,
            *REQUIRED_PAIR_STRATA,
        )
        if column not in pair_rows[0]
    ]
    if missing_columns:
        return {
            "available": False,
            "reason": "candidate_pair_manifest_missing_required_columns",
            "missing_columns": missing_columns,
        }

    invalid_endpoint_rows = 0
    self_pairs = 0
    duplicate_pairs = 0
    seen_pairs: set[tuple[str, str]] = set()
    valid_pairs: list[tuple[str, str]] = []
    for row in pair_rows:
        left, right = row[PAIR_ENDPOINT_A].strip(), row[PAIR_ENDPOINT_B].strip()
        if left not in candidate_image_ids or right not in candidate_image_ids:
            invalid_endpoint_rows += 1
            continue
        if left == right:
            self_pairs += 1
            continue
        edge = tuple(sorted((left, right)))
        if edge in seen_pairs:
            duplicate_pairs += 1
            continue
        seen_pairs.add(edge)
        valid_pairs.append(edge)

    graph = DisjointSet(candidate_image_ids)
    for left, right in valid_pairs:
        graph.union(left, right)
    component_pairs: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for edge in valid_pairs:
        component_pairs[graph.find(edge[0])].append(edge)
    degree = Counter(endpoint for edge in valid_pairs for endpoint in edge)
    component_sizes = [len(edges) for edges in component_pairs.values()]
    components_with_min_pairs = sum(
        size >= requirements.min_pairs_per_component for size in component_sizes
    )
    maximum_component_pairs = max(component_sizes, default=0)
    maximum_endpoint_degree = max(degree.values(), default=0)
    strata_complete = all(
        all(row[column].strip() for column in REQUIRED_PAIR_STRATA)
        for row in pair_rows
    )
    return {
        "available": True,
        "pair_row_count": len(pair_rows),
        "unique_valid_pair_count": len(valid_pairs),
        "invalid_endpoint_rows": invalid_endpoint_rows,
        "self_pair_rows": self_pairs,
        "duplicate_pair_rows": duplicate_pairs,
        "component_count": len(component_pairs),
        "components_with_minimum_pair_count": components_with_min_pairs,
        "maximum_component_pair_count": maximum_component_pairs,
        "maximum_endpoint_degree": maximum_endpoint_degree,
        "strata_complete": strata_complete,
        "strata_columns": list(REQUIRED_PAIR_STRATA),
        "pair_target_pass": len(valid_pairs) >= requirements.pair_target,
        "component_target_pass": len(component_pairs) >= requirements.component_target,
        "component_size_cap_pass": maximum_component_pairs <= requirements.max_pairs_per_component,
        "endpoint_degree_cap_pass": maximum_endpoint_degree <= requirements.max_endpoint_degree,
        "outer_fold_capacity_pass": components_with_min_pairs
        >= requirements.outer_fold_count * requirements.min_components_per_outer_fold,
    }


def finite(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def audit_measurements(
    *,
    candidate_image_ids: set[str],
    pair_rows: list[dict[str, str]],
    automatic_quality_manifest: Path | None,
    local_match_manifest: Path | None,
) -> dict[str, Any]:
    records: dict[str, Any] = {}
    if not automatic_quality_manifest or not automatic_quality_manifest.is_file():
        records["automatic_quality"] = {"present": False, "pass": False, "path": ""}
    else:
        rows = read_csv(automatic_quality_manifest)
        required = {
            "candidate_image_id",
            "image_decode_status",
            "native_pixel_count",
            "sharpness_measure",
            "exposure_clipping_fraction",
        }
        missing = sorted(required - set(rows[0])) if rows else sorted(required)
        by_id = {row.get("candidate_image_id", ""): row for row in rows}
        valid_rows = [
            row
            for image_id, row in by_id.items()
            if image_id in candidate_image_ids
            and row.get("image_decode_status") == "ok"
            and all(finite(row.get(field, "")) for field in required - {"candidate_image_id", "image_decode_status"})
        ]
        distinct = {
            field: len({row[field] for row in valid_rows})
            for field in ("native_pixel_count", "sharpness_measure", "exposure_clipping_fraction")
        }
        minimum_distinct = 10 if len(candidate_image_ids) >= 10 else 1
        records["automatic_quality"] = {
            "present": True,
            "pass": not missing
            and len(by_id) == len(candidate_image_ids)
            and len(valid_rows) / len(candidate_image_ids) >= 0.9
            and all(count >= minimum_distinct for count in distinct.values()),
            "path": str(automatic_quality_manifest),
            "missing_columns": missing,
            "matched_image_count": len(by_id),
            "valid_image_count": len(valid_rows),
            "distinct_valid_values": distinct,
        }
    if not local_match_manifest or not local_match_manifest.is_file():
        records["local_match"] = {"present": False, "pass": False, "path": ""}
    else:
        rows = read_csv(local_match_manifest)
        required = {
            "candidate_pair_id",
            "failure_code",
            "value_status",
            "local_match_coverage_fraction",
        }
        missing = sorted(required - set(rows[0])) if rows else sorted(required)
        expected_pair_ids = {row["candidate_pair_id"] for row in pair_rows}
        by_id = {row.get("candidate_pair_id", ""): row for row in rows}
        valid_rows = [
            row
            for pair_id, row in by_id.items()
            if pair_id in expected_pair_ids
            and row.get("failure_code") == "none"
            and row.get("value_status") == "not_missing"
            and finite(row.get("local_match_coverage_fraction", ""))
        ]
        minimum_distinct = 10 if len(expected_pair_ids) >= 10 else 1
        distinct = len({row["local_match_coverage_fraction"] for row in valid_rows})
        records["local_match"] = {
            "present": True,
            "pass": not missing
            and len(by_id) == len(expected_pair_ids)
            and len(valid_rows) / len(expected_pair_ids) >= 0.8
            and distinct >= minimum_distinct,
            "path": str(local_match_manifest),
            "missing_columns": missing,
            "matched_pair_count": len(by_id),
            "valid_pair_count": len(valid_rows),
            "distinct_valid_values": distinct,
        }
    return records


def audit_capacity(
    *,
    candidate_image_manifest: Path,
    existing_manifest_paths: Iterable[Path],
    candidate_pair_manifest: Path | None = None,
    automatic_quality_manifest: Path | None = None,
    local_match_manifest: Path | None = None,
    requirements: CapacityRequirements = CapacityRequirements(),
) -> dict[str, Any]:
    """Return a fully outcome-free readiness decision for a candidate reservoir."""
    candidate_rows = read_csv(candidate_image_manifest)
    if not candidate_rows:
        raise ValueError("candidate image manifest is empty")
    required_image_columns = {
        "source_candidate_id",
        "source_image_uri",
        "species",
        "domain_label",
    }
    missing_image_columns = sorted(required_image_columns - set(candidate_rows[0]))
    if missing_image_columns:
        raise ValueError(f"candidate image manifest missing {missing_image_columns}")
    if not ({"source_image_path", "local_relative_path"} & set(candidate_rows[0])):
        raise ValueError("candidate image manifest needs source_image_path or local_relative_path")

    existing_ids, existing_uris, existing_hashes, existing_fingerprints = (
        existing_reservoir_fingerprints(existing_manifest_paths)
    )
    candidate_source_ids = values(candidate_rows, ("source_candidate_id",))
    candidate_uris = values(candidate_rows, ("source_image_uri",))
    candidate_image_ids = {
        row.get("candidate_image_id", "").strip() or row["source_image_uri"].strip()
        for row in candidate_rows
    }
    candidate_hashes: set[str] = set()
    hash_to_candidate_image_ids: dict[str, list[str]] = defaultdict(list)
    existing_file_count = 0
    missing_files: list[str] = []
    for row in candidate_rows:
        path = resolve_candidate_path(
            row.get("local_relative_path", "") or row.get("source_image_path", ""),
            candidate_image_manifest,
        )
        if path.is_file():
            existing_file_count += 1
            content_hash = sha256(path)
            candidate_hashes.add(content_hash)
            hash_to_candidate_image_ids[content_hash].append(
                row.get("candidate_image_id", "") or row["source_image_uri"]
            )
        else:
            missing_files.append(row["source_candidate_id"])

    pair_rows = read_csv(candidate_pair_manifest) if candidate_pair_manifest and candidate_pair_manifest.is_file() else []
    graph_audit = pair_graph_audit(pair_rows, candidate_image_ids, requirements)
    measurement_audit = audit_measurements(
        candidate_image_ids=candidate_image_ids,
        pair_rows=pair_rows,
        automatic_quality_manifest=automatic_quality_manifest,
        local_match_manifest=local_match_manifest,
    )

    source_id_overlap = candidate_source_ids & existing_ids
    uri_overlap = candidate_uris & existing_uris
    hash_overlap = candidate_hashes & existing_hashes
    blocking_reasons: list[str] = []
    if len(candidate_image_ids) != len(candidate_rows):
        blocking_reasons.append("candidate_image_uris_are_not_unique")
    if missing_files:
        blocking_reasons.append("candidate_image_files_missing")
    duplicate_content_count = sum(
        len(candidate_ids) - 1
        for candidate_ids in hash_to_candidate_image_ids.values()
        if len(candidate_ids) > 1
    )
    if duplicate_content_count:
        blocking_reasons.append("candidate_images_have_duplicate_content")
    if source_id_overlap or uri_overlap or hash_overlap:
        blocking_reasons.append("candidate_images_overlap_existing_roles")
    if not graph_audit["available"]:
        blocking_reasons.append(str(graph_audit["reason"]))
    else:
        for field, reason in (
            ("pair_target_pass", "insufficient_candidate_pair_capacity"),
            ("component_target_pass", "insufficient_independent_component_capacity"),
            ("component_size_cap_pass", "component_pair_cap_exceeded"),
            ("endpoint_degree_cap_pass", "endpoint_degree_cap_exceeded"),
            ("outer_fold_capacity_pass", "insufficient_component_fold_capacity"),
            ("strata_complete", "candidate_pair_strata_incomplete"),
        ):
            if not graph_audit[field]:
                blocking_reasons.append(reason)
    for name, record in measurement_audit.items():
        if not record["present"]:
            blocking_reasons.append(f"missing_{name}_measurement_manifest")
        elif not record["pass"]:
            blocking_reasons.append(f"{name}_measurement_inadequate")

    return {
        "audit_version": "pferi_v2_task15i_independent_redevelopment_capacity_audit_v6",
        "status": "READY_FOR_PRELABEL_AMENDMENT" if not blocking_reasons else "NOT_READY",
        "requirements": asdict(requirements),
        "candidate_images": {
            "manifest_row_count": len(candidate_rows),
            "unique_source_candidate_id_count": len(candidate_source_ids),
            "unique_candidate_image_id_count": len(candidate_image_ids),
            "usable_image_count": existing_file_count,
            "missing_image_file_count": len(missing_files),
            "duplicate_content_image_count": duplicate_content_count,
            "species_counts": dict(sorted(Counter(row["species"] for row in candidate_rows).items())),
            "domain_counts": dict(sorted(Counter(row["domain_label"] for row in candidate_rows).items())),
        },
        "overlap_audit": {
            "source_candidate_id_overlap_count": len(source_id_overlap),
            "source_image_uri_overlap_count": len(uri_overlap),
            "image_overlap_count": len(hash_overlap),
            "candidate_hashable_image_count": len(candidate_hashes),
            "existing_role_manifest_count": len(existing_fingerprints),
        },
        "pair_graph_audit": graph_audit,
        "measurement_audit": measurement_audit,
        "input_fingerprints": {
            "candidate_image_manifest": file_fingerprint(candidate_image_manifest),
            "existing_role_manifests": existing_fingerprints,
            "candidate_pair_manifest": file_fingerprint(candidate_pair_manifest)
            if candidate_pair_manifest and candidate_pair_manifest.is_file()
            else None,
        },
        "blocking_reasons": blocking_reasons,
        "prelabel_contract_amendment_authorized": not blocking_reasons,
        "human_outcome_collection_authorized": False,
        "calibration_authorized": False,
        "confirmation_authorized": False,
        "claim_boundary": "This is an outcome-free capacity audit. A READY result only authorizes a new prelabel redevelopment contract; it does not authorize outcome collection, calibration, confirmation, or a performance claim.",
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze(output: Path, audit: dict[str, Any]) -> None:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable audit output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        audit_path = staging / "capacity_audit.json"
        builder_snapshot = staging / "audit_builder_snapshot.py"
        write_json(audit_path, audit)
        shutil.copy2(Path(__file__), builder_snapshot)
        artifacts = (audit_path, builder_snapshot)
        (staging / "CHECKSUMS.sha256").write_text(
            "".join(
                f"{sha256(path)}  {path.name}\n"
                for path in sorted(artifacts, key=lambda item: item.name)
            ),
            encoding="utf-8",
        )
        shutil.move(str(staging), str(output))
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-image-manifest", type=Path, default=DEFAULT_CANDIDATE_IMAGES)
    parser.add_argument("--candidate-pair-manifest", type=Path)
    parser.add_argument("--automatic-quality-manifest", type=Path)
    parser.add_argument("--local-match-manifest", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = audit_capacity(
        candidate_image_manifest=args.candidate_image_manifest,
        existing_manifest_paths=DEFAULT_EXISTING_MANIFESTS,
        candidate_pair_manifest=args.candidate_pair_manifest,
        automatic_quality_manifest=args.automatic_quality_manifest,
        local_match_manifest=args.local_match_manifest,
    )
    freeze(args.output, audit)
    print(f"{audit['status']}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
