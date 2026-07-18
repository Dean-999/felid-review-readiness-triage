#!/usr/bin/env python3
"""Build a restricted PF-ERI v2 outcome-free measurement-pilot manifest.

The builder accepts only v2 canonical-pair and directed-membership manifests.
It deliberately refuses legacy, identity-bearing, outcome-bearing, or
feature-bearing pair sources rather than silently converting them into v2 data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "pferi_v2_measurement_feasibility_pilot_contract_v1"
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_v2_canonical_pair_contract as pair_contract


IMAGE_CONTEXT_COLUMNS = ["image_id", "image_decode_status", "illumination_metadata", "source_camera_context"]
PILOT_COLUMNS = ["contract_version", "pilot_pair_id", "canonical_pair_id", "selection_seed_id", "selection_stratum", "pair_availability_status", "pilot_inclusion_status", "exclusion_reason"]
FORBIDDEN_SOURCE_TOKENS = ("review", "outcome", "decision", "label", "route", "pferi", "identity", "phase18", "v1", "feature")


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _assert_safe_headers(headers: Sequence[str], source_name: str, forbidden_tokens: Sequence[str] = FORBIDDEN_SOURCE_TOKENS) -> None:
    forbidden = [header for header in headers if any(token in header.lower() for token in forbidden_tokens)]
    if forbidden:
        raise ValueError(f"{source_name} has forbidden v2 source headers: {', '.join(sorted(forbidden))}")


def _rank_band(rank: str) -> str:
    value = int(rank)
    if value == 1:
        return "rank_01"
    if value <= 5:
        return "rank_02_05"
    if value <= 20:
        return "rank_06_20"
    return "rank_21_plus"


def _pilot_pair_id(canonical_pair_id: str, seed: str) -> str:
    digest = hashlib.sha256(f"{seed}:{canonical_pair_id}".encode("utf-8")).hexdigest()
    return "pferi_v2_pilot_" + digest[:24]


def build_pilot_manifest(
    canonical_pairs: Sequence[Mapping[str, str]],
    memberships: Sequence[Mapping[str, str]],
    image_context_rows: Sequence[Mapping[str, str]],
    *,
    target_count: int,
    seed: str,
    canonical_headers: Sequence[str] | None = None,
    membership_headers: Sequence[str] | None = None,
    image_context_headers: Sequence[str] | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Select a reproducible, restricted pilot sample without outcome inputs."""
    canonical_headers = list(canonical_headers or (list(canonical_pairs[0].keys()) if canonical_pairs else []))
    membership_headers = list(membership_headers or (list(memberships[0].keys()) if memberships else []))
    image_context_headers = list(image_context_headers or (list(image_context_rows[0].keys()) if image_context_rows else []))
    _assert_safe_headers(canonical_headers, "canonical-pairs source")
    _assert_safe_headers(membership_headers, "candidate-memberships source", ("review", "outcome", "decision", "label", "route", "pferi", "identity", "phase18", "v1", "feature"))
    missing_context = set(IMAGE_CONTEXT_COLUMNS).difference(image_context_headers)
    if missing_context:
        raise ValueError(f"image-context source missing columns: {', '.join(sorted(missing_context))}")
    if target_count < 1:
        raise ValueError("target_count must be positive")
    if not seed.strip():
        raise ValueError("seed must be non-empty")

    context_by_id = {str(row["image_id"]): row for row in image_context_rows}
    memberships_by_pair: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in memberships:
        memberships_by_pair[str(row.get("canonical_pair_id", ""))].append(row)
    candidates: list[tuple[Mapping[str, str], str]] = []
    exclusions: Counter[str] = Counter()
    for row in canonical_pairs:
        if row.get("contract_version") != pair_contract.CONTRACT_VERSION:
            exclusions["invalid_canonical_contract_version"] += 1
            continue
        if row.get("pair_inclusion_status") != "eligible" or row.get("pair_availability_status") != "available":
            exclusions["canonical_pair_not_eligible_and_available"] += 1
            continue
        pair_id = str(row.get("canonical_pair_id", ""))
        left, right = str(row.get("endpoint_a_image_id", "")), str(row.get("endpoint_b_image_id", ""))
        if pair_contract.canonical_pair_id(left, right) != pair_id:
            exclusions["invalid_canonical_pair_identifier"] += 1
            continue
        left_context, right_context = context_by_id.get(left), context_by_id.get(right)
        if left_context is None or right_context is None:
            exclusions["image_context_missing"] += 1
            continue
        if left_context.get("image_decode_status") != "ok" or right_context.get("image_decode_status") != "ok":
            exclusions["image_not_decodable"] += 1
            continue
        pair_memberships = memberships_by_pair.get(pair_id, [])
        if not pair_memberships:
            exclusions["no_directed_membership"] += 1
            continue
        first = sorted(pair_memberships, key=lambda item: (int(item["candidate_rank"]), item["descriptor_name"]))[0]
        descriptor = str(first["descriptor_name"])
        rank_band = _rank_band(str(first["candidate_rank"]))
        illumination = "infrared" if "infrared" in {str(left_context.get("illumination_metadata", "")), str(right_context.get("illumination_metadata", ""))} else "day_or_unknown"
        stratum = f"descriptor:{descriptor}|{rank_band}|illumination:{illumination}"
        candidates.append((row, stratum))
    if len(candidates) < target_count:
        raise ValueError(f"insufficient eligible v2 pilot pairs: need {target_count}, found {len(candidates)}")

    rng = random.Random(seed)
    by_stratum: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row, stratum in candidates:
        by_stratum[stratum].append(row)
    for rows in by_stratum.values():
        rng.shuffle(rows)
    selected: list[tuple[Mapping[str, str], str]] = []
    strata = sorted(by_stratum)
    while len(selected) < target_count and any(by_stratum[stratum] for stratum in strata):
        for stratum in strata:
            if len(selected) >= target_count:
                break
            if by_stratum[stratum]:
                selected.append((by_stratum[stratum].pop(), stratum))
    rows = [
        {
            "contract_version": CONTRACT_VERSION,
            "pilot_pair_id": _pilot_pair_id(str(pair["canonical_pair_id"]), seed),
            "canonical_pair_id": str(pair["canonical_pair_id"]),
            "selection_seed_id": seed,
            "selection_stratum": stratum,
            "pair_availability_status": "available",
            "pilot_inclusion_status": "included",
            "exclusion_reason": "",
        }
        for pair, stratum in selected
    ]
    audit = {
        "contract_version": CONTRACT_VERSION,
        "status": "PASS",
        "target_count": target_count,
        "selected_count": len(rows),
        "input_canonical_pair_count": len(canonical_pairs),
        "eligible_candidate_count": len(candidates),
        "exclusion_counts": dict(sorted(exclusions.items())),
        "selection_stratum_counts": dict(sorted(Counter(row["selection_stratum"] for row in rows).items())),
        "duplicate_canonical_pair_count": len(rows) - len({row["canonical_pair_id"] for row in rows}),
        "outcome_data_rule": "no_v2_outcome_collection_or_outcome_label_access",
        "confirmation_overlap_rule": "pilot_pairs_are_ineligible_for_v2_confirmation_samples",
        "claim_boundary": "This manifest is a restricted outcome-free measurement pilot. It does not establish v2 confirmation eligibility, feature validity, or model performance.",
    }
    return rows, audit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-pairs", type=Path, required=True)
    parser.add_argument("--candidate-memberships", type=Path, required=True)
    parser.add_argument("--image-context", type=Path, required=True)
    parser.add_argument("--target-count", type=int, default=160)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args(argv)
    canonical_rows, canonical_headers = read_csv(args.canonical_pairs)
    membership_rows, membership_headers = read_csv(args.candidate_memberships)
    context_rows, context_headers = read_csv(args.image_context)
    try:
        rows, audit = build_pilot_manifest(canonical_rows, membership_rows, context_rows, target_count=args.target_count, seed=args.seed, canonical_headers=canonical_headers, membership_headers=membership_headers, image_context_headers=context_headers)
    except ValueError as error:
        audit = {"contract_version": CONTRACT_VERSION, "status": "FAIL", "error": str(error)}
        args.audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 1
    write_csv(args.output_csv, rows, PILOT_COLUMNS)
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
