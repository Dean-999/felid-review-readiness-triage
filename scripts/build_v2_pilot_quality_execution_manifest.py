#!/usr/bin/env python3
"""Create the image-only execution manifest for the restricted v2 quality pilot."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(pilot_rows: Sequence[dict[str, str]], canonical_rows: Sequence[dict[str, str]], execution_rows: Sequence[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    pilot_ids = {row["canonical_pair_id"] for row in pilot_rows if row.get("pilot_inclusion_status") == "included"}
    if len(pilot_ids) != len(pilot_rows):
        raise ValueError("pilot rows must be unique included canonical pairs")
    selected_pairs = [row for row in canonical_rows if row.get("canonical_pair_id") in pilot_ids]
    if len(selected_pairs) != len(pilot_ids):
        raise ValueError("pilot pair does not resolve exactly once")
    selected_ids = sorted({row[key] for row in selected_pairs for key in ("endpoint_a_image_id", "endpoint_b_image_id")})
    execution_by_id = {row["image_id"]: row for row in execution_rows}
    if len(execution_by_id) != len(execution_rows):
        raise ValueError("execution manifest has duplicate image IDs")
    if set(selected_ids).difference(execution_by_id):
        raise ValueError("pilot image missing from restricted execution manifest")
    rows = [{key: execution_by_id[image_id][key] for key in OUTPUT_COLUMNS} for image_id in selected_ids]
    if any(any(token in key.lower() for token in ("identity", "outcome", "review", "route", "rank", "score", "feature")) for key in OUTPUT_COLUMNS):
        raise ValueError("output columns are not restricted")
    return rows, {"status": "PASS", "pilot_pair_count": len(pilot_ids), "unique_image_count": len(rows), "claim_boundary": "Restricted image execution manifest only; it contains no outcome, identity, review, route, rank, score, or feature fields."}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-manifest", type=Path, required=True)
    parser.add_argument("--canonical-pairs", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args(argv)
    pilot, pilot_headers = read_csv(args.pilot_manifest)
    canonical, canonical_headers = read_csv(args.canonical_pairs)
    execution, execution_headers = read_csv(args.execution_manifest)
    if execution_headers != OUTPUT_COLUMNS or "canonical_pair_id" not in pilot_headers or not {"canonical_pair_id", "endpoint_a_image_id", "endpoint_b_image_id"}.issubset(canonical_headers):
        raise ValueError("input manifest headers violate the locked v2 contracts")
    rows, audit = build(pilot, canonical, execution)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader(); writer.writerows(rows)
    audit.update({"source_pilot_manifest_sha256": sha256(args.pilot_manifest), "source_canonical_pairs_sha256": sha256(args.canonical_pairs), "source_execution_manifest_sha256": sha256(args.execution_manifest), "output_manifest_sha256": sha256(args.output_csv)})
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
