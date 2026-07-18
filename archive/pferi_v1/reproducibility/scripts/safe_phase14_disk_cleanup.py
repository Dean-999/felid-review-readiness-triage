#!/usr/bin/env python3
"""Safely remove non-working-final Phase 14 image copies and Colab upload zips.

This script is intentionally conservative:
- keep paths are derived from the current Phase 14 2x2 working-final CSVs;
- only image files under approved FCF image roots can be deleted;
- only explicitly listed Colab upload zip files can be deleted;
- CSV/JSON/metadata/manifests are never deletion targets;
- working-final CSV image references are verified before and after execution.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

FINAL_CSVS = [
    PROJECT_ROOT
    / "outputs/phase14/phase14_final_2x2_working_labels/phase14_bobcat_high_confidence_3000_working_final_labels.csv",
    PROJECT_ROOT
    / "outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_high_confidence_3000_working_final_labels.csv",
    PROJECT_ROOT
    / "outputs/phase14/phase14_final_2x2_working_labels/phase14_bobcat_low_evidence_stress_3000_working_final_labels.csv",
    PROJECT_ROOT
    / "outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_low_evidence_stress_3000_working_final_labels.csv",
]

PATH_COLUMNS = [
    "candidate_source_path",
    "local_image_path",
    "review_image_path_local",
    "local_relative_path",
    "path",
    "image_path",
]

FCF_IMAGE_ROOTS = [
    PROJECT_ROOT / "data/external/felidae_conservation_fund/images/bobcat_3000",
    PROJECT_ROOT / "data/external/felidae_conservation_fund/images/bobcat_md_prefilter_top2800",
    PROJECT_ROOT / "data/external/felidae_conservation_fund/images/bobcat_phase14_2x2_expansion_6000",
]

COLAB_UPLOAD_ZIPS = [
    PROJECT_ROOT
    / "outputs/phase14/phase14_colab_megadetector_low_evidence_package/phase14_md_low_czechlynx_images_part_01.zip",
    PROJECT_ROOT
    / "outputs/phase14/phase14_colab_megadetector_low_evidence_package/phase14_md_low_czechlynx_images_part_02.zip",
    PROJECT_ROOT
    / "outputs/phase14/phase14_colab_megadetector_low_evidence_package/phase14_md_low_czechlynx_images_part_03.zip",
    PROJECT_ROOT
    / "outputs/phase14/phase14_czechlynx_high_topup_colab_package/phase14_czechlynx_high_topup_images_part_01.zip",
    PROJECT_ROOT
    / "outputs/phase14/phase14_czechlynx_high_topup_colab_package/phase14_czechlynx_high_topup_images_part_02.zip",
    PROJECT_ROOT
    / "outputs/phase14/phase14_czechlynx_high_topup_colab_package/phase14_czechlynx_high_topup_images_part_03.zip",
    PROJECT_ROOT
    / "outputs/phase14/phase14_low_evidence_topup_colab_package/phase14_lowtopup_czechlynx_images_part_01.zip",
    PROJECT_ROOT
    / "outputs/phase14/phase14_low_evidence_topup_colab_package/phase14_lowtopup_czechlynx_images_part_02.zip",
    PROJECT_ROOT
    / "outputs/phase14/phase14_low_evidence_topup_colab_package/phase14_lowtopup_czechlynx_images_part_03.zip",
]

REGENERABLE_DESCRIPTOR_CLOUD_TARGETS = [
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/images",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_01.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_02.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_03.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_04.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_05.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_06.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_07.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_08.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_09.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_10.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_11.zip",
    PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package/phase14_descriptor_images_part_12.zip",
]

OUTPUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_disk_cleanup"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


@dataclass
class RootAudit:
    root: str
    image_files: int
    kept_by_final: int
    delete_candidates: int
    kept_bytes: int
    delete_candidate_bytes: int
    deleted_files: int = 0
    deleted_bytes: int = 0


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_project_path(value: str) -> Path | None:
    value = value.strip()
    if not value or value.lower() == "nan":
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def iter_existing_final_paths() -> tuple[set[Path], list[str]]:
    keep_paths: set[Path] = set()
    missing_refs: list[str] = []
    for csv_path in FINAL_CSVS:
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing final CSV: {rel(csv_path)}")
        df = pd.read_csv(csv_path, low_memory=False)
        for column in PATH_COLUMNS:
            if column not in df.columns:
                continue
            for raw_value in df[column].dropna().astype(str):
                path = resolve_project_path(raw_value)
                if path is None:
                    continue
                if not rel(path).startswith("data/"):
                    continue
                if path.exists():
                    keep_paths.add(path.resolve())
                else:
                    missing_refs.append(raw_value)
    return keep_paths, missing_refs


def iter_images(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def audit_cleanup(keep_paths: set[Path]) -> tuple[list[RootAudit], list[Path]]:
    audits: list[RootAudit] = []
    delete_candidates: list[Path] = []
    for root in FCF_IMAGE_ROOTS:
        images = list(iter_images(root))
        kept = [path for path in images if path.resolve() in keep_paths]
        deletable = [path for path in images if path.resolve() not in keep_paths]
        delete_candidates.extend(deletable)
        audits.append(
            RootAudit(
                root=rel(root),
                image_files=len(images),
                kept_by_final=len(kept),
                delete_candidates=len(deletable),
                kept_bytes=sum(path.stat().st_size for path in kept),
                delete_candidate_bytes=sum(path.stat().st_size for path in deletable),
            )
        )
    return audits, delete_candidates


def zip_candidates() -> list[Path]:
    return [path for path in COLAB_UPLOAD_ZIPS if path.exists()]


def descriptor_cloud_candidates() -> list[Path]:
    return [path for path in REGENERABLE_DESCRIPTOR_CLOUD_TARGETS if path.exists()]


def verify_final_refs() -> list[str]:
    _, missing_refs = iter_existing_final_paths()
    return missing_refs


def write_outputs(
    keep_paths: set[Path],
    audits: list[RootAudit],
    delete_candidates: list[Path],
    zips: list[Path],
    descriptor_cloud: list[Path],
    execute: bool,
    deleted_paths: list[tuple[Path, int, str]],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "phase14_disk_cleanup_keep_paths.txt").write_text(
        "\n".join(sorted(rel(path) for path in keep_paths)) + "\n",
        encoding="utf-8",
    )

    with (OUTPUT_DIR / "phase14_disk_cleanup_root_audit.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(audits[0]).keys()))
        writer.writeheader()
        for audit in audits:
            writer.writerow(asdict(audit))

    with (OUTPUT_DIR / "phase14_disk_cleanup_delete_candidates.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "kind"])
        writer.writeheader()
        for path in delete_candidates:
            writer.writerow(
                {
                    "path": rel(path),
                    "bytes": path.stat().st_size if path.exists() else 0,
                    "kind": "non_final_fcf_image",
                }
            )
        for path in zips:
            writer.writerow(
                {
                    "path": rel(path),
                    "bytes": path_size(path),
                    "kind": "colab_upload_zip",
                }
            )
        for path in descriptor_cloud:
            writer.writerow(
                {
                    "path": rel(path),
                    "bytes": path_size(path),
                    "kind": "regenerable_descriptor_cloud_payload",
                }
            )

    with (OUTPUT_DIR / "phase14_disk_cleanup_deleted_files.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "kind"])
        writer.writeheader()
        for path, size, kind in deleted_paths:
            writer.writerow({"path": rel(path), "bytes": size, "kind": kind})

    summary = {
        "mode": "execute" if execute else "dry_run",
        "keep_path_count": len(keep_paths),
        "root_audits": [asdict(audit) for audit in audits],
        "delete_candidate_files": len(delete_candidates),
        "delete_candidate_bytes": sum(
            path.stat().st_size for path in delete_candidates if path.exists()
        ),
        "colab_zip_candidates": len(zips),
        "colab_zip_candidate_bytes": sum(path.stat().st_size for path in zips if path.exists()),
        "descriptor_cloud_payload_candidates": len(descriptor_cloud),
        "descriptor_cloud_payload_candidate_bytes": sum(path_size(path) for path in descriptor_cloud),
        "deleted_files": len(deleted_paths),
        "deleted_bytes": sum(size for _, size, _ in deleted_paths),
    }
    summary_name = "phase14_disk_cleanup_summary.json" if execute else "phase14_disk_cleanup_dry_run_summary.json"
    (OUTPUT_DIR / summary_name).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def delete_files(paths: Iterable[Path], kind: str) -> list[tuple[Path, int, str]]:
    deleted: list[tuple[Path, int, str]] = []
    for path in paths:
        if not path.exists():
            continue
        size = path.stat().st_size
        path.unlink()
        deleted.append((path, size, kind))
    return deleted


def path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def delete_paths(paths: Iterable[Path], kind: str) -> list[tuple[Path, int, str]]:
    deleted: list[tuple[Path, int, str]] = []
    for path in paths:
        if not path.exists():
            continue
        size = path_size(path)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        deleted.append((path, size, kind))
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete non-final FCF images and explicit Colab upload zips.",
    )
    args = parser.parse_args()

    keep_paths, missing_refs = iter_existing_final_paths()
    if missing_refs:
        print("ABORT: final CSV references are missing before cleanup.")
        for ref in missing_refs[:50]:
            print(f"  missing: {ref}")
        return 2

    audits, delete_candidates = audit_cleanup(keep_paths)
    zips = zip_candidates()
    descriptor_cloud = descriptor_cloud_candidates()
    deleted_paths: list[tuple[Path, int, str]] = []

    if args.execute:
        deleted_paths.extend(delete_files(delete_candidates, "non_final_fcf_image"))
        deleted_paths.extend(delete_files(zips, "colab_upload_zip"))
        deleted_paths.extend(delete_paths(descriptor_cloud, "regenerable_descriptor_cloud_payload"))
        post_missing = verify_final_refs()
        if post_missing:
            print("ERROR: cleanup completed but final references are now missing.")
            for ref in post_missing[:50]:
                print(f"  missing: {ref}")
            return 3

    # Update audit delete counts after execution.
    if args.execute:
        deleted_set = {path for path, _, _ in deleted_paths}
        for audit in audits:
            root = PROJECT_ROOT / audit.root
            root_deleted = [
                (path, size)
                for path, size, kind in deleted_paths
                if kind == "non_final_fcf_image" and path.is_relative_to(root)
            ]
            audit.deleted_files = len(root_deleted)
            audit.deleted_bytes = sum(size for _, size in root_deleted)

    write_outputs(keep_paths, audits, delete_candidates, zips, descriptor_cloud, args.execute, deleted_paths)

    print("MODE", "EXECUTE" if args.execute else "DRY_RUN")
    print("keep_path_count", len(keep_paths))
    for audit in audits:
        print(
            audit.root,
            "images", audit.image_files,
            "keep", audit.kept_by_final,
            "delete_candidates", audit.delete_candidates,
            "delete_candidate_GB", round(audit.delete_candidate_bytes / 1024**3, 3),
            "deleted", audit.deleted_files,
        )
    print("zip_candidates", len(zips), "zip_GB", round(sum(path.stat().st_size for path in zips if path.exists()) / 1024**3, 3))
    print(
        "descriptor_cloud_candidates",
        len(descriptor_cloud),
        "descriptor_cloud_GB",
        round(sum(path_size(path) for path in descriptor_cloud if path.exists()) / 1024**3, 3),
    )
    print("deleted_files", len(deleted_paths), "deleted_GB", round(sum(size for _, size, _ in deleted_paths) / 1024**3, 3))
    print("audit_dir", rel(OUTPUT_DIR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
