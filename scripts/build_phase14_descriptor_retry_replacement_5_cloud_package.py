#!/usr/bin/env python3
"""Build a cloud retry package for the five Phase 14 replacement images.

This package is intentionally small. It uses the rebuilt 12000-image descriptor
manifest and the 11995-row returned embedding table to identify the exact images
whose embeddings are still missing after invalid-source replacement.
"""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_descriptor_embedding_package/phase14_2x2_descriptor_embedding_manifest.csv"
)
RETURNED_EMBEDDINGS = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_descriptor_embedding_package/return/phase14_2x2_megadescriptor_embeddings.csv"
)
OUT_DIR = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_descriptor_embedding_package/retry_replacement_5_cloud_package"
)
EXTRACTION_SCRIPT_SOURCE = PROJECT_ROOT / "scripts/extract_phase14_megadescriptor_embeddings.py"

EXPECTED_MISSING = 5
SAFE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

MANIFEST_COLUMNS = [
    "phase14_image_evidence_index",
    "phase14_image_evidence_id",
    "source_quadrant",
    "environment_axis",
    "species_axis",
    "evidence_axis",
    "image_key",
    "image_exists",
    "identity_label_available_for_validation",
    "image_evidence_utility_score",
    "descriptor_extraction_status",
    "cloud_image_relpath",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve_path(value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else PROJECT_ROOT / path


def safe_extension(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in SAFE_EXTENSIONS:
        return suffix
    with Image.open(path) as image:
        image.verify()
    return ".jpg"


def verify_image(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return {
            "format": str(image.format),
            "width": int(image.width),
            "height": int(image.height),
        }


def clean_out_dir(out_dir: Path) -> Path:
    image_dir = out_dir / "images/phase14_descriptor_images"
    if image_dir.exists():
        shutil.rmtree(image_dir)
    image_dir.mkdir(parents=True, exist_ok=True)
    for path in out_dir.glob("phase14_descriptor_images_replacement_5.zip"):
        path.unlink()
    (out_dir / "scripts").mkdir(parents=True, exist_ok=True)
    return image_dir


def load_missing_rows(source_manifest: Path, returned_embeddings: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest = pd.read_csv(source_manifest, low_memory=False)
    returned = pd.read_csv(returned_embeddings, usecols=["phase14_image_evidence_id"])
    manifest_ids = set(manifest["phase14_image_evidence_id"].astype(str))
    returned_ids = set(returned["phase14_image_evidence_id"].astype(str))
    missing_ids = sorted(manifest_ids - returned_ids)
    extra_ids = sorted(returned_ids - manifest_ids)
    missing = manifest[manifest["phase14_image_evidence_id"].astype(str).isin(missing_ids)].copy()
    return missing, {
        "source_manifest_rows": int(len(manifest)),
        "returned_embedding_rows": int(len(returned)),
        "missing_embedding_ids": missing_ids,
        "extra_returned_embedding_ids": extra_ids,
    }


def build_package(missing: pd.DataFrame, out_dir: Path) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    image_dir = clean_out_dir(out_dir)
    rows = []
    image_checks = []
    for _, row in missing.iterrows():
        image_id = str(row["phase14_image_evidence_id"])
        source = resolve_path(row["image_path_relative"] if "image_path_relative" in row else row["image_path"])
        if not source.exists():
            raise FileNotFoundError(f"Missing replacement image source: {source}")
        check = verify_image(source)
        extension = safe_extension(source)
        output_name = f"{image_id}{extension}"
        target = image_dir / output_name
        shutil.copy2(source, target)
        target_check = verify_image(target)
        record = row.to_dict()
        record["cloud_image_relpath"] = f"images/phase14_descriptor_images/{output_name}"
        record["descriptor_extraction_status"] = "retry_replacement_pending"
        rows.append(record)
        image_checks.append(
            {
                "phase14_image_evidence_id": image_id,
                "source_image": rel(source),
                "cloud_image_relpath": record["cloud_image_relpath"],
                "source_format": check["format"],
                "target_format": target_check["format"],
                "width": target_check["width"],
                "height": target_check["height"],
            }
        )

    cloud = pd.DataFrame(rows)
    missing_columns = [column for column in MANIFEST_COLUMNS if column not in cloud.columns]
    if missing_columns:
        raise ValueError(f"Retry cloud manifest missing columns: {missing_columns}")
    cloud = cloud[MANIFEST_COLUMNS].copy()
    manifest_path = out_dir / "phase14_2x2_descriptor_embedding_manifest_replacement_5_cloud.csv"
    cloud.to_csv(manifest_path, index=False)

    zip_path = out_dir / "phase14_descriptor_images_replacement_5.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relpath in cloud["cloud_image_relpath"].astype(str):
            archive.write(out_dir / relpath, arcname=relpath)
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad_member = archive.testzip()
        member_count = len(archive.namelist())

    shutil.copy2(EXTRACTION_SCRIPT_SOURCE, out_dir / "scripts/extract_phase14_megadescriptor_embeddings.py")
    details = {
        "cloud_manifest": rel(manifest_path),
        "zip_file": rel(zip_path),
        "zip_member_count": int(member_count),
        "zip_bad_member": bad_member,
    }
    return cloud, image_checks, details


def write_readme(out_dir: Path) -> None:
    text = """# Phase 14 Replacement-5 Descriptor Retry Package

This package contains only the five valid replacement images needed to complete
the Phase 14 12000-image MegaDescriptor table.

Upload this directory to Colab/Kaggle, unzip `phase14_descriptor_images_replacement_5.zip`,
and run:

```bash
python scripts/extract_phase14_megadescriptor_embeddings.py \\
  --manifest phase14_2x2_descriptor_embedding_manifest_replacement_5_cloud.csv \\
  --output phase14_2x2_megadescriptor_embeddings_replacement_5.csv \\
  --project-root . \\
  --batch-size 8
```

Return only `phase14_2x2_megadescriptor_embeddings_replacement_5.csv`.
Do not reuse the older `retry_failed_5_cloud_package`; those source files were
confirmed invalid after redownload.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, default=SOURCE_MANIFEST)
    parser.add_argument("--returned-embeddings", type=Path, default=RETURNED_EMBEDDINGS)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--expected-missing", type=int, default=EXPECTED_MISSING)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.source_manifest.exists():
        raise FileNotFoundError(f"Missing source manifest: {args.source_manifest}")
    if not args.returned_embeddings.exists():
        raise FileNotFoundError(f"Missing returned embeddings: {args.returned_embeddings}")
    if not EXTRACTION_SCRIPT_SOURCE.exists():
        raise FileNotFoundError(f"Missing extraction script: {EXTRACTION_SCRIPT_SOURCE}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    missing, alignment = load_missing_rows(args.source_manifest, args.returned_embeddings)
    if len(missing) != args.expected_missing:
        raise ValueError(f"Missing replacement rows={len(missing)}, expected {args.expected_missing}")
    if alignment["extra_returned_embedding_ids"]:
        raise ValueError("Returned embeddings contain IDs not present in the rebuilt manifest")

    cloud, image_checks, package_details = build_package(missing, args.out_dir)
    write_readme(args.out_dir)
    audit = {
        "source_manifest": rel(args.source_manifest),
        "returned_embeddings": rel(args.returned_embeddings),
        "output_dir": rel(args.out_dir),
        "alignment": alignment,
        "cloud_manifest_rows": int(len(cloud)),
        "source_quadrant_counts": {
            str(k): int(v) for k, v in cloud["source_quadrant"].value_counts().sort_index().items()
        },
        "species_axis_counts": {
            str(k): int(v) for k, v in cloud["species_axis"].value_counts().sort_index().items()
        },
        "evidence_axis_counts": {
            str(k): int(v) for k, v in cloud["evidence_axis"].value_counts().sort_index().items()
        },
        "image_checks": image_checks,
        "package": package_details,
        "status": "complete",
    }
    audit_path = args.out_dir / "phase14_retry_replacement_5_cloud_package_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))

    if audit["cloud_manifest_rows"] != args.expected_missing:
        raise SystemExit("Unexpected retry manifest row count")
    if audit["package"]["zip_member_count"] != args.expected_missing:
        raise SystemExit("Unexpected retry zip member count")
    if audit["package"]["zip_bad_member"] is not None:
        raise SystemExit("Retry zip integrity check failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
