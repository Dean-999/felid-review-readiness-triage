#!/usr/bin/env python3
"""Create an immutable image-only ZIP for PF-ERI v2 external descriptor inference."""
from __future__ import annotations

import argparse, csv, hashlib, json, shutil, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "work/pferi_v2/pipeline/descriptor_manifests/restricted_descriptor_execution_manifest.csv"
DEFAULT_PACKAGE = ROOT / "work/pferi_v2/descriptor_execution_package"
DEFAULT_ZIP = ROOT / "archive/pferi_v2/task_runs/v2_czechlynx_fresh_descriptor_images.zip"
DEFAULT_AUDIT = ROOT / "work/pferi_v2/pipeline/descriptor_manifests/v2_descriptor_package_audit.json"

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def package(manifest: Path, package_dir: Path, zip_path: Path, audit_path: Path) -> dict[str, Any]:
    manifest = manifest.resolve()
    package_dir = package_dir.resolve()
    zip_path = zip_path.resolve()
    audit_path = audit_path.resolve()
    with manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"image_id", "image_path_relative", "content_sha256"}
    if not rows or set(rows[0]) != required:
        raise ValueError("manifest must contain exactly image_id, image_path_relative, content_sha256")
    if package_dir.exists() or zip_path.exists():
        raise FileExistsError("refusing to overwrite an existing package or ZIP")
    package_dir.parent.mkdir(parents=True, exist_ok=True)
    failed = 0
    with tempfile.TemporaryDirectory(dir=package_dir.parent, prefix=".v2_descriptor_package_") as temp:
        temp_root = Path(temp)
        images = temp_root / "v2_descriptor_execution_package" / "images"
        images.mkdir(parents=True)
        seen_names: set[str] = set()
        for row in rows:
            source = ROOT / row["image_path_relative"]
            if not source.is_file() or sha256(source) != row["content_sha256"]:
                failed += 1
                raise ValueError(f"source integrity failure for {row['image_id']}")
            destination = images / source.name
            if destination.name in seen_names:
                raise ValueError(f"duplicate filename requires an unsafe rename: {destination.name}")
            seen_names.add(destination.name)
            shutil.copyfile(source, destination)
            if sha256(destination) != row["content_sha256"]:
                failed += 1
                raise ValueError(f"copied integrity failure for {row['image_id']}")
        if len(list(images.iterdir())) != len(rows):
            raise ValueError("copied image count does not equal manifest count")
        temp_zip = temp_root / zip_path.name
        with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_STORED) as archive:
            for image in sorted(images.iterdir()):
                archive.write(image, arcname=f"v2_descriptor_execution_package/images/{image.name}")
        # Verify ZIP members' bytes after extraction into memory.
        with zipfile.ZipFile(temp_zip) as archive:
            if len(archive.infolist()) != len(rows):
                raise ValueError("ZIP image count does not equal manifest count")
            expected = {Path(row["image_path_relative"]).name: row["content_sha256"] for row in rows}
            for info in archive.infolist():
                if sha256_bytes(archive.read(info)) != expected.get(Path(info.filename).name):
                    failed += 1
                    raise ValueError(f"ZIP integrity failure for {info.filename}")
        shutil.move(str(temp_root / "v2_descriptor_execution_package"), package_dir)
        shutil.move(str(temp_zip), zip_path)
    audit = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "source_manifest_path": str(manifest.relative_to(ROOT)), "manifest_sha256": sha256(manifest), "image_count": len(rows), "copied_image_count": len(rows), "failed_verification_count": failed, "zip_sha256": sha256(zip_path), "status": "PASS"}
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()
    try:
        audit = package(args.manifest, args.package_dir, args.zip, args.audit)
    except Exception as error:
        audit = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "source_manifest_path": str(args.manifest), "failed_verification_count": 1, "status": "FAIL", "error": str(error)}
        args.audit.parent.mkdir(parents=True, exist_ok=True)
        args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(audit, indent=2, sort_keys=True)); return 1
    print(json.dumps(audit, indent=2, sort_keys=True)); return 0

if __name__ == "__main__":
    raise SystemExit(main())
