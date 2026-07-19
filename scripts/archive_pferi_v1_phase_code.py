#!/usr/bin/env python3
"""Archive inactive PF-ERI v1 Phase 7–19 source and directly coupled tests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = ROOT / "archive/pferi_v1/reproducibility"
DEFAULT_MANIFEST = (
    ROOT
    / "docs/project-governance/structure/2026-07-18_pferi_v1_phase_code_archive_manifest.csv"
)
PHASE_RE = re.compile(r"(?:^|_)(?:phase|legacy-code)(7|8|9|1[0-9])(?=[a-z_]|$)", re.IGNORECASE)


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_scripts(root: Path) -> list[Path]:
    scripts = root / "scripts"
    return sorted(path for path in scripts.glob("*.py") if PHASE_RE.search(path.stem))


def selected_tests(root: Path, scripts: list[Path]) -> list[Path]:
    stems = {path.stem for path in scripts}
    selected: list[Path] = []
    for path in sorted((root / "tests").glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        if PHASE_RE.search(path.stem) or any(
            f"scripts.{stem}" in text or f"scripts import {stem}" in text
            for stem in stems
        ):
            selected.append(path)
    return selected


def build_plan(root: Path = ROOT) -> list[Move]:
    scripts = selected_scripts(root)
    tests = selected_tests(root, scripts)
    plan = [
        Move(path, root / "archive/pferi_v1/reproducibility/scripts" / path.name)
        for path in scripts
    ] + [
        Move(path, root / "archive/pferi_v1/reproducibility/tests" / path.name)
        for path in tests
    ]
    destinations: set[Path] = set()
    for move in plan:
        if move.destination in destinations or move.destination.exists():
            raise FileExistsError(f"Archive destination already exists: {move.destination}")
        destinations.add(move.destination)
    return plan


def source_commit(root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def apply_plan(root: Path, plan: list[Move], manifest: Path) -> None:
    commit = source_commit(root)
    rows = []
    for move in plan:
        rows.append(
            {
                "source_path": move.source.relative_to(root).as_posix(),
                "archive_path": move.destination.relative_to(root).as_posix(),
                "size_bytes": move.source.stat().st_size,
                "sha256": sha256(move.source),
                "source_commit": commit,
            }
        )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    append = manifest.exists() and manifest.stat().st_size > 0
    with manifest.open("a" if append else "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_path", "archive_path", "size_bytes", "sha256", "source_commit"],
            lineterminator="\n",
        )
        if not append:
            writer.writeheader()
        writer.writerows(rows)
    for move in plan:
        move.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(move.source), str(move.destination))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    plan = build_plan(ROOT)
    script_count = sum(move.source.parent == ROOT / "scripts" for move in plan)
    test_count = len(plan) - script_count
    byte_count = sum(move.source.stat().st_size for move in plan)
    print(
        f"mode={'apply' if args.apply else 'dry-run'} scripts={script_count} "
        f"tests={test_count} files={len(plan)} bytes={byte_count}"
    )
    if args.apply:
        apply_plan(ROOT, plan, args.manifest.resolve())
        print(f"manifest={args.manifest.resolve()}")


if __name__ == "__main__":
    main()
