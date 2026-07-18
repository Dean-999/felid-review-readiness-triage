#!/usr/bin/env python3
"""Physically separate PF-ERI v1 evidence, v2 results, inputs, and work artifacts.

The command is a dry run unless ``--apply`` is supplied.  It never infers a
scientific generation from a bare ``v1``/``v2`` filename token; every move is
controlled by an explicit path-prefix mapping.  Before applying, it writes a
SHA-256 relocation manifest so every moved byte has an old/new path record.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT
    / "docs/project-governance/structure/2026-07-17_pferi_v1_v2_relocation_manifest.csv"
)
DEFAULT_AUDIT = (
    ROOT
    / "docs/project-governance/structure/2026-07-17_pferi_v1_v2_relocation_audit.json"
)
DEFAULT_DEDUP_MANIFEST = ROOT / "artifacts/manifests/pferi_v2_work_image_dedup.csv"
DEFAULT_CLEANUP_MANIFEST = (
    ROOT / "docs/project-governance/structure/2026-07-17_output_cleanup_manifest.csv"
)

LEGACY_OUTPUT_AREAS = (
    "candidate-reservoirs",
    "data-foundation",
    "manuscript",
    "modeling-validation",
    "photo-freeze",
    "photo-selection",
    "project-governance",
    "review-routing",
)

# More-specific prefixes must win.  ``rewrite_text`` and ``relocate_path`` sort
# this table by source length, so declaration order is only for readability.
PATH_MAPPINGS: tuple[tuple[str, str], ...] = (
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/"
        "reviewer_interface_dry_run/2026-07-14_v2_blinded_interface_dry_run_v3/"
        "independent_browser_audit/returned_audits/2026-07-14_a001_completed/"
        "PF_ERI_V2_INTERFACE_AUDIT_DELIVERY.zip",
        "artifacts/transfers/pferi_v2/PF_ERI_V2_INTERFACE_AUDIT_DELIVERY_returned_a001.zip",
    ),
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/"
        "reviewer_interface_dry_run/2026-07-14_v2_blinded_interface_dry_run_v3/"
        "independent_browser_audit/PF_ERI_V2_INTERFACE_AUDIT_DELIVERY.zip",
        "artifacts/transfers/pferi_v2/PF_ERI_V2_INTERFACE_AUDIT_DELIVERY_original.zip",
    ),
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/local_match_runs/"
        "2026-07-14_gpu_t4_protocol_v2/PF_ERI_FINAL_RESULTS_GPU/smoke_input",
        "work/pferi_v2/measurement_feasibility/local_match_return/"
        "2026-07-14_gpu_t4_protocol_v2/smoke_input",
    ),
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/local_match_runs/"
        "2026-07-14_gpu_t4_protocol_v2/PF_ERI_FINAL_RESULTS_GPU/input",
        "work/pferi_v2/measurement_feasibility/local_match_return/"
        "2026-07-14_gpu_t4_protocol_v2/input",
    ),
    (
        "outputs/v2_candidate_reservoir/dual_sample_confirmation/"
        "2026-07-15_timed_operational_rehearsal_v2/reviewer_view",
        "work/pferi_v2/workbook04/timed_operational_rehearsal_v2/reviewer_view",
    ),
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/"
        "reviewer_interface_dry_run",
        "work/pferi_v2/measurement_feasibility/reviewer_interface_dry_run",
    ),
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/"
        "structural_oracle_annotation_package",
        "work/pferi_v2/measurement_feasibility/structural_oracle_annotation_package",
    ),
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/"
        "v2_local_match_execution_package",
        "work/pferi_v2/measurement_feasibility/local_match_execution_package",
    ),
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/"
        "v2_quality_execution_package",
        "work/pferi_v2/measurement_feasibility/quality_execution_package",
    ),
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/"
        "final_local_match_package_v2",
        "work/pferi_v2/measurement_feasibility/final_local_match_package_v2",
    ),
    (
        "outputs/v2_candidate_reservoir/v2_descriptor_execution_package",
        "work/pferi_v2/descriptor_execution_package",
    ),
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/"
        "automatic_quality_gpu_execution_bundle.zip",
        "artifacts/transfers/pferi_v2/automatic_quality_gpu_execution_bundle.zip",
    ),
    (
        "outputs/v2_candidate_reservoir/measurement_feasibility_pilot/automatic_quality_runs/"
        "2026-07-14_gpu_cuda_protocol_v1/PF_ERI_V2_AUTOMATIC_QUALITY_RESULTS.zip",
        "artifacts/transfers/pferi_v2/PF_ERI_V2_AUTOMATIC_QUALITY_RESULTS.zip",
    ),
    (
        "outputs/v2_candidate_reservoir/full_frame_local_match_execution/2026-07-16_v1/"
        "PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip",
        "artifacts/transfers/pferi_v2/PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip",
    ),
    ("outputs/final_freeze", "data/frozen/pferi_v2"),
    ("outputs/v2_candidate_reservoir", "outputs/pferi_v2"),
    ("outputs/.ua", ".ua/outputs-analysis"),
    (
        "outputs/PF-ERI_full_project_adversarial_hv_report.pdf",
        "archive/pferi_v1/reports/PF-ERI_full_project_adversarial_hv_report.pdf",
    ),
    *tuple(
        (f"outputs/{area}", f"archive/pferi_v1/outputs/{area}")
        for area in LEGACY_OUTPUT_AREAS
    ),
)

ACTIVE_REWRITE_DIRECTORIES = (
    "colab",
    "docs",
    "gpu",
    "models",
    "schemas",
    "scripts",
    "sessions",
    "sources",
    "tests",
)
ACTIVE_REWRITE_FILES = (
    ".gitignore",
    "AGENTS.md",
    "PROJECT_RULES.md",
    "README.md",
    "outputs/README.md",
)
TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".html",
    ".ini",
    ".ipynb",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}
REWRITE_EXCLUSIONS = {
    "docs/superpowers/plans/2026-07-17-pferi-v1-v2-layout-separation.md",
    "docs/project-governance/structure/2026-07-17_output_cleanup_manifest.csv",
    "docs/project-governance/structure/2026-07-17_pferi_v1_v2_relocation_manifest.csv",
    "docs/project-governance/structure/2026-07-17_pferi_v1_v2_relocation_audit.json",
    "scripts/migrate_pferi_v1_v2_layout.py",
    "tests/test_migrate_pferi_v1_v2_layout.py",
}


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path


def ordered_mappings() -> tuple[tuple[str, str], ...]:
    return tuple(sorted(PATH_MAPPINGS, key=lambda pair: len(pair[0]), reverse=True))


def relocate_path(relative_path: str) -> str | None:
    normalized = relative_path.replace(os.sep, "/").rstrip("/")
    for old, new in ordered_mappings():
        if normalized == old or normalized.startswith(old + "/"):
            return new + normalized[len(old) :]
    return None


def rewrite_text(text: str) -> str:
    rewritten = text
    protected: dict[str, str] = {}
    for index, (_, new) in enumerate(ordered_mappings()):
        token = f"__PFERI_MIGRATION_DESTINATION_{index}__"
        if new in rewritten:
            rewritten = rewritten.replace(new, token)
            protected[token] = new
    for old, new in ordered_mappings():
        rewritten = rewritten.replace(old, new)
    for token, destination in protected.items():
        rewritten = rewritten.replace(token, destination)
    return rewritten


def original_path(destination_path: str) -> str | None:
    normalized = destination_path.replace(os.sep, "/").rstrip("/")
    inverse = sorted(PATH_MAPPINGS, key=lambda pair: len(pair[1]), reverse=True)
    for old, new in inverse:
        if normalized == new or normalized.startswith(new + "/"):
            return old + normalized[len(new) :]
    return None


def repair_manifest(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    repaired = 0
    for row in rows:
        destination = row["destination_path"]
        duplicated_archive_prefix = "archive/pferi_v1/archive/pferi_v1/outputs/"
        if destination.startswith(duplicated_archive_prefix):
            destination = "archive/pferi_v1/outputs/" + destination[len(duplicated_archive_prefix) :]
        source = original_path(destination)
        if source is None:
            raise ValueError(f"Cannot reconstruct source path for {destination}")
        if row["source_path"] != source or row["destination_path"] != destination:
            repaired += 1
        row["source_path"] = source
        row["destination_path"] = destination
    write_manifest(path, rows)
    return repaired


def build_plan(root: Path = ROOT) -> list[Move]:
    outputs = root / "outputs"
    if not outputs.exists():
        return []
    moves: list[Move] = []
    destination_sources: dict[Path, Path] = {}
    for source in sorted(outputs.rglob("*")):
        if not source.is_file() and not source.is_symlink():
            continue
        relative = source.relative_to(root).as_posix()
        destination_relative = relocate_path(relative)
        if destination_relative is None:
            continue
        destination = root / destination_relative
        if destination in destination_sources:
            raise ValueError(
                f"Two sources map to one destination: {destination_sources[destination]} and {source}"
            )
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Refusing to overwrite migration destination: {destination}")
        destination_sources[destination] = source
        moves.append(Move(source=source, destination=destination))
    return moves


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_rows(root: Path, plan: list[Move]) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for move in plan:
        source_relative = move.source.relative_to(root).as_posix()
        rows.append(
            {
                "source_path": source_relative,
                "destination_path": move.destination.relative_to(root).as_posix(),
                "size_bytes": move.source.lstat().st_size,
                "sha256": sha256(move.source),
            }
        )
    return rows


def reconcile_manifest(
    path: Path,
    dedup_manifest: Path = DEFAULT_DEDUP_MANIFEST,
    cleanup_manifest: Path = DEFAULT_CLEANUP_MANIFEST,
    root: Path = ROOT,
) -> dict[str, int]:
    """Rebuild raw SHA-256 values for the current post-migration repository state."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    deduplicated: dict[str, dict[str, str]] = {}
    if dedup_manifest.exists():
        with dedup_manifest.open(newline="", encoding="utf-8") as handle:
            deduplicated = {row["work_path"]: row for row in csv.DictReader(handle)}
    cleaned: dict[str, dict[str, str]] = {}
    if cleanup_manifest.exists():
        with cleanup_manifest.open(newline="", encoding="utf-8") as handle:
            cleaned = {row["removed_path"]: row for row in csv.DictReader(handle)}

    present_count = 0
    deduplicated_count = 0
    cleaned_count = 0
    canonical_hashes: dict[Path, str] = {}
    for row in rows:
        destination = root / row["destination_path"]
        if destination.is_file():
            row["size_bytes"] = destination.stat().st_size
            row["sha256"] = sha256(destination)
            present_count += 1
            continue
        duplicate = deduplicated.get(row["destination_path"])
        cleanup = cleaned.get(row["destination_path"])
        if duplicate is None and cleanup is not None:
            if (
                int(cleanup["size_bytes"]) != int(row["size_bytes"])
                or cleanup["sha256"] != row["sha256"]
            ):
                raise ValueError(f"Cleanup manifest does not match relocation bytes: {destination}")
            cleaned_count += 1
            continue
        if duplicate is None:
            raise FileNotFoundError(
                f"Relocation destination is missing without a dedup or cleanup record: {destination}"
            )
        canonical = root / duplicate["canonical_path"]
        if not canonical.is_file():
            raise FileNotFoundError(f"Dedup canonical file is missing: {canonical}")
        canonical_digest = canonical_hashes.get(canonical)
        if canonical_digest is None:
            canonical_digest = sha256(canonical)
            canonical_hashes[canonical] = canonical_digest
        if canonical_digest != duplicate["sha256"]:
            raise ValueError(f"Dedup canonical hash mismatch: {canonical}")
        row["size_bytes"] = int(duplicate["size_bytes"])
        row["sha256"] = duplicate["sha256"]
        deduplicated_count += 1
    write_manifest(path, rows)
    return {
        "rowCount": len(rows),
        "presentDestinationCount": present_count,
        "deduplicatedDestinationCount": deduplicated_count,
        "cleanedDestinationCount": cleaned_count,
    }


