#!/usr/bin/env python3
"""Build opaque, deterministic local-match shard manifests for the full v2 role frames."""

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
    from scripts.prepare_v2_image_allocation_strata import sha256_file
except ModuleNotFoundError:  # Direct execution sets scripts/ as sys.path[0].
    from prepare_v2_image_allocation_strata import sha256_file


ROOT = Path(__file__).resolve().parents[1]
SHARD_CONTRACT_VERSION = "pferi_v2_full_frame_local_match_shards_v1"
PUBLIC_COLUMNS = ["pair_execution_id", "left_asset_filename", "right_asset_filename"]
LINKAGE_COLUMNS = [
    "shard_contract_version",
    "shard_id",
    "pair_execution_id",
    "canonical_pair_id",
    "partition_role",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def execution_id(canonical_pair_id: str, role: str, seed: str) -> str:
    digest = hashlib.sha256(
        f"{SHARD_CONTRACT_VERSION}|{seed}|{role}|{canonical_pair_id}".encode("utf-8")
    ).hexdigest()
    return f"pferi_v2_fullframe_exec_{digest[:32]}"


def build_shards(
    frame_rows: Sequence[Mapping[str, str]],
    image_rows: Sequence[Mapping[str, str]],
    *,
    seed: str,
    shard_size: int,
) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, str]], dict[str, object]]:
    if shard_size <= 0:
        raise ValueError("shard_size must be positive")
    filename_by_image = {
        row["image_id"]: Path(row["image_path_relative"]).name
        for row in image_rows
    }
    if len(filename_by_image) != len(image_rows):
        raise ValueError("duplicate image_id in image execution manifest")
    shards: dict[str, list[dict[str, str]]] = {}
    linkage: list[dict[str, str]] = []
    role_counts = Counter(row["partition_role"] for row in frame_rows)
    execution_ids: set[str] = set()
    for role in ("development", "calibration", "confirmation"):
        role_rows = sorted(
            (row for row in frame_rows if row["partition_role"] == role),
            key=lambda row: row["canonical_pair_id"],
        )
        for start in range(0, len(role_rows), shard_size):
            shard_number = start // shard_size + 1
            shard_id = f"{role}_shard_{shard_number:03d}"
            public_rows = []
            for row in role_rows[start : start + shard_size]:
                pair_id = row["canonical_pair_id"]
                left = row["endpoint_a_image_id"]
                right = row["endpoint_b_image_id"]
                if left not in filename_by_image or right not in filename_by_image:
                    raise ValueError(f"frame endpoint missing from image manifest: {pair_id}")
                opaque_id = execution_id(pair_id, role, seed)
                if opaque_id in execution_ids:
                    raise ValueError(f"execution ID collision: {opaque_id}")
                execution_ids.add(opaque_id)
                public_rows.append(
                    {
                        "pair_execution_id": opaque_id,
                        "left_asset_filename": filename_by_image[left],
                        "right_asset_filename": filename_by_image[right],
                    }
                )
                linkage.append(
                    {
                        "shard_contract_version": SHARD_CONTRACT_VERSION,
                        "shard_id": shard_id,
                        "pair_execution_id": opaque_id,
                        "canonical_pair_id": pair_id,
                        "partition_role": role,
                    }
                )
            shards[shard_id] = public_rows
    shard_counts = {shard_id: len(rows) for shard_id, rows in sorted(shards.items())}
    status = "PASS" if len(linkage) == len(frame_rows) == len(execution_ids) and all(count <= shard_size for count in shard_counts.values()) else "FAIL"
    audit = {
        "audit_version": "pferi_v2_full_frame_local_match_shards_audit_v1",
        "status": status,
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "frame_pair_count": len(frame_rows),
        "unique_pair_execution_id_count": len(execution_ids),
        "role_pair_counts": dict(sorted(role_counts.items())),
        "shard_size_maximum": shard_size,
        "shard_count": len(shards),
        "shard_pair_counts": shard_counts,
        "image_asset_count": len(image_rows),
        "contains_outcomes": False,
        "contains_identity_truth": False,
        "formal_pair_sample_created": False,
        "claim_boundary": (
            "These manifests cover the complete post-allocation within-role frame for outcome-free automatic "
            "measurement. Sharding is computational only and does not select the formal review sample."
        ),
    }
    return shards, linkage, audit


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--within-role-frame", type=Path, required=True)
    parser.add_argument("--image-execution-manifest", type=Path, required=True)
    parser.add_argument("--seed-record", type=Path, required=True)
    parser.add_argument("--shard-size", type=int, default=1000)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    seed_record = json.loads(args.seed_record.read_text(encoding="utf-8"))
    if seed_record.get("status") != "FROZEN" or seed_record.get("reroll_policy") != "PROHIBITED":
        raise ValueError("invalid official seed record")
    seed = str(seed_record["official_seed"])
    shards, linkage, audit = build_shards(
        read_csv(args.within_role_frame),
        read_csv(args.image_execution_manifest),
        seed=seed,
        shard_size=args.shard_size,
    )
    manifest_dir = args.output_directory / "public_pair_manifests"
    for shard_id, rows in shards.items():
        write_csv(manifest_dir / f"{shard_id}.csv", PUBLIC_COLUMNS, rows)
    linkage_path = args.output_directory / "restricted_pair_execution_linkage.csv"
    write_csv(linkage_path, LINKAGE_COLUMNS, linkage)
    inventory = [
        {
            "shard_id": shard_id,
            "manifest_path": str((manifest_dir / f"{shard_id}.csv").resolve().relative_to(ROOT)),
            "pair_count": len(rows),
            "manifest_sha256": sha256_file(manifest_dir / f"{shard_id}.csv"),
        }
        for shard_id, rows in sorted(shards.items())
    ]
    inventory_path = args.output_directory / "shard_inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit.update(
        {
            "within_role_frame_sha256": sha256_file(args.within_role_frame),
            "image_execution_manifest_sha256": sha256_file(args.image_execution_manifest),
            "seed_record_sha256": sha256_file(args.seed_record),
            "restricted_linkage_sha256": sha256_file(linkage_path),
            "shard_inventory_sha256": sha256_file(inventory_path),
            "reused_immutable_image_zip": "archive/pferi_v2/task_runs/v2_czechlynx_fresh_descriptor_images.zip",
            "reused_immutable_image_zip_sha256": "540912351ff958b0d4395c0a8fec3ab8e129995f0d0f355656e673599f018bc0",
        }
    )
    audit_path = args.output_directory / "full_frame_local_match_shards_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
