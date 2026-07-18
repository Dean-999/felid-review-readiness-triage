#!/usr/bin/env python3
"""Apply the frozen official seed to the passed PF-ERI v2 image strata."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

try:
    from scripts.prepare_v2_image_allocation_strata import CONTRACT_VERSION, allocate_roles, sha256_file
except ModuleNotFoundError:  # Direct execution sets scripts/ as sys.path[0].
    from prepare_v2_image_allocation_strata import CONTRACT_VERSION, allocate_roles, sha256_file


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_COLUMNS = [
    "allocation_contract_version",
    "image_id",
    "image_allocation_cell_id",
    "partition_role",
    "within_cell_order_sha256",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_frozen_seed(path: Path) -> str:
    record = json.loads(path.read_text(encoding="utf-8"))
    seed = str(record.get("official_seed", ""))
    if record.get("status") != "FROZEN" or len(seed) != 64:
        raise ValueError("invalid or unfrozen official seed record")
    if record.get("reroll_policy") != "PROHIBITED":
        raise ValueError("official seed record lacks reroll prohibition")
    return seed


def build_allocation(
    strata_rows: Sequence[Mapping[str, str]],
    *,
    seed: str,
    target_per_role: int,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    if len(strata_rows) != target_per_role * 3:
        raise ValueError("strata row count must equal three exact role targets")
    image_ids = [row["image_id"] for row in strata_rows]
    if len(image_ids) != len(set(image_ids)):
        raise ValueError("duplicate image_id in strata manifest")
    assignments = allocate_roles(strata_rows, target_per_role=target_per_role, seed=seed)
    output = []
    for row in sorted(strata_rows, key=lambda item: item["image_id"]):
        image_id = row["image_id"]
        cell = row["image_allocation_cell_id"]
        output.append(
            {
                "allocation_contract_version": CONTRACT_VERSION,
                "image_id": image_id,
                "image_allocation_cell_id": cell,
                "partition_role": assignments[image_id],
                "within_cell_order_sha256": hashlib.sha256(
                    f"{seed}|image|{cell}|{image_id}".encode("utf-8")
                ).hexdigest(),
            }
        )
    role_counts = Counter(row["partition_role"] for row in output)
    role_sets = {
        role: {row["image_id"] for row in output if row["partition_role"] == role}
        for role in ("development", "calibration", "confirmation")
    }
    crossing_count = sum(
        len(role_sets[left] & role_sets[right])
        for left, right in (("development", "calibration"), ("development", "confirmation"), ("calibration", "confirmation"))
    )
    status = "PASS" if all(role_counts[role] == target_per_role for role in role_sets) and crossing_count == 0 else "FAIL"
    audit = {
        "audit_version": "pferi_v2_official_image_allocation_audit_v1",
        "status": status,
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "image_count": len(output),
        "unique_image_count": len(set(image_ids)),
        "target_per_role": target_per_role,
        "role_counts": dict(sorted(role_counts.items())),
        "cross_role_image_overlap_count": crossing_count,
        "nonempty_image_allocation_cell_count": len({row["image_allocation_cell_id"] for row in output}),
        "official_seed_sha256": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
        "pair_sampling_authorized": False,
        "outcome_packet_authorized": False,
        "claim_boundary": (
            "PASS freezes a zero-crossing image-role allocation only. Within-role pair measurement, "
            "capacity, exclusion, probability, and pair-selection audits remain required."
        ),
    }
    return output, audit


def write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strata-csv", type=Path, required=True)
    parser.add_argument("--seed-record", type=Path, required=True)
    parser.add_argument("--target-per-role", type=int, default=1000)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args(argv)
    seed = load_frozen_seed(args.seed_record)
    rows, audit = build_allocation(read_csv(args.strata_csv), seed=seed, target_per_role=args.target_per_role)
    write_csv(args.output_csv, rows)
    audit.update(
        {
            "strata_manifest": str(args.strata_csv.resolve().relative_to(ROOT)),
            "strata_manifest_sha256": sha256_file(args.strata_csv),
            "seed_record": str(args.seed_record.resolve().relative_to(ROOT)),
            "seed_record_sha256": sha256_file(args.seed_record),
            "allocation_manifest": str(args.output_csv.resolve().relative_to(ROOT)),
            "allocation_manifest_sha256": sha256_file(args.output_csv),
        }
    )
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
