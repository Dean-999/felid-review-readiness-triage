#!/usr/bin/env python3
"""Materialize licensed, outcome-free Task 15I external lynx candidate images."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "data/candidate-reservoirs/photo-selection-candidate-pools"
    / "lynx_external_heterogeneous_supplement"
    / "lynx_external_heterogeneous_supplement_download_manifest.csv"
)
OUTPUT = ROOT / "data/candidate-reservoirs/task15i_independent_lynx_v1"
USER_AGENT = "felid-review-readiness-triage/task15i-independent-reservoir"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def image_id(uri: str) -> str:
    return f"task15i_image_{hashlib.sha256(uri.encode('utf-8')).hexdigest()}"


def is_open_license(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized.startswith("cc-") or "creativecommons.org" in normalized


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("refusing to write an empty manifest")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def is_image(data: bytes) -> bool:
    return (
        data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    )


def materialize_one(
    row: dict[str, str], image_dir: Path, timeout: int = 60, allow_network: bool = True
) -> dict[str, str]:
    uri = row["source_image_uri"].strip()
    identifier = image_id(uri)
    target = image_dir / f"{identifier}.jpg"
    result = {
        "candidate_image_id": identifier,
        "source_candidate_id": row["source_candidate_id"],
        "source_image_uri": uri,
        "source_dataset": row["source_dataset"],
        "source_platform": row["source_platform"],
        "species": row["species"],
        "domain_label": row["domain_label"],
        "license": row["license"],
        "attribution": row["attribution"],
        "local_relative_path": str(target.relative_to(ROOT)),
        "download_status": "",
        "bytes": "0",
        "sha256": "",
        "error": "",
    }
    if target.is_file() and target.stat().st_size > 1024:
        data = target.read_bytes()
        if is_image(data):
            result.update(download_status="already_present", bytes=str(len(data)), sha256=sha256_bytes(data))
            return result
    if not allow_network:
        result.update(download_status="failed", error="not_materialized")
        return result
    try:
        request = urllib.request.Request(uri, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
        if len(data) <= 1024 or not is_image(data):
            raise ValueError("response was not a valid image larger than 1 KiB")
        image_dir.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(data)
        os.replace(temporary, target)
        result.update(download_status="downloaded", bytes=str(len(data)), sha256=sha256_bytes(data))
    # A single remote read failure must be recorded, never abort the full
    # resumable reservoir materialization.
    except Exception as error:  # noqa: BLE001 - network stacks vary by backend
        result.update(download_status="failed", error=repr(error))
    return result


def materialize(
    rows: list[dict[str, str]], output: Path, workers: int, timeout: int, allow_network: bool
) -> list[dict[str, str]]:
    image_dir = output / "images"
    completed: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(materialize_one, row, image_dir, timeout, allow_network)
            for row in rows
        ]
        for index, future in enumerate(as_completed(futures), start=1):
            completed.append(future.result())
            if index % 100 == 0 or index == len(rows):
                successes = sum(row["download_status"] in {"downloaded", "already_present"} for row in completed)
                print(f"materialized {index}/{len(rows)}; usable={successes}", flush=True)
    return sorted(completed, key=lambda row: row["candidate_image_id"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--audit-existing-only", action="store_true")
    args = parser.parse_args()
    source_rows = read_csv(args.source)
    licensed_rows = [row for row in source_rows if is_open_license(row.get("license", ""))]
    by_uri = {row["source_image_uri"]: row for row in licensed_rows}
    rows = [by_uri[uri] for uri in sorted(by_uri)]
    if args.limit is not None:
        rows = rows[: args.limit]
    if not rows:
        raise ValueError("no explicitly Creative Commons candidate images selected")
    if args.output.exists() and not (args.output / "images").exists():
        raise FileExistsError(f"refusing to use a non-reservoir output directory: {args.output}")
    completed = materialize(
        rows, args.output, args.workers, args.timeout, not args.audit_existing_only
    )
    write_csv(args.output / "materialized_image_manifest.csv", completed)
    successful = sorted(
        (
            row
            for row in completed
            if row["download_status"] in {"downloaded", "already_present"}
        ),
        key=lambda row: (row["sha256"], row["candidate_image_id"]),
    )
    eligible: list[dict[str, str]] = []
    seen_hashes: set[str] = set()
    for row in successful:
        if row["sha256"] not in seen_hashes:
            eligible.append(row)
            seen_hashes.add(row["sha256"])
    write_csv(args.output / "eligible_unique_image_manifest.csv", eligible)
    audit = {
        "audit_version": "pferi_v2_task15i_independent_reservoir_materialization_v1",
        "source_manifest": str(args.source.relative_to(ROOT)),
        "source_manifest_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "source_row_count": len(source_rows),
        "explicit_creative_commons_unique_uri_count": len(by_uri),
        "attempted_unique_uri_count": len(rows),
        "materialized_image_count": len(successful),
        "failed_image_count": sum(row["download_status"] == "failed" for row in completed),
        "eligible_unique_content_image_count": len(eligible),
        "duplicate_content_exclusion_count": len(successful) - len(eligible),
        "outcome_accessed": False,
        "claim_boundary": "This package materializes licensed external candidate images only. It does not establish image disjointness, pair capacity, reviewability labels, model performance, calibration, or confirmation.",
    }
    (args.output / "materialization_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