def write_manifest(path: Path, rows: list[dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_path", "destination_path", "size_bytes", "sha256"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def active_text_paths(root: Path) -> list[Path]:
    paths: set[Path] = set()
    for directory in ACTIVE_REWRITE_DIRECTORIES:
        base = root / directory
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                paths.add(path)
    for name in ACTIVE_REWRITE_FILES:
        path = root / name
        if path.is_file():
            paths.add(path)
    return sorted(paths)


def rewrite_active_references(root: Path = ROOT) -> list[str]:
    changed: list[str] = []
    for path in active_text_paths(root):
        relative = path.relative_to(root).as_posix()
        if relative in REWRITE_EXCLUSIONS:
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rewritten = rewrite_text(original)
        if rewritten == original:
            continue
        path.write_text(rewritten, encoding="utf-8")
        changed.append(relative)
    return changed


def remove_empty_directories(root: Path) -> None:
    candidates = [root / "outputs"]
    for candidate in candidates:
        if not candidate.exists():
            continue
        for directory in sorted(
            (path for path in candidate.rglob("*") if path.is_dir()),
            key=lambda item: len(item.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass


def apply_plan(root: Path, plan: list[Move], manifest: Path, audit: Path) -> dict:
    rows = manifest_rows(root, plan)
    write_manifest(manifest, rows)
    moved = 0
    for move in plan:
        move.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(move.source), str(move.destination))
        moved += 1
    remove_empty_directories(root)
    rewritten = rewrite_active_references(root)
    payload = {
        "status": "PASS",
        "appliedAt": datetime.now(timezone.utc).isoformat(),
        "movedFileCount": moved,
        "rewrittenActiveFileCount": len(rewritten),
        "rewrittenActiveFiles": rewritten,
        "manifest": str(manifest.relative_to(root)),
        "boundary": (
            "PF-ERI v1 historical bytes are archived; PF-ERI v2 results, frozen inputs, "
            "work packages, and transfer artifacts occupy separate roots."
        ),
    }
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def summary(plan: list[Move], root: Path) -> dict:
    counts: Counter[str] = Counter()
    total = 0
    for move in plan:
        relative = move.destination.relative_to(root).as_posix()
        counts[relative.split("/", 1)[0]] += 1
        total += move.source.lstat().st_size
    return {"files": len(plan), "bytes": total, "destinationRoots": dict(sorted(counts.items()))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="apply the validated migration plan")
    parser.add_argument(
        "--repair-manifest",
        action="store_true",
        help="repair source/destination columns after an interrupted metadata rewrite",
    )
    parser.add_argument(
        "--reconcile-manifest",
        action="store_true",
        help="replace non-raw historical fingerprints with verified raw SHA-256 values",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--dedup-manifest", type=Path, default=DEFAULT_DEDUP_MANIFEST)
    parser.add_argument("--cleanup-manifest", type=Path, default=DEFAULT_CLEANUP_MANIFEST)
    args = parser.parse_args()

    if args.repair_manifest:
        repaired = repair_manifest(args.manifest.resolve())
        print(json.dumps({"status": "PASS", "repairedRows": repaired}, indent=2))
        return

    if args.reconcile_manifest:
        report = reconcile_manifest(
            args.manifest.resolve(),
            args.dedup_manifest.resolve(),
            args.cleanup_manifest.resolve(),
        )
        report["status"] = "PASS"
        audit_path = args.audit.resolve()
        audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
        audit_payload["manifestHashReconciliation"] = {
            "reason": (
                "Understand Anything contentHash values are semantic analysis fingerprints, "
                "not raw file SHA-256 values. The relocation manifest was rebuilt from current "
                "destination bytes; intentionally removed work copies are verified through the "
                "deduplication manifest and canonical frozen files, while later allowlisted "
                "cleanup is verified through the cleanup manifest."
            ),
            "reconciledAt": datetime.now(timezone.utc).isoformat(),
            **report,
        }
        audit_path.write_text(json.dumps(audit_payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return

    plan = build_plan(ROOT)
    report = summary(plan, ROOT)
    report["mode"] = "apply" if args.apply else "dry-run"
    print(json.dumps(report, indent=2))
    if not args.apply:
        return
    if not plan:
        raise SystemExit("No old-layout files found; migration was not applied.")
    payload = apply_plan(ROOT, plan, args.manifest.resolve(), args.audit.resolve())
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
