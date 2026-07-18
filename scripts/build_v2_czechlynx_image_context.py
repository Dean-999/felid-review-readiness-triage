#!/usr/bin/env python3
"""Create the neutral v2 CzechLynx image-context manifest from the final freeze.

The source manifest is accessed only to verify frozen image availability and
content identity. Identity labels, source paths, filenames, licenses, and
other provenance details are deliberately omitted from the v2 context export.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/frozen/pferi_v2/lynx-wild/manifest.csv"
DEFAULT_OUTPUT = ROOT / "outputs/pferi_v2/czechlynx_v2_image_context.csv"
DEFAULT_AUDIT = ROOT / "outputs/pferi_v2/czechlynx_v2_image_context_audit.json"
REQUIRED_SOURCE_COLUMNS = {"species", "decode_status", "final_freeze_image_exists", "final_freeze_sha256", "final_freeze_image_path"}
OUTPUT_COLUMNS = ["image_id", "image_decode_status", "illumination_metadata", "source_camera_context"]


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


def build_context(source_rows: Sequence[Mapping[str, str]], source_headers: Sequence[str] | None = None) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Return neutral image context and an audit; raise when the freeze is unsuitable."""
    source_headers = list(source_headers or (list(source_rows[0].keys()) if source_rows else []))
    missing = REQUIRED_SOURCE_COLUMNS.difference(source_headers)
    if missing:
        raise ValueError(f"source manifest missing columns: {', '.join(sorted(missing))}")
    if not source_rows:
        raise ValueError("source manifest is empty")
    rows: list[dict[str, str]] = []
    for row in source_rows:
        if str(row.get("species", "")).lower() != "czechlynx":
            raise ValueError("source manifest contains a non-CzechLynx row")
        if row.get("final_freeze_image_exists") != "yes":
            raise ValueError("source manifest contains an image absent from final freeze")
        if row.get("decode_status") != "ok":
            raise ValueError("source manifest contains a nondecodable image")
        content_hash = str(row.get("final_freeze_sha256", "")).lower()
        if len(content_hash) != 64 or any(character not in "0123456789abcdef" for character in content_hash):
            raise ValueError("source manifest contains an invalid final-freeze content hash")
        rows.append({
            "image_id": "pferi_v2_image_" + content_hash,
            "image_decode_status": "ok",
            "illumination_metadata": "unknown_not_in_freeze_manifest",
            "source_camera_context": "unknown_not_in_freeze_manifest",
        })
    duplicate_ids = sum(count - 1 for count in Counter(row["image_id"] for row in rows).values() if count > 1)
    if duplicate_ids:
        raise ValueError("source manifest contains duplicate final-freeze content hashes")
    audit = {
        "status": "PASS",
        "source_row_count": len(source_rows),
        "output_image_count": len(rows),
        "duplicate_content_hash_count": duplicate_ids,
        "identity_or_path_columns_in_output": [],
        "illumination_metadata_status": "unknown_not_in_freeze_manifest",
        "source_camera_context_status": "unknown_not_in_freeze_manifest",
        "claim_boundary": "This neutral context manifest establishes v2 image availability only. It is not a descriptor queue, pair reservoir, feature table, or outcome dataset.",
    }
    return rows, audit


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args(argv)
    source_rows, headers = read_csv(args.source_manifest)
    try:
        rows, audit = build_context(source_rows, headers)
    except ValueError as error:
        audit = {"status": "FAIL", "error": str(error)}
        args.audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 1
    audit["source_manifest"] = str(args.source_manifest.relative_to(ROOT)) if args.source_manifest.is_relative_to(ROOT) else str(args.source_manifest)
    audit["source_manifest_sha256"] = file_sha256(args.source_manifest)
    write_csv(args.output_csv, rows, OUTPUT_COLUMNS)
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
