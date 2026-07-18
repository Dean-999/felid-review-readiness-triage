#!/usr/bin/env python3
"""Remove only reconstructable v2 work images with a unique frozen counterpart.

The command is a dry run unless ``--apply`` is supplied.  Canonical hashes that
occur in more than one frozen scientific scope are deliberately skipped because
they may represent unresolved cross-label duplication.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FROZEN_ROOT = Path("data/frozen/pferi_v2")
WORK_ROOT = Path("work/pferi_v2")
DEFAULT_RELOCATION_MANIFEST = Path(
    "docs/project-governance/structure/2026-07-17_pferi_v1_v2_relocation_manifest.csv"
)
DEFAULT_DEDUP_MANIFEST = Path("artifacts/manifests/pferi_v2_work_image_dedup.csv")
IMAGE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png"}


@dataclass(frozen=True)
class Duplicate:
    work_path: str
    canonical_path: str
    size_bytes: int
    sha256: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_known_hashes(root: Path) -> dict[str, str]:
    manifest = root / DEFAULT_RELOCATION_MANIFEST
    if not manifest.exists():
        return {}
    with manifest.open(newline="", encoding="utf-8") as handle:
        return {
            row["destination_path"]: row["sha256"]
            for row in csv.DictReader(handle)
            if row.get("destination_path") and row.get("sha256")
        }


def image_paths(root: Path, relative_root: Path) -> list[Path]:
    base = root / relative_root
    if not base.exists():
        return []
    return sorted(
        path
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def hash_for(path: Path, root: Path, known: dict[str, str]) -> str:
    relative = path.relative_to(root).as_posix()
    return known.get(relative) or sha256(path)


def canonical_hash_index(
    root: Path, candidate_sizes: set[int] | None = None
) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in image_paths(root, FROZEN_ROOT):
        if candidate_sizes is not None and path.stat().st_size not in candidate_sizes:
            continue
        index.setdefault(sha256(path), []).append(path)
    return index


def analyze_duplicates(root: Path = ROOT) -> tuple[list[Duplicate], int]:
    work_images = image_paths(root, WORK_ROOT)
    candidate_sizes = {path.stat().st_size for path in work_images}
    canonical = canonical_hash_index(root, candidate_sizes)
    rows: list[Duplicate] = []
    for work_path in work_images:
        digest = sha256(work_path)
        matches = canonical.get(digest, [])
        if len(matches) != 1:
            continue
        retained = matches[0]
        if retained.stat().st_size != work_path.stat().st_size:
            raise ValueError(f"Hash/size inconsistency: {work_path} and {retained}")
        rows.append(
            Duplicate(
                work_path=work_path.relative_to(root).as_posix(),
                canonical_path=retained.relative_to(root).as_posix(),
                size_bytes=work_path.stat().st_size,
                sha256=digest,
            )
        )
    ambiguous = sum(1 for paths in canonical.values() if len(paths) > 1)
    return sorted(rows, key=lambda row: row.work_path), ambiguous


def find_duplicates(root: Path = ROOT) -> list[Duplicate]:
    rows, _ = analyze_duplicates(root)
    return rows


def ambiguous_canonical_hash_count(root: Path = ROOT) -> int:
    _, ambiguous = analyze_duplicates(root)
    return ambiguous


def write_manifest(path: Path, rows: list[Duplicate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["work_path", "canonical_path", "size_bytes", "sha256"],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "work_path": row.work_path,
                    "canonical_path": row.canonical_path,
                    "size_bytes": row.size_bytes,
                    "sha256": row.sha256,
                }
            )
    temporary.replace(path)


def apply_duplicates(root: Path, rows: list[Duplicate]) -> int:
    verified_canonical: dict[Path, str] = {}
    work_paths: list[Path] = []
    for row in rows:
        work = root / row.work_path
        canonical = root / row.canonical_path
        if not work.is_file() or not canonical.is_file():
            raise FileNotFoundError(f"Missing work/canonical pair: {work} -> {canonical}")
        canonical_digest = verified_canonical.get(canonical)
        if canonical_digest is None:
            canonical_digest = sha256(canonical)
            verified_canonical[canonical] = canonical_digest
        if canonical_digest != row.sha256:
            raise ValueError(f"Canonical hash changed: {canonical}")
        if sha256(work) != row.sha256:
            raise ValueError(f"Work hash changed: {work}")
        if work.stat().st_size != row.size_bytes:
            raise ValueError(f"Work size changed: {work}")
        work_paths.append(work)
    for path in work_paths:
        path.unlink()
    for directory in sorted(
        {path.parent for path in work_paths}, key=lambda path: len(path.parts), reverse=True
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
    return len(work_paths)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_DEDUP_MANIFEST)
    args = parser.parse_args()

    rows, ambiguous = analyze_duplicates(ROOT)
    report = {
        "mode": "apply" if args.apply else "dry-run",
        "duplicateWorkImages": len(rows),
        "reclaimableBytes": sum(row.size_bytes for row in rows),
        "ambiguousCanonicalHashesSkipped": ambiguous,
    }
    print(json.dumps(report, indent=2))
    if not args.apply:
        return
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    write_manifest(manifest, rows)
    removed = apply_duplicates(ROOT, rows)
    print(json.dumps({"status": "PASS", "removed": removed, "manifest": str(manifest)}, indent=2))


if __name__ == "__main__":
    main()
