#!/usr/bin/env python3
"""Prepare and audit outcome-free image-allocation strata without choosing a seed."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "pferi_v2_four_stage_stratified_sampling_contract_v1"
QUALITY_REQUIRED_COLUMNS = {
    "image_id",
    "image_integrity_status",
    "image_decode_status",
    "native_pixel_count",
    "native_pixel_count_value_status",
    "sharpness_measure",
    "sharpness_value_status",
    "exposure_clipping_fraction",
    "exposure_value_status",
}
CANONICAL_REQUIRED_COLUMNS = {"canonical_pair_id", "endpoint_a_image_id", "endpoint_b_image_id", "pair_availability_status", "pair_inclusion_status"}
OUTPUT_COLUMNS = [
    "strata_contract_version",
    "image_id",
    "graph_degree",
    "graph_degree_quintile",
    "quality_bottleneck_percentile",
    "quality_state",
    "image_allocation_cell_id",
]
ROLE_NAMES = ("development", "calibration", "confirmation")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def deterministic_percentiles(values: Mapping[str, float], *, higher_is_better: bool) -> dict[str, float]:
    ordered = sorted(values, key=lambda image_id: ((values[image_id] if higher_is_better else -values[image_id]), image_id))
    count = len(ordered)
    return {image_id: (index + 1) / count for index, image_id in enumerate(ordered)}


def equal_frequency_groups(values: Mapping[str, float], group_count: int) -> dict[str, int]:
    ordered = sorted(values, key=lambda image_id: (values[image_id], image_id))
    count = len(ordered)
    return {image_id: min(group_count, (index * group_count) // count + 1) for index, image_id in enumerate(ordered)}


def graph_degrees(canonical_rows: Sequence[Mapping[str, str]]) -> Counter[str]:
    degrees: Counter[str] = Counter()
    seen_pairs: set[str] = set()
    for row in canonical_rows:
        if row["pair_availability_status"] != "available" or row["pair_inclusion_status"] != "eligible":
            continue
        pair_id = row["canonical_pair_id"]
        if pair_id in seen_pairs:
            raise ValueError(f"duplicate eligible canonical pair: {pair_id}")
        seen_pairs.add(pair_id)
        left, right = row["endpoint_a_image_id"], row["endpoint_b_image_id"]
        if left == right:
            raise ValueError(f"self pair: {pair_id}")
        degrees[left] += 1
        degrees[right] += 1
    return degrees


def prepare_strata(
    quality_rows: Sequence[Mapping[str, str]],
    canonical_rows: Sequence[Mapping[str, str]],
    *,
    expected_image_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not quality_rows or not QUALITY_REQUIRED_COLUMNS.issubset(quality_rows[0]):
        raise ValueError("quality measurements do not satisfy the retained-field schema")
    if not canonical_rows or not CANONICAL_REQUIRED_COLUMNS.issubset(canonical_rows[0]):
        raise ValueError("canonical pairs do not satisfy the required schema")
    if len(quality_rows) != expected_image_count or len({row["image_id"] for row in quality_rows}) != expected_image_count:
        raise ValueError("quality measurements must contain exactly one row per frozen image")

    degrees = graph_degrees(canonical_rows)
    quality_ids = {row["image_id"] for row in quality_rows}
    if set(degrees) != quality_ids:
        raise ValueError("quality image IDs and eligible graph image nodes differ")

    valid: dict[str, Mapping[str, str]] = {}
    failed: set[str] = set()
    for row in quality_rows:
        statuses = (
            row["image_integrity_status"],
            row["image_decode_status"],
            row["native_pixel_count_value_status"],
            row["sharpness_value_status"],
            row["exposure_value_status"],
        )
        if statuses == ("pass", "ok", "not_missing", "not_missing", "not_missing"):
            valid[row["image_id"]] = row
        else:
            failed.add(row["image_id"])

    native = {image_id: float(row["native_pixel_count"]) for image_id, row in valid.items()}
    sharpness = {image_id: float(row["sharpness_measure"]) for image_id, row in valid.items()}
    clipping = {image_id: float(row["exposure_clipping_fraction"]) for image_id, row in valid.items()}
    native_pct = deterministic_percentiles(native, higher_is_better=True)
    sharpness_pct = deterministic_percentiles(sharpness, higher_is_better=True)
    clipping_pct = deterministic_percentiles(clipping, higher_is_better=False)
    bottleneck = {image_id: min(native_pct[image_id], sharpness_pct[image_id], clipping_pct[image_id]) for image_id in valid}
    quality_rank_groups = equal_frequency_groups(bottleneck, 5) if bottleneck else {}
    degree_groups = equal_frequency_groups({image_id: float(degrees[image_id]) for image_id in quality_ids}, 5)

    output: list[dict[str, Any]] = []
    for image_id in sorted(quality_ids):
        if image_id in failed:
            quality_state = "measurement_failure"
            bottleneck_text = ""
        else:
            quality_state = "quality_stress_bottom_quintile" if quality_rank_groups[image_id] == 1 else "ordinary"
            bottleneck_text = f"{bottleneck[image_id]:.12f}"
        degree_group = degree_groups[image_id]
        output.append(
            {
                "strata_contract_version": CONTRACT_VERSION,
                "image_id": image_id,
                "graph_degree": degrees[image_id],
                "graph_degree_quintile": f"degree_q{degree_group}",
                "quality_bottleneck_percentile": bottleneck_text,
                "quality_state": quality_state,
                "image_allocation_cell_id": f"degree_q{degree_group}__{quality_state}",
            }
        )

    cell_counts = Counter(row["image_allocation_cell_id"] for row in output)
    degree_counts = Counter(row["graph_degree_quintile"] for row in output)
    quality_counts = Counter(row["quality_state"] for row in output)
    audit = {
        "audit_version": "pferi_v2_image_allocation_strata_preflight_v1",
        "status": "PASS" if len(output) == expected_image_count and sum(cell_counts.values()) == expected_image_count else "FAIL",
        "expected_image_count": expected_image_count,
        "output_image_count": len(output),
        "eligible_canonical_pair_count": sum(1 for row in canonical_rows if row["pair_availability_status"] == "available" and row["pair_inclusion_status"] == "eligible"),
        "graph_degree_min": min(degrees.values()),
        "graph_degree_max": max(degrees.values()),
        "degree_quintile_counts": dict(sorted(degree_counts.items())),
        "quality_state_counts": dict(sorted(quality_counts.items())),
        "image_allocation_cell_counts": dict(sorted(cell_counts.items())),
        "nonempty_cell_count": len(cell_counts),
        "official_seed": None,
        "role_assignment_created": False,
        "claim_boundary": "Outcome-free image-strata preflight only. PASS does not choose a seed, assign an image role, sample a pair, or authorize an outcome packet.",
    }
    return output, audit


def role_quotas(cell_counts: Mapping[str, int], *, target_per_role: int, seed: str) -> dict[str, dict[str, int]]:
    quotas = {cell: {role: count // 3 for role in ROLE_NAMES} for cell, count in cell_counts.items()}
    deficits = {role: target_per_role - sum(quotas[cell][role] for cell in quotas) for role in ROLE_NAMES}
    for cell in sorted(cell_counts, key=lambda value: hashlib.sha256(f"{seed}|cell|{value}".encode()).hexdigest()):
        remainder = cell_counts[cell] % 3
        ordered_roles = sorted(
            ROLE_NAMES,
            key=lambda role: (-deficits[role], hashlib.sha256(f"{seed}|{cell}|{role}".encode()).hexdigest()),
        )
        for role in ordered_roles[:remainder]:
            quotas[cell][role] += 1
            deficits[role] -= 1
    if any(deficits.values()):
        raise RuntimeError(f"unable to satisfy exact role totals: {deficits}")
    return quotas


def allocate_roles(strata_rows: Sequence[Mapping[str, Any]], *, target_per_role: int, seed: str) -> dict[str, str]:
    if not seed:
        raise ValueError("official seed must be nonempty")
    by_cell: dict[str, list[str]] = {}
    for row in strata_rows:
        by_cell.setdefault(str(row["image_allocation_cell_id"]), []).append(str(row["image_id"]))
    quotas = role_quotas({cell: len(ids) for cell, ids in by_cell.items()}, target_per_role=target_per_role, seed=seed)
    assigned: dict[str, str] = {}
    for cell, image_ids in by_cell.items():
        ordered = sorted(image_ids, key=lambda image_id: hashlib.sha256(f"{seed}|image|{cell}|{image_id}".encode()).hexdigest())
        cursor = 0
        for role in ROLE_NAMES:
            count = quotas[cell][role]
            for image_id in ordered[cursor : cursor + count]:
                assigned[image_id] = role
            cursor += count
        if cursor != len(ordered):
            raise RuntimeError(f"cell allocation mismatch: {cell}")
    counts = Counter(assigned.values())
    if any(counts[role] != target_per_role for role in ROLE_NAMES):
        raise RuntimeError(f"role counts differ from target: {counts}")
    return assigned


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality-measurements", type=Path, required=True)
    parser.add_argument("--canonical-pairs", type=Path, default=ROOT / "outputs/pferi_v2/dual_descriptor_queue/canonical_pairs.csv")
    parser.add_argument("--expected-image-count", type=int, default=3000)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args(argv)
    quality_rows, _ = read_csv(args.quality_measurements)
    canonical_rows, _ = read_csv(args.canonical_pairs)
    rows, audit = prepare_strata(quality_rows, canonical_rows, expected_image_count=args.expected_image_count)
    write_csv(args.output_csv, rows)
    audit.update(
        {
            "quality_measurements": str(args.quality_measurements.resolve().relative_to(ROOT)),
            "quality_measurements_sha256": sha256_file(args.quality_measurements),
            "canonical_pairs": str(args.canonical_pairs.resolve().relative_to(ROOT)),
            "canonical_pairs_sha256": sha256_file(args.canonical_pairs),
            "strata_manifest": str(args.output_csv.resolve().relative_to(ROOT)),
            "strata_manifest_sha256": sha256_file(args.output_csv),
        }
    )
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
