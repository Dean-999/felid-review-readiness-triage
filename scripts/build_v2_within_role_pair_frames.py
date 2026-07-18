#!/usr/bin/env python3
"""Build and audit post-allocation within-role canonical pair frames."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

try:
    from scripts.prepare_v2_image_allocation_strata import sha256_file
except ModuleNotFoundError:  # Direct execution sets scripts/ as sys.path[0].
    from prepare_v2_image_allocation_strata import sha256_file


ROOT = Path(__file__).resolve().parents[1]
FRAME_VERSION = "pferi_v2_post_allocation_within_role_pair_frame_v1"
ROLES = ("development", "calibration", "confirmation")
DESCRIPTORS = {
    "megadescriptor_l_384": "megadescriptor",
    "dinov2_vitl14": "dinov2",
}
OUTPUT_COLUMNS = [
    "frame_contract_version",
    "canonical_pair_id",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "partition_role",
    "descriptor_support_category",
    "best_candidate_rank",
    "best_rank_band",
    "retrieval_stratum_id",
    "membership_count",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def rank_band(rank: int) -> str:
    if 1 <= rank <= 5:
        return "rank_01_05"
    if 6 <= rank <= 10:
        return "rank_06_10"
    if 11 <= rank <= 20:
        return "rank_11_20"
    raise ValueError(f"candidate rank outside frozen top-20 queue: {rank}")


def membership_metadata(rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, object]]:
    descriptors: dict[str, set[str]] = defaultdict(set)
    ranks: dict[str, list[int]] = defaultdict(list)
    counts: Counter[str] = Counter()
    for row in rows:
        pair_id = row["canonical_pair_id"]
        descriptor_name = row["descriptor_name"]
        if descriptor_name not in DESCRIPTORS:
            raise ValueError(f"unexpected descriptor: {descriptor_name}")
        descriptors[pair_id].add(DESCRIPTORS[descriptor_name])
        ranks[pair_id].append(int(row["candidate_rank"]))
        counts[pair_id] += 1
    result: dict[str, dict[str, object]] = {}
    for pair_id in descriptors:
        support = descriptors[pair_id]
        if support == {"megadescriptor"}:
            category = "megadescriptor_only"
        elif support == {"dinov2"}:
            category = "dinov2_only"
        elif support == {"megadescriptor", "dinov2"}:
            category = "both"
        else:
            raise ValueError(f"invalid descriptor support set for {pair_id}: {support}")
        best_rank = min(ranks[pair_id])
        result[pair_id] = {
            "descriptor_support_category": category,
            "best_candidate_rank": best_rank,
            "best_rank_band": rank_band(best_rank),
            "membership_count": counts[pair_id],
        }
    return result


def build_frames(
    canonical_rows: Sequence[Mapping[str, str]],
    membership_rows: Sequence[Mapping[str, str]],
    allocation_rows: Sequence[Mapping[str, str]],
    exclusion_rows: Sequence[Mapping[str, str]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    role_by_image = {row["image_id"]: row["partition_role"] for row in allocation_rows}
    if len(role_by_image) != len(allocation_rows):
        raise ValueError("duplicate image_id in allocation manifest")
    if set(role_by_image.values()) != set(ROLES):
        raise ValueError("allocation manifest lacks one or more required roles")
    excluded = {row["canonical_pair_id"] for row in exclusion_rows}
    if len(excluded) != len(exclusion_rows):
        raise ValueError("duplicate canonical_pair_id in exclusion register")
    metadata = membership_metadata(membership_rows)

    output: list[dict[str, object]] = []
    counts = Counter()
    seen_pairs: set[str] = set()
    for row in canonical_rows:
        if row["pair_availability_status"] != "available" or row["pair_inclusion_status"] != "eligible":
            counts["canonical_ineligible_or_unavailable"] += 1
            continue
        pair_id = row["canonical_pair_id"]
        if pair_id in seen_pairs:
            raise ValueError(f"duplicate eligible canonical pair: {pair_id}")
        seen_pairs.add(pair_id)
        left = row["endpoint_a_image_id"]
        right = row["endpoint_b_image_id"]
        if left not in role_by_image or right not in role_by_image:
            raise ValueError(f"canonical pair endpoint absent from image allocation: {pair_id}")
        if role_by_image[left] != role_by_image[right]:
            counts["cross_role_pair"] += 1
            continue
        if pair_id in excluded:
            counts["historical_exclusion_pair"] += 1
            continue
        if pair_id not in metadata:
            raise ValueError(f"canonical pair lacks descriptor membership: {pair_id}")
        role = role_by_image[left]
        meta = metadata[pair_id]
        retrieval_stratum = f"{meta['descriptor_support_category']}__{meta['best_rank_band']}"
        output.append(
            {
                "frame_contract_version": FRAME_VERSION,
                "canonical_pair_id": pair_id,
                "endpoint_a_image_id": left,
                "endpoint_b_image_id": right,
                "partition_role": role,
                **meta,
                "retrieval_stratum_id": retrieval_stratum,
            }
        )
        counts[f"within_role_{role}"] += 1

    pair_ids = [row["canonical_pair_id"] for row in output]
    role_counts = Counter(row["partition_role"] for row in output)
    role_strata_counts = {
        role: dict(sorted(Counter(
            row["retrieval_stratum_id"] for row in output if row["partition_role"] == role
        ).items()))
        for role in ROLES
    }
    all_nine_present = all(len(role_strata_counts[role]) == 9 for role in ROLES)
    basic_capacity_pass = (
        role_counts["development"] >= 445
        and role_counts["calibration"] >= 445
        and role_counts["confirmation"] >= 1334
    )
    status = "PASS" if len(pair_ids) == len(set(pair_ids)) and all_nine_present and basic_capacity_pass else "FAIL"
    audit = {
        "audit_version": "pferi_v2_post_allocation_within_role_pair_frame_audit_v1",
        "status": status,
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "eligible_canonical_pair_count": len(seen_pairs),
        "within_role_pair_count": len(output),
        "unique_within_role_pair_count": len(set(pair_ids)),
        "role_pair_counts": dict(sorted(role_counts.items())),
        "role_retrieval_stratum_counts": role_strata_counts,
        "all_nine_retrieval_strata_present_in_each_role": all_nine_present,
        "minimum_basic_pair_targets": {"development": 445, "calibration": 445, "confirmation_combined": 1334},
        "basic_total_capacity_pass": basic_capacity_pass,
        "exclusion_and_crossing_counts": dict(sorted(counts.items())),
        "pair_measurement_required_count": len(output),
        "pair_sampling_authorized": False,
        "outcome_packet_authorized": False,
        "claim_boundary": (
            "PASS establishes the immutable within-role pair frames and basic retrieval-cell capacity only. "
            "All rows still require frozen automatic pair measurements before formal pair sampling."
        ),
    }
    return sorted(output, key=lambda row: (str(row["partition_role"]), str(row["canonical_pair_id"]))), audit


def write_csv(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-pairs", type=Path, required=True)
    parser.add_argument("--candidate-memberships", type=Path, required=True)
    parser.add_argument("--image-allocation", type=Path, required=True)
    parser.add_argument("--exclusion-register", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args(argv)
    rows, audit = build_frames(
        read_csv(args.canonical_pairs),
        read_csv(args.candidate_memberships),
        read_csv(args.image_allocation),
        read_csv(args.exclusion_register),
    )
    write_csv(args.output_csv, rows)
    audit.update(
        {
            "canonical_pairs_sha256": sha256_file(args.canonical_pairs),
            "candidate_memberships_sha256": sha256_file(args.candidate_memberships),
            "image_allocation_sha256": sha256_file(args.image_allocation),
            "exclusion_register_sha256": sha256_file(args.exclusion_register),
            "within_role_pair_frame": str(args.output_csv.resolve().relative_to(ROOT)),
            "within_role_pair_frame_sha256": sha256_file(args.output_csv),
        }
    )
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
