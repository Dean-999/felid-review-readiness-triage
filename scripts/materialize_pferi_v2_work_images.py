#!/usr/bin/env python3
"""Restore deduplicated PF-ERI v2 work images from canonical frozen inputs."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.deduplicate_pferi_v2_work_images import (
    DEFAULT_DEDUP_MANIFEST,
    FROZEN_ROOT,
    ROOT,
    WORK_ROOT,
    Duplicate,
    sha256,
)


def read_manifest(path: Path) -> list[Duplicate]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            Duplicate(
                work_path=row["work_path"],
                canonical_path=row["canonical_path"],
                size_bytes=int(row["size_bytes"]),
                sha256=row["sha256"],
            )
            for row in csv.DictReader(handle)
        ]


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def restore_rows(root: Path, rows: list[Duplicate], apply: bool = False) -> int:
    planned: list[tuple[Path, Path, Duplicate]] = []
    verified_canonical: dict[Path, str] = {}
    for row in rows:
        work = root / row.work_path
        canonical = root / row.canonical_path
        if not is_within(work, root / WORK_ROOT):
            raise ValueError(f"Work path escapes allowed root: {work}")
        if not is_within(canonical, root / FROZEN_ROOT):
            raise ValueError(f"Canonical path escapes allowed root: {canonical}")
        if not canonical.is_file():
            raise ValueError(f"Canonical source missing or changed: {canonical}")
        canonical_digest = verified_canonical.get(canonical)
        if canonical_digest is None:
            canonical_digest = sha256(canonical)
            verified_canonical[canonical] = canonical_digest
        if canonical_digest != row.sha256:
            raise ValueError(f"Canonical source missing or changed: {canonical}")
        if canonical.stat().st_size != row.size_bytes:
            raise ValueError(f"Canonical size changed: {canonical}")
        if work.exists():
            if not work.is_file() or sha256(work) != row.sha256:
                raise FileExistsError(f"Refusing to overwrite nonmatching work file: {work}")
            continue
        planned.append((canonical, work, row))
    if not apply:
        return len(planned)
    for canonical, work, _ in planned:
        work.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(canonical, work)
    return len(planned)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_DEDUP_MANIFEST)
    args = parser.parse_args()
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    rows = read_manifest(manifest)
    count = restore_rows(ROOT, rows, apply=args.apply)
    print(
        json.dumps(
            {"status": "PASS", "mode": "apply" if args.apply else "dry-run", "restored": count},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
