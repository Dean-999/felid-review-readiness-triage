#!/usr/bin/env python3
"""Build an image-only external descriptor manifest for Task 15I-C."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/candidate-reservoirs/task15i_independent_lynx_v1/eligible_unique_image_manifest.csv"
OUTPUT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-25_task15i_descriptor_execution_manifest_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(source: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    output_rows = []
    for row in rows:
        source_path = ROOT / row["local_relative_path"]
        if not source_path.is_file() or sha256(source_path) != row["sha256"]:
            raise ValueError(f"source integrity failure: {row['candidate_image_id']}")
        output_rows.append(
            {
                "image_id": row["candidate_image_id"],
                "image_path_relative": row["local_relative_path"],
                "content_sha256": row["sha256"],
            }
        )
    output_rows.sort(key=lambda row: row["image_id"])
    if len({row["image_id"] for row in output_rows}) != len(output_rows):
        raise ValueError("candidate image ids are not unique")
    if len({row["content_sha256"] for row in output_rows}) != len(output_rows):
        raise ValueError("candidate image content hashes are not unique")
    output.mkdir(parents=True)
    manifest = output / "descriptor_execution_manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    audit = {
        "status": "PASS",
        "image_count": len(output_rows),
        "source_manifest": str(source.relative_to(ROOT)),
        "source_manifest_sha256": sha256(source),
        "manifest_sha256": sha256(manifest),
        "outcome_accessed": False,
        "claim_boundary": "This is an image-only descriptor execution input. It contains no human outcome, identity label, calibration outcome, or confirmation outcome.",
    }
    (output / "manifest_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksum_lines = [
        f"{sha256(path)}  {path.name}\n"
        for path in (manifest, output / "manifest_audit.json")
    ]
    (output / "CHECKSUMS.sha256").write_text("".join(checksum_lines), encoding="utf-8")
    return audit


def main() -> int:
    audit = build(SOURCE, OUTPUT)
    print(json.dumps(audit, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
