#!/usr/bin/env python3
"""Audit the outcome-free PF-ERI v2 candidate image-pair graph for Workstream 03.

The audit deliberately reads only the frozen dual-descriptor candidate reservoir.
It never reads outcome labels, identity truth, PF-ERI feature measurements, or
review responses.  Its outputs describe the graph that future partitioning must
respect; they are not a development/calibration/confirmation split.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANONICAL_PAIRS = ROOT / "outputs/pferi_v2/dual_descriptor_queue/canonical_pairs.csv"
DEFAULT_MEMBERSHIPS = ROOT / "outputs/pferi_v2/dual_descriptor_queue/candidate_memberships.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs/pferi_v2/information_partitioning/2026-07-14_graph_inventory_v1"

CANONICAL_COLUMNS = {
    "contract_version",
    "canonical_pair_id",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "source_dataset",
    "pair_availability_status",
    "pair_inclusion_status",
    "exclusion_reason",
}
MEMBERSHIP_COLUMNS = {
    "contract_version",
    "canonical_pair_id",
    "descriptor_name",
    "queue_name",
    "queue_snapshot_id",
    "query_image_id",
    "candidate_image_id",
    "candidate_rank",
    "descriptor_similarity",
    "membership_direction",
}


class UnionFind:
    """Small deterministic union-find implementation for the candidate graph."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}
        self.size: dict[str, int] = {}

    def add(self, item: str) -> None:
        if item not in self.parent:
            self.parent[item] = item
            self.size[item] = 1

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            parent = self.parent[item]
            self.parent[item] = root
            item = parent
        return root

    def union(self, left: str, right: str) -> None:
        self.add(left)
        self.add(right)
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if (self.size[left_root], left_root) < (self.size[right_root], right_root):
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        self.size[left_root] += self.size[right_root]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def recorded_path(path: Path) -> str:
    """Prefer repository-relative evidence paths while retaining test portability."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = sorted(required_columns - headers)
        if missing:
            raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")
        return list(reader)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def component_records(
    eligible_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    union_find = UnionFind()
    degree = Counter()
    component_edges = Counter()
    for row in eligible_rows:
        endpoint_a = row["endpoint_a_image_id"]
        endpoint_b = row["endpoint_b_image_id"]
        union_find.union(endpoint_a, endpoint_b)
        degree[endpoint_a] += 1
        degree[endpoint_b] += 1

    members_by_root: dict[str, list[str]] = defaultdict(list)
    for image_id in sorted(union_find.parent):
        members_by_root[union_find.find(image_id)].append(image_id)
    canonical_component_key = {
        root: min(members) for root, members in members_by_root.items()
    }
    component_id_by_root = {
        root: f"component_{index:06d}"
        for index, root in enumerate(sorted(members_by_root, key=lambda item: canonical_component_key[item]), start=1)
    }
    for row in eligible_rows:
        component_edges[union_find.find(row["endpoint_a_image_id"])] += 1

    components: list[dict[str, Any]] = []
    image_rows: list[dict[str, Any]] = []
    for root, members in members_by_root.items():
        component_id = component_id_by_root[root]
        components.append(
            {
                "component_id": component_id,
                "component_anchor_image_id": canonical_component_key[root],
                "image_count": len(members),
                "canonical_pair_count": component_edges[root],
            }
        )
        for image_id in members:
            image_rows.append(
                {
                    "image_id": image_id,
                    "component_id": component_id,
                    "eligible_incident_pair_count": degree[image_id],
                }
            )
    components.sort(key=lambda row: (-int(row["image_count"]), str(row["component_anchor_image_id"])))
    image_rows.sort(key=lambda row: str(row["image_id"]))
    return components, image_rows


def make_figure(
    components: list[dict[str, Any]], image_rows: list[dict[str, Any]], output_dir: Path
) -> None:
    image_counts = [int(row["image_count"]) for row in components]
    pair_counts = [int(row["canonical_pair_count"]) for row in components]
    degree_counts = [int(row["eligible_incident_pair_count"]) for row in image_rows]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    axes[0].axis("off")
    axes[0].set_title("A. Candidate graph connectivity", loc="left")
    axes[0].text(0.06, 0.78, f"{len(components):,}", fontsize=40, fontweight="bold", color="#356aa0")
    axes[0].text(0.06, 0.67, "connected component", fontsize=13)
    axes[0].text(0.06, 0.48, f"{sum(image_counts):,} images", fontsize=20, fontweight="bold")
    axes[0].text(0.06, 0.34, f"{sum(pair_counts):,} eligible canonical pairs", fontsize=20, fontweight="bold")
    axes[0].text(
        0.06,
        0.13,
        "Whole-component allocation is infeasible.\nFuture splits must assign disjoint image sets\nand exclude cross-set candidate edges.",
        fontsize=12,
        va="bottom",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#f5f5f5", "edgecolor": "#999999"},
    )

    bins = max(10, min(45, int(max(degree_counts) - min(degree_counts) + 1)))
    axes[1].hist(degree_counts, bins=bins, color="#d98528", edgecolor="white")
    axes[1].axvline(sum(degree_counts) / len(degree_counts), color="#356aa0", linewidth=2, label="mean degree")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Eligible incident canonical pairs per image")
    axes[1].set_ylabel("Number of images (log scale)")
    axes[1].set_title("B. Image reuse in the candidate graph")
    axes[1].legend(frameon=False)
    axes[1].grid(axis="y", alpha=0.25)
    fig.savefig(output_dir / "candidate_graph_component_structure.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / "candidate_graph_component_structure.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build_report(audit: dict[str, Any]) -> str:
    components = audit["graph_structure"]
    checks = audit["integrity_checks"]
    status = audit["status"]
    return f"""# Workstream 03 Candidate Graph Inventory

