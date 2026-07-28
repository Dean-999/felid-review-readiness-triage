#!/usr/bin/env python3
"""Build the restricted image-path manifest for external fresh descriptor inference."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/frozen/pferi_v2/lynx-wild/manifest.csv"
DEFAULT_OUTPUT = ROOT / "work/pferi_v2/pipeline/descriptor_manifests/restricted_descriptor_execution_manifest.csv"
DEFAULT_AUDIT = ROOT / "work/pferi_v2/pipeline/descriptor_manifests/restricted_descriptor_execution_manifest_audit.json"
OUTPUT_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)

def build(rows: Sequence[Mapping[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    output = []
    for row in rows:
        if row.get("species") != "czechlynx" or row.get("final_freeze_image_exists") != "yes" or row.get("decode_status") != "ok":
            raise ValueError("source row is not an available, decodable CzechLynx final-freeze image")
        digest = str(row.get("final_freeze_sha256", ""))
        path = Path(str(row.get("final_freeze_image_path", "")))
        if not path.is_absolute():
            path = ROOT / path
        if len(digest) != 64 or not path.is_file():
            raise ValueError("source row has missing content hash or image path")
        output.append({"image_id": "pferi_v2_image_" + digest, "image_path_relative": str(path.relative_to(ROOT)), "content_sha256": digest})
    if len({row["image_id"] for row in output}) != len(output):
        raise ValueError("duplicate content hashes in source manifest")
    return output, {"status":"PASS", "image_count":len(output), "identity_fields_in_output":[], "claim_boundary":"Restricted execution manifest only; do not distribute to reviewers or use as an outcome dataset."}

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args(argv)
    try:
        rows, audit = build(read_csv(args.source_manifest))
        write_csv(args.output_csv, rows)
    except ValueError as exc:
        audit = {"status":"FAIL", "error":str(exc)}
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
