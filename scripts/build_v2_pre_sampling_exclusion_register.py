#!/usr/bin/env python3
"""Build the immutable union of pair IDs exposed before official v2 sampling."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "pferi_v2_pre_sampling_exclusion_register_v1"
OUTPUT_COLUMNS = [
    "exclusion_contract_version",
    "canonical_pair_id",
    "exclusion_reason_codes",
    "source_artifact_count",
    "source_artifacts",
]


@dataclass(frozen=True)
class ExclusionSource:
    reason_code: str
    path: Path


DEFAULT_SOURCES = (
    ExclusionSource(
        "measurement_feasibility_pilot",
        ROOT / "work/pferi_v2/gpu/measurement_feasibility/restricted_pilot_manifest.csv",
    ),
    ExclusionSource(
        "reviewer_interface_dry_run",
        ROOT
        / "work/pferi_v2/review/interface_dry_run/restricted/restricted_linkage.csv",
    ),
    ExclusionSource(
        "timed_operational_rehearsal_v1_retired",
        ROOT
        / "archive/pferi_v2/task_runs/dual_sample_confirmation"
        / "timed_operational_rehearsal_v1_retired_pair_ids.csv",
    ),
    ExclusionSource(
        "timed_operational_rehearsal_v2",
        ROOT
        / "archive/pferi_v2/task_runs/dual_sample_confirmation"
        / "2026-07-15_timed_operational_rehearsal_v2/restricted/restricted_linkage.csv",
    ),
)


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


def canonical_pair_ids(path: Path) -> set[str]:
    rows, fields = read_csv(path)
    if "canonical_pair_id" not in fields:
        raise ValueError(f"canonical pair manifest lacks canonical_pair_id: {path}")
    pair_ids = [row["canonical_pair_id"].strip() for row in rows]
    if any(not pair_id for pair_id in pair_ids):
        raise ValueError(f"blank canonical_pair_id in canonical pair manifest: {path}")
    if len(pair_ids) != len(set(pair_ids)):
        raise ValueError(f"duplicate canonical_pair_id in canonical pair manifest: {path}")
    return set(pair_ids)


def build_exclusion_rows(
    sources: Sequence[ExclusionSource],
    *,
    valid_canonical_pair_ids: set[str],
) -> tuple[list[dict[str, str | int]], dict[str, object]]:
    if not sources:
        raise ValueError("at least one exclusion source is required")

    source_paths_by_pair: dict[str, set[str]] = defaultdict(set)
    reasons_by_pair: dict[str, set[str]] = defaultdict(set)
    source_summaries: list[dict[str, object]] = []
    raw_pair_occurrences = 0

    for source in sources:
        if not source.reason_code.strip():
            raise ValueError(f"blank exclusion reason for source: {source.path}")
        if not source.path.exists():
            raise FileNotFoundError(source.path)
        rows, fields = read_csv(source.path)
        if "canonical_pair_id" not in fields:
            raise ValueError(f"source lacks canonical_pair_id: {source.path}")
        pair_ids = [row["canonical_pair_id"].strip() for row in rows]
        if any(not pair_id for pair_id in pair_ids):
            raise ValueError(f"blank canonical_pair_id in exclusion source: {source.path}")
        raw_pair_occurrences += len(pair_ids)
        relative_path = str(source.path.resolve().relative_to(ROOT))
        for pair_id in pair_ids:
            source_paths_by_pair[pair_id].add(relative_path)
            reasons_by_pair[pair_id].add(source.reason_code)
        source_summaries.append(
            {
                "reason_code": source.reason_code,
                "path": relative_path,
                "sha256": sha256_file(source.path),
                "row_count": len(pair_ids),
                "unique_pair_count": len(set(pair_ids)),
                "duplicate_pair_occurrence_count": len(pair_ids) - len(set(pair_ids)),
            }
        )

    excluded_ids = set(source_paths_by_pair)
    missing_from_canonical = sorted(excluded_ids - valid_canonical_pair_ids)
    rows = [
        {
            "exclusion_contract_version": CONTRACT_VERSION,
            "canonical_pair_id": pair_id,
            "exclusion_reason_codes": ";".join(sorted(reasons_by_pair[pair_id])),
            "source_artifact_count": len(source_paths_by_pair[pair_id]),
            "source_artifacts": ";".join(sorted(source_paths_by_pair[pair_id])),
        }
        for pair_id in sorted(excluded_ids)
    ]
    reason_counts = Counter(
        reason
        for pair_id in excluded_ids
        for reason in reasons_by_pair[pair_id]
    )
    audit = {
        "audit_version": "pferi_v2_pre_sampling_exclusion_register_audit_v1",
        "status": "PASS" if rows and not missing_from_canonical else "FAIL",
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_artifact_count": len(sources),
        "raw_pair_occurrence_count": raw_pair_occurrences,
        "excluded_unique_pair_count": len(rows),
        "duplicate_or_repeated_source_occurrence_count": raw_pair_occurrences - len(rows),
        "missing_from_canonical_pair_manifest_count": len(missing_from_canonical),
        "missing_from_canonical_pair_manifest": missing_from_canonical,
        "unique_pair_count_by_reason": dict(sorted(reason_counts.items())),
        "sources": source_summaries,
        "official_seed": None,
        "claim_boundary": (
            "This register excludes pairs exposed in pre-sampling pilot, interface, or operational rehearsal work. "
            "PASS does not choose an official seed, assign image roles, sample formal pairs, or authorize outcome collection."
        ),
    }
    return rows, audit


def write_csv(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--canonical-pairs",
        type=Path,
        default=ROOT / "work/pferi_v2/pipeline/dual_descriptor_queue/canonical_pairs.csv",
    )
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args(argv)

    valid_ids = canonical_pair_ids(args.canonical_pairs)
    rows, audit = build_exclusion_rows(DEFAULT_SOURCES, valid_canonical_pair_ids=valid_ids)
    write_csv(args.output_csv, rows)
    audit.update(
        {
            "canonical_pair_manifest": str(args.canonical_pairs.resolve().relative_to(ROOT)),
            "canonical_pair_manifest_sha256": sha256_file(args.canonical_pairs),
            "exclusion_register": str(args.output_csv.resolve().relative_to(ROOT)),
            "exclusion_register_sha256": sha256_file(args.output_csv),
        }
    )
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