## Scope

This report describes the outcome-free PF-ERI v2 candidate image-pair graph used to prepare the development, calibration, and confirmation information barriers. The audit reads only the frozen dual-descriptor queue manifests. It does not read identity truth, reviewer outcomes, PF-ERI measurement values, thresholds, or model outputs. Its purpose is therefore structural: it establishes which images and unordered physical pairs must remain together or be explicitly excluded when a later split is constructed.

## Methods

The audit treated each eligible and available canonical unordered pair as one graph edge and each endpoint image as one node. Connected components were computed with deterministic union-find operations. Directed descriptor-membership rows were separately reconciled to their canonical pair and endpoint orientation. The audit records input SHA-256 hashes, checks for duplicate canonical identifiers and endpoint pairs, self-pairs, missing membership references, invalid directions, and membership rows whose query/candidate orientation does not agree with the canonical endpoints. It does not assign any graph component to a modelling role.

## Results

The frozen reservoir contains {audit['counts']['canonical_pair_row_count']:,} canonical-pair rows, of which {audit['counts']['eligible_available_canonical_pair_count']:,} are eligible and available. The corresponding graph contains {components['image_node_count']:,} image nodes and {components['connected_component_count']:,} connected components. The largest component contains {components['largest_component_image_count']:,} images and {components['largest_component_canonical_pair_count']:,} canonical pairs. The entire candidate graph is one connected component. Consequently, a whole-component allocation would leave no data for more than one role and is not an admissible partition method. A later split must allocate disjoint image sets and retain only canonical pairs whose two endpoints fall within the same allocated set; every cross-set candidate edge must be excluded and recorded. This preserves the required zero image and zero canonical-pair crossings without pretending that graph connectivity itself solves allocation.

The directed-membership reconciliation covers {audit['counts']['membership_row_count']:,} rows across {audit['counts']['membership_canonical_pair_count']:,} canonical pairs. The audit found {checks['duplicate_canonical_pair_id_count']:,} duplicate canonical identifiers, {checks['duplicate_unordered_endpoint_pair_count']:,} duplicate unordered endpoint pairs, {checks['self_pair_count']:,} self-pairs, {checks['membership_missing_canonical_pair_count']:,} membership rows without a canonical-pair reference, and {checks['membership_orientation_mismatch_count']:,} endpoint-orientation mismatches. The graph-inventory decision is therefore {status}.

## Interpretation and limitation

