#!/usr/bin/env python3
"""Remove reproducible photo payloads from approved PF-ERI v2 ZIP packages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile


PHOTO_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
NOTE_MEMBER = "PHOTOS_REMOVED.md"
EXPECTED_ZIP_COUNT = 53
EXPECTED_PHOTO_COUNT = 26_482
MANIFEST_PATH = Path("artifacts/manifests/pferi_v2_zip_photo_removal.csv")
MANIFEST_FIELDS = [
    "zip_path",
    "provenance_group",
    "provenance_reference",
    "original_size_bytes",
    "original_sha256",
    "removed_photo_count",
    "removed_photo_uncompressed_bytes",
    "removed_photo_compressed_bytes",
    "retained_member_count",
    "new_size_bytes",
    "new_sha256",
    "reclaimed_bytes",
    "note_member",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_photo_member(name: str) -> bool:
    return Path(name).suffix.lower() in PHOTO_EXTENSIONS


def approved_targets(repo: Path) -> list[Path]:
    patterns = [
        "artifacts/transfers/pferi_v2/PF_ERI_V2_INTERFACE_AUDIT_DELIVERY_original.zip",
        "artifacts/transfers/pferi_v2/PF_ERI_V2_INTERFACE_AUDIT_DELIVERY_returned_a001.zip",
        "artifacts/transfers/pferi_v2/review/adjudication_packages/candidate_adjudication_packages/*.zip",
        "artifacts/transfers/pferi_v2/review/formal_reviewer_packages/candidate_reviewer_packages/*.zip",
        "artifacts/transfers/pferi_v2/review/formal_reviewer_subpackages/reviewer_*/*.zip",
        "artifacts/transfers/pferi_v2/review/task15i_reviewer_packages/candidate_reviewer_packages/*.zip",
        "archive/pferi_v2/task_runs/model_development/2026-07-25_task15i_descriptor_execution_manifest_v1/TASK15I_INDEPENDENT_DESCRIPTOR_IMAGES.zip",
        "archive/pferi_v2/task_runs/model_development/2026-07-27_task15l_calibration_collection_freeze_v1/reviewer_packages/candidate_reviewer_packages/*.zip",
        "work/pferi_v2/gpu/packages/task15k_calibration/PF_ERI_TASK15K_CALIBRATION_MODELSCOPE_CONTROL_PACKAGE.zip",
        "work/pferi_v2/gpu/packages/task15m_confirmation/PF_ERI_TASK15M_CONFIRMATION_MODELSCOPE_CONTROL_PACKAGE.zip",
    ]
    targets = sorted({path for pattern in patterns for path in repo.glob(pattern)})
    if len(targets) != EXPECTED_ZIP_COUNT:
        raise RuntimeError(
            f"approval boundary mismatch: expected {EXPECTED_ZIP_COUNT} ZIPs, found {len(targets)}"
        )
    return targets


def provenance_for(relative_path: str) -> tuple[str, str]:
    if "formal_reviewer_subpackages" in relative_path:
        return (
            "formal_reviewer_subpackages",
            "artifacts/transfers/pferi_v2/review/formal_reviewer_subpackages/SUBPACKAGE_MANIFEST.csv; "
            "artifacts/transfers/pferi_v2/review/formal_reviewer_subpackages/subpackage_audit.json",
        )
    if "formal_reviewer_packages" in relative_path:
        return (
            "formal_reviewer_packages",
            "scripts/build_v2_formal_reviewer_packages.py; "
            "artifacts/transfers/pferi_v2/review/formal_reviewer_packages/restricted/restricted_asset_map.csv; "
            "data/frozen/pferi_v2/",
        )
    if "task15i_reviewer_packages" in relative_path:
        return (
            "task15i_reviewer_packages",
            "artifacts/transfers/pferi_v2/review/task15i_reviewer_packages/restricted/restricted_asset_map.csv; "
            "data/candidate-reservoirs/task15i_independent_lynx_v1/images/",
        )
    if "adjudication_packages" in relative_path:
        return (
            "adjudication_packages",
            "scripts/build_v2_adjudication_packages.py; "
            "artifacts/transfers/pferi_v2/review/adjudication_packages/",
        )
    if "task15l_calibration_collection_freeze_v1/reviewer_packages" in relative_path:
        return (
            "task15l_calibration_reviewer_packages",
            "archive/pferi_v2/task_runs/model_development/2026-07-27_task15l_calibration_collection_freeze_v1/"
            "restricted/selected_image_execution_manifest.csv; reviewer_packages/restricted/restricted_asset_map.csv",
        )
    if relative_path.endswith("TASK15I_INDEPENDENT_DESCRIPTOR_IMAGES.zip"):
        return (
            "task15i_descriptor_images",
            "archive/pferi_v2/task_runs/model_development/2026-07-25_task15i_descriptor_execution_manifest_v1/"
            "descriptor_execution_manifest.csv",
        )
    if "task15k_calibration" in relative_path:
        return (
            "task15k_modelscope_package",
            "scripts/build_task15k_calibration_modelscope_package.py; inputs/selected_image_manifest.csv",
        )
    if "task15m_confirmation" in relative_path:
        return (
            "task15m_modelscope_package",
            "scripts/build_task15m_confirmation_modelscope_package.py; inputs/selected_image_manifest.csv; "
            "data/frozen/pferi_v2/lynx-wild/images/",
        )
    if "INTERFACE_AUDIT_DELIVERY" in relative_path:
        return (
            "interface_audit_delivery",
            "scripts/build_task15i_independent_browser_audit_delivery.py; "
            "work/pferi_v2/review/interface_dry_run/independent_browser_audit/",
        )
    raise RuntimeError(f"no provenance rule for {relative_path}")


def load_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["zip_path"]: row for row in csv.DictReader(handle)}


def write_manifest(path: Path, records: dict[str, dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=MANIFEST_FIELDS,
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(records[key] for key in sorted(records))
        os.replace(temporary_name, path)
    except Exception:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
        raise


def photo_inventory(path: Path) -> list[zipfile.ZipInfo]:
    with zipfile.ZipFile(path) as archive:
        return [info for info in archive.infolist() if is_photo_member(info.filename)]


def removal_note(
    relative_path: str,
    group: str,
    provenance: str,
    original_hash: str,
    original_size: int,
    photos: list[zipfile.ZipInfo],
) -> bytes:
    compressed = sum(info.compress_size for info in photos)
    uncompressed = sum(info.file_size for info in photos)
    text = f"""# Photos Removed

