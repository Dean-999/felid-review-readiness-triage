#!/usr/bin/env python3
"""Build the restricted 3,000-image manifest for retained v2 quality measurements."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]
FORBIDDEN_TOKENS = ("identity", "outcome", "review", "route", "rank", "score", "feature")


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_rows(
    source_rows: Sequence[Mapping[str, str]],
    *,
    project_root: Path,
    expected_count: int,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    required = {"species", "final_freeze_image_path", "final_freeze_image_exists", "final_freeze_sha256"}
    if not source_rows:
        raise ValueError("source freeze manifest is empty")
    missing = sorted(required.difference(source_rows[0]))
    if missing:
        raise ValueError(f"source freeze manifest is missing columns: {missing}")

    output: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for source in source_rows:
        if source["species"] != "czechlynx":
            continue
        digest = source["final_freeze_sha256"].lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("invalid final_freeze_sha256")
        image_id = f"pferi_v2_image_{digest}"
        if image_id in seen_ids:
            raise ValueError(f"duplicate frozen image content: {image_id}")
        seen_ids.add(image_id)
        relative = Path(source["final_freeze_image_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe final freeze path: {relative}")
        absolute = (project_root / relative).resolve()
        if not absolute.is_relative_to(project_root.resolve()):
            raise ValueError(f"final freeze path escapes project root: {relative}")
        if source["final_freeze_image_exists"] != "yes" or not absolute.is_file():
            raise FileNotFoundError(absolute)
        if sha256_file(absolute) != digest:
            raise ValueError(f"content SHA256 mismatch: {relative}")
        output.append(
            {
                "image_id": image_id,
                "image_path_relative": relative.as_posix(),
                "content_sha256": digest,
            }
        )

    output.sort(key=lambda row: row["image_id"])
    if len(output) != expected_count:
        raise ValueError(f"expected {expected_count} CzechLynx images, found {len(output)}")
    if any(any(token in header.lower() for token in FORBIDDEN_TOKENS) for header in OUTPUT_COLUMNS):
        raise AssertionError("restricted output schema contains a forbidden header")
    return output, {
        "status": "PASS",
        "expected_image_count": expected_count,
        "output_image_count": len(output),
        "duplicate_image_id_count": len(output) - len({row["image_id"] for row in output}),
        "content_sha256_mismatch_count": 0,
        "claim_boundary": "Restricted immutable image-execution manifest only; no outcome, identity, review, route, rank, score, or feature fields.",
    }


def write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-freeze-manifest", type=Path, default=ROOT / "data/frozen/pferi_v2/lynx-wild/manifest.csv")
    parser.add_argument("--expected-count", type=int, default=3000)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args(argv)
    source_rows, _ = read_csv(args.source_freeze_manifest)
    rows, audit = build_rows(source_rows, project_root=ROOT, expected_count=args.expected_count)
    write_csv(args.output_csv, rows)
    audit.update(
        {
            "source_freeze_manifest": str(args.source_freeze_manifest.resolve().relative_to(ROOT)),
            "source_freeze_manifest_sha256": sha256_file(args.source_freeze_manifest),
            "output_manifest": str(args.output_csv.resolve().relative_to(ROOT)),
            "output_manifest_sha256": sha256_file(args.output_csv),
        }
    )
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