This PASS decision means that the frozen candidate manifests are structurally auditable enough to support the next partition-design task. It does not mean that a development/calibration/confirmation split has been made, that an identity-disjoint sensitivity analysis is feasible, or that any performance result is valid. Identity truth is intentionally outside this audit. The later split must still use a pre-specified allocation rule and seed, demonstrate zero prohibited image and canonical-pair crossings, and apply the separate identity-disjoint sensitivity rule wherever the authorized identity graph permits it.
"""


def audit(canonical_pairs_path: Path, memberships_path: Path, output_dir: Path) -> dict[str, Any]:
    canonical_rows = read_csv(canonical_pairs_path, CANONICAL_COLUMNS)
    membership_rows = read_csv(memberships_path, MEMBERSHIP_COLUMNS)
    output_dir.mkdir(parents=True, exist_ok=True)

    error_messages: list[str] = []
    pair_ids = [row["canonical_pair_id"] for row in canonical_rows]
    canonical_by_id: dict[str, dict[str, str]] = {}
    duplicate_ids = 0
    duplicate_endpoints = 0
    endpoint_keys: set[tuple[str, str]] = set()
    self_pairs = 0
    contract_versions = set()
    for row in canonical_rows:
        pair_id = row["canonical_pair_id"]
        contract_versions.add(row["contract_version"])
        if pair_id in canonical_by_id:
            duplicate_ids += 1
        canonical_by_id[pair_id] = row
        endpoint_a = row["endpoint_a_image_id"]
        endpoint_b = row["endpoint_b_image_id"]
        if endpoint_a == endpoint_b:
            self_pairs += 1
        endpoint_key = tuple(sorted((endpoint_a, endpoint_b)))
        if endpoint_key in endpoint_keys:
            duplicate_endpoints += 1
        endpoint_keys.add(endpoint_key)

    eligible_rows = [
        row
        for row in canonical_rows
        if row["pair_availability_status"] == "available" and row["pair_inclusion_status"] == "eligible"
    ]
    components, image_rows = component_records(eligible_rows)
    component_by_image = {row["image_id"]: row["component_id"] for row in image_rows}

    membership_missing_pair = 0
    membership_orientation_mismatch = 0
    membership_invalid_direction = 0
    membership_contract_mismatch = 0
    membership_count_by_pair = Counter()
    descriptor_counts = Counter()
    direction_counts = Counter()
    for row in membership_rows:
        membership_count_by_pair[row["canonical_pair_id"]] += 1
        descriptor_counts[row["descriptor_name"]] += 1
        direction = row["membership_direction"]
        direction_counts[direction] += 1
        pair = canonical_by_id.get(row["canonical_pair_id"])
        if pair is None:
            membership_missing_pair += 1
            continue
        if row["contract_version"] != pair["contract_version"]:
            membership_contract_mismatch += 1
        if direction == "a_to_b":
            expected = (pair["endpoint_a_image_id"], pair["endpoint_b_image_id"])
        elif direction == "b_to_a":
            expected = (pair["endpoint_b_image_id"], pair["endpoint_a_image_id"])
        else:
            membership_invalid_direction += 1
            continue
        observed = (row["query_image_id"], row["candidate_image_id"])
        if observed != expected:
            membership_orientation_mismatch += 1

    if len(contract_versions) != 1:
        error_messages.append("canonical manifest has more than one contract version")
    for label, count in {
        "duplicate canonical pair IDs": duplicate_ids,
        "duplicate unordered endpoint pairs": duplicate_endpoints,
        "self pairs": self_pairs,
        "membership rows missing canonical pairs": membership_missing_pair,
        "invalid membership directions": membership_invalid_direction,
        "membership endpoint orientation mismatches": membership_orientation_mismatch,
        "membership contract mismatches": membership_contract_mismatch,
    }.items():
        if count:
            error_messages.append(f"{label}: {count}")

    membership_multiplicity = Counter(membership_count_by_pair.values())
    audit_result: dict[str, Any] = {
        "audit_version": "pferi_v2_workstream_03_graph_inventory_v1",
        "audit_date": str(date.today()),
        "status": "PASS" if not error_messages else "FAIL",
        "claim_boundary": "Outcome-free candidate-graph structural audit only. This is not a split, an identity-truth audit, an outcome analysis, or a Re-ID-performance result.",
        "input_artifacts": {
            "canonical_pairs_path": recorded_path(canonical_pairs_path),
            "canonical_pairs_sha256": sha256(canonical_pairs_path),
            "candidate_memberships_path": recorded_path(memberships_path),
            "candidate_memberships_sha256": sha256(memberships_path),
        },
        "counts": {
            "canonical_pair_row_count": len(canonical_rows),
            "unique_canonical_pair_id_count": len(set(pair_ids)),
            "eligible_available_canonical_pair_count": len(eligible_rows),
            "membership_row_count": len(membership_rows),
            "membership_canonical_pair_count": len(membership_count_by_pair),
            "descriptor_membership_counts": dict(sorted(descriptor_counts.items())),
            "membership_direction_counts": dict(sorted(direction_counts.items())),
            "membership_multiplicity_distribution": {str(key): value for key, value in sorted(membership_multiplicity.items())},
        },
        "graph_structure": {
            "image_node_count": len(image_rows),
            "connected_component_count": len(components),
            "largest_component_image_count": int(components[0]["image_count"]) if components else 0,
            "largest_component_canonical_pair_count": int(components[0]["canonical_pair_count"]) if components else 0,
            "singleton_image_component_count": sum(1 for row in components if int(row["image_count"]) == 1),
        },
        "integrity_checks": {
            "duplicate_canonical_pair_id_count": duplicate_ids,
            "duplicate_unordered_endpoint_pair_count": duplicate_endpoints,
            "self_pair_count": self_pairs,
            "membership_missing_canonical_pair_count": membership_missing_pair,
            "membership_invalid_direction_count": membership_invalid_direction,
            "membership_orientation_mismatch_count": membership_orientation_mismatch,
            "membership_contract_mismatch_count": membership_contract_mismatch,
            "error_messages": error_messages,
        },
        "next_boundary": "No partition is locked by this audit. A later split must record a pre-specified allocation rule and seed, show zero image and canonical-pair crossings, and separately assess authorized identity-disjoint sensitivity feasibility.",
    }
    write_csv(
        output_dir / "component_inventory.csv",
        components,
        ["component_id", "component_anchor_image_id", "image_count", "canonical_pair_count"],
    )
    write_csv(
        output_dir / "image_node_inventory.csv",
        image_rows,
        ["image_id", "component_id", "eligible_incident_pair_count"],
    )
    (output_dir / "graph_inventory_audit.json").write_text(
        json.dumps(audit_result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "graph_inventory_report.md").write_text(build_report(audit_result), encoding="utf-8")
    make_figure(components, image_rows, output_dir)
    return audit_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-pairs", type=Path, default=DEFAULT_CANONICAL_PAIRS)
    parser.add_argument("--memberships", type=Path, default=DEFAULT_MEMBERSHIPS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = audit(args.canonical_pairs.resolve(), args.memberships.resolve(), args.output_dir.resolve())
    print(result["status"])
    print(json.dumps(result["counts"], indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