Removal date: 2026-07-28

This package was converted to a metadata-only preservation copy to avoid retaining a reproducible photo payload inside a delivery ZIP.

- ZIP path: `{relative_path}`
- Provenance group: `{group}`
- Source/provenance: `{provenance}`
- Original ZIP size: `{original_size}` bytes
- Original ZIP SHA256: `{original_hash}`
- Removed image members: `{len(photos)}`
- Removed image bytes (uncompressed): `{uncompressed}`
- Removed image bytes (compressed in original ZIP): `{compressed}`
- Rebuild tool: `scripts/strip_pferi_v2_zip_photos.py`

CSV, JSON, README, audit, contract, mapping, and result members were retained. Historical manifests inside this ZIP may still list the removed image members; use the provenance source above to reconstruct them when required.
"""
    return text.encode("utf-8")


def rebuild_zip(repo: Path, path: Path) -> dict[str, object]:
    relative_path = path.relative_to(repo).as_posix()
    group, provenance = provenance_for(relative_path)
    original_size = path.stat().st_size
    original_hash = sha256_file(path)

    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        with zipfile.ZipFile(path, "r") as source:
            photos = [info for info in source.infolist() if is_photo_member(info.filename)]
            retained = [
                info
                for info in source.infolist()
                if not is_photo_member(info.filename) and info.filename != NOTE_MEMBER
            ]
            if not photos:
                raise RuntimeError(f"no photos found in approved target {relative_path}")
            note = removal_note(
                relative_path,
                group,
                provenance,
                original_hash,
                original_size,
                photos,
            )
            with zipfile.ZipFile(temporary_path, "w", allowZip64=True) as destination:
                for info in retained:
                    if info.is_dir():
                        destination.writestr(info, b"")
                        continue
                    with source.open(info, "r") as reader, destination.open(
                        info, "w", force_zip64=True
                    ) as writer:
                        shutil.copyfileobj(reader, writer, length=8 * 1024 * 1024)
                destination.writestr(NOTE_MEMBER, note, compress_type=zipfile.ZIP_DEFLATED)

        with zipfile.ZipFile(temporary_path, "r") as rebuilt:
            bad_member = rebuilt.testzip()
            if bad_member is not None:
                raise RuntimeError(f"CRC verification failed for {relative_path}: {bad_member}")
            if any(is_photo_member(info.filename) for info in rebuilt.infolist()):
                raise RuntimeError(f"photo member remains in {relative_path}")
            if NOTE_MEMBER not in rebuilt.namelist():
                raise RuntimeError(f"removal note missing from {relative_path}")

        new_size = temporary_path.stat().st_size
        new_hash = sha256_file(temporary_path)
        os.replace(temporary_path, path)
        return {
            "zip_path": relative_path,
            "provenance_group": group,
            "provenance_reference": provenance,
            "original_size_bytes": original_size,
            "original_sha256": original_hash,
            "removed_photo_count": len(photos),
            "removed_photo_uncompressed_bytes": sum(info.file_size for info in photos),
            "removed_photo_compressed_bytes": sum(info.compress_size for info in photos),
            "retained_member_count": len(retained) + 1,
            "new_size_bytes": new_size,
            "new_sha256": new_hash,
            "reclaimed_bytes": original_size - new_size,
            "note_member": NOTE_MEMBER,
        }
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


CHECKSUM_LINE = re.compile(r"^([0-9a-fA-F]{64})([ \t]+)(\*?)(.+?)(\r?\n)?$")


def referenced_path(checksum_file: Path, listed_name: str) -> Path:
    if checksum_file.name.endswith(".zip.sha256"):
        return checksum_file.with_suffix("").resolve()
    return (checksum_file.parent / listed_name).resolve()


def update_impacted_checksums(repo: Path, changed_paths: set[Path]) -> list[Path]:
    roots = [repo / "artifacts/transfers/pferi_v2", repo / "archive/pferi_v2", repo / "work/pferi_v2"]
    checksum_files = sorted(path for root in roots for path in root.rglob("*.sha256"))
    changed = {path.resolve() for path in changed_paths}
    updated_files: set[Path] = set()

    while True:
        updated_this_pass = False
        for checksum_file in checksum_files:
            lines = checksum_file.read_text(encoding="utf-8").splitlines(keepends=True)
            output: list[str] = []
            file_changed = False
            for line in lines:
                match = CHECKSUM_LINE.match(line)
                if not match:
                    output.append(line)
                    continue
                old_hash, spacing, marker, listed_name, newline = match.groups()
                target = referenced_path(checksum_file, listed_name)
                if target in changed and target.exists():
                    new_hash = sha256_file(target)
                    replacement = f"{new_hash}{spacing}{marker}{listed_name}{newline or ''}"
                    output.append(replacement)
                    file_changed = file_changed or replacement != line
                else:
                    output.append(line)
            if file_changed:
                checksum_file.write_text("".join(output), encoding="utf-8")
                changed.add(checksum_file.resolve())
                updated_files.add(checksum_file)
                updated_this_pass = True
        if not updated_this_pass:
            return sorted(updated_files)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="perform the approved atomic rebuild")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[1]
    manifest_path = repo / MANIFEST_PATH
    targets = approved_targets(repo)
    existing = load_manifest(manifest_path)
    inventories = {path: photo_inventory(path) for path in targets}
    accounted_photos = sum(len(photos) for photos in inventories.values()) + sum(
        int(row["removed_photo_count"])
        for relative_path, row in existing.items()
        if not inventories.get(repo / relative_path)
    )
    if accounted_photos != EXPECTED_PHOTO_COUNT:
        raise RuntimeError(
            f"photo boundary mismatch: expected {EXPECTED_PHOTO_COUNT}, accounted for {accounted_photos}"
        )

    pending = [path for path, photos in inventories.items() if photos]
    print(f"approved_zips={len(targets)} pending_zips={len(pending)} accounted_photos={accounted_photos}")
    if not args.apply:
        print("dry run only; pass --apply after explicit approval")
        return 0

    records: dict[str, dict[str, object]] = {key: dict(value) for key, value in existing.items()}
    changed_paths: set[Path] = set()
    for index, path in enumerate(pending, start=1):
        relative_path = path.relative_to(repo).as_posix()
        record = rebuild_zip(repo, path)
        records[relative_path] = record
        changed_paths.add(path)
        write_manifest(manifest_path, records)
        print(
            f"[{index}/{len(pending)}] {relative_path}: "
            f"removed={record['removed_photo_count']} reclaimed={record['reclaimed_bytes']}"
        )

    updated_checksums = update_impacted_checksums(repo, changed_paths)
    print(f"updated_checksum_files={len(updated_checksums)}")
    print(f"manifest={MANIFEST_PATH.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
