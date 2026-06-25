#!/usr/bin/env python3
"""Build the Phase 14 descriptor embedding cloud package.

The package contains renamed image copies, a path-safe cloud manifest, zip
chunks, the extraction script, README, and an audit JSON. It does not extract
embeddings or run descriptor-evidence conflict analysis.
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
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_cloud_package"
IMAGE_DIR = OUT_DIR / "images/phase14_descriptor_images"
CLOUD_MANIFEST = OUT_DIR / "phase14_2x2_descriptor_embedding_manifest_cloud.csv"
AUDIT_JSON = OUT_DIR / "phase14_descriptor_embedding_cloud_package_audit.json"
README = OUT_DIR / "README.md"
EXTRACTION_SCRIPT_SOURCE = PROJECT_ROOT / "scripts/extract_phase14_megadescriptor_embeddings.py"
EXTRACTION_SCRIPT_TARGET = OUT_DIR / "scripts/extract_phase14_megadescriptor_embeddings.py"

EXPECTED_ROWS = 12_000
EXPECTED_ZIP_COUNT = 12
IMAGES_PER_ZIP = 1_000
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


def resolve_source_path(value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else PROJECT_ROOT / path


def safe_extension(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in SAFE_EXTENSIONS:
        return suffix
    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as exc:
        raise ValueError(f"Cannot use unusual extension for unreadable image {path}: {exc}") from exc
    return ".jpg"


def validate_source_manifest(frame: pd.DataFrame) -> None:
    required = {
        "phase14_image_evidence_id",
        "source_quadrant",
        "image_path",
        "image_exists",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Source manifest missing columns: {sorted(missing)}")
    if len(frame) != EXPECTED_ROWS:
        raise ValueError(f"Manifest rows={len(frame)}, expected {EXPECTED_ROWS}")
    unique_ids = frame["phase14_image_evidence_id"].astype(str).nunique()
    if unique_ids != EXPECTED_ROWS:
        raise ValueError(f"Unique phase14_image_evidence_id={unique_ids}, expected {EXPECTED_ROWS}")
    not_exists = frame[frame["image_exists"].astype(str).str.lower().ne("yes")]
    if len(not_exists):
        examples = not_exists["phase14_image_evidence_id"].astype(str).head(20).tolist()
        raise FileNotFoundError(f"Manifest has image_exists != yes for {len(not_exists)} rows: {examples}")


def clean_output_dirs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if IMAGE_DIR.exists():
        shutil.rmtree(IMAGE_DIR)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    for zip_path in out_dir.glob("phase14_descriptor_images_part_*.zip"):
        zip_path.unlink()
    scripts_dir = out_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)


def copy_images(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    output_names: list[str] = []
    missing_source: list[str] = []
    for _, row in frame.iterrows():
        image_id = str(row["phase14_image_evidence_id"])
        source_path = resolve_source_path(row["image_path"])
        if not source_path.exists():
            missing_source.append(image_id)
            continue
        extension = safe_extension(source_path)
        output_name = f"{image_id}{extension}"
        target_path = IMAGE_DIR / output_name
        shutil.copy2(source_path, target_path)
        output_names.append(output_name)
        record = row.to_dict()
        record["cloud_image_relpath"] = f"images/phase14_descriptor_images/{output_name}"
        rows.append(record)
    duplicate_names = sorted({name for name in output_names if output_names.count(name) > 1})
    if missing_source:
        raise FileNotFoundError(f"Missing source images: {missing_source[:20]}")
    if duplicate_names:
        raise ValueError(f"Duplicate output filenames: {duplicate_names[:20]}")
    cloud = pd.DataFrame(rows)
    copied_paths = [OUT_DIR / relpath for relpath in cloud["cloud_image_relpath"]]
    missing_copied = [str(cloud.iloc[index]["phase14_image_evidence_id"]) for index, path in enumerate(copied_paths) if not path.exists()]
    if missing_copied:
        raise FileNotFoundError(f"Missing copied images: {missing_copied[:20]}")
    details = {
        "copied_images": int(len(cloud)),
        "missing_source_images": [],
        "duplicate_output_filenames": [],
        "missing_copied_images": [],
    }
    return cloud, details


def write_cloud_manifest(cloud: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in MANIFEST_COLUMNS if column not in cloud.columns]
    if missing:
        raise ValueError(f"Cloud manifest missing required source columns: {missing}")
    safe = cloud[MANIFEST_COLUMNS].copy()
    leaked = [column for column in safe.columns if column in {"image_path", "image_path_relative"}]
    if leaked:
        raise ValueError(f"Cloud manifest contains forbidden path columns: {leaked}")
    safe.to_csv(CLOUD_MANIFEST, index=False)
    return safe


def zip_chunks(cloud_manifest: pd.DataFrame) -> tuple[list[dict[str, Any]], list[str]]:
    zip_counts = []
    errors = []
    relpaths = cloud_manifest["cloud_image_relpath"].astype(str).tolist()
    if len(relpaths) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} cloud relpaths, got {len(relpaths)}")
    for index in range(EXPECTED_ZIP_COUNT):
        part = relpaths[index * IMAGES_PER_ZIP : (index + 1) * IMAGES_PER_ZIP]
        zip_path = OUT_DIR / f"phase14_descriptor_images_part_{index + 1:02d}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for relpath in part:
                source = OUT_DIR / relpath
                archive.write(source, arcname=relpath)
        with zipfile.ZipFile(zip_path, "r") as archive:
            bad = archive.testzip()
            names = archive.namelist()
        if bad is not None:
            errors.append(f"{zip_path.name}: first bad member {bad}")
        if len(names) != len(part):
            errors.append(f"{zip_path.name}: member_count={len(names)} expected={len(part)}")
        zip_counts.append({"zip": zip_path.name, "image_count": int(len(part)), "size_bytes": int(zip_path.stat().st_size)})
    return zip_counts, errors


def write_readme() -> None:
    text = """# Phase 14 Descriptor Embedding Cloud Package

This package is for Phase 14 descriptor embedding extraction. It contains 12000 renamed image copies, a cloud-safe manifest, 12 image zip chunks, and the extraction script.

Upload this directory to Kaggle or Colab as `phase14-descriptor-embedding-cloud-package`.

## Contents

- `phase14_2x2_descriptor_embedding_manifest_cloud.csv`
- `phase14_descriptor_images_part_01.zip` through `phase14_descriptor_images_part_12.zip`
- `scripts/extract_phase14_megadescriptor_embeddings.py`
- `README.md`
- `phase14_descriptor_embedding_cloud_package_audit.json`

## Use

Unzip all zip chunks before running extraction. The internal image layout is:

```text
images/phase14_descriptor_images/<phase14_image_evidence_id>.<extension>
```

Use `cloud_image_relpath` from the cloud manifest as the image path column.

Example command from the package root:

```bash
python scripts/extract_phase14_megadescriptor_embeddings.py \
  --manifest phase14_2x2_descriptor_embedding_manifest_cloud.csv \
  --output outputs/phase14/phase14_descriptor_embeddings/phase14_2x2_megadescriptor_embeddings.csv \
  --project-root . \
  --batch-size 32
```

## Expected Return File

```text
outputs/phase14/phase14_descriptor_embeddings/phase14_2x2_megadescriptor_embeddings.csv
```

Required return columns:

```text
phase14_image_evidence_id, embedding_model, embedding_dim, embedding_vector
```

Use a fixed pretrained descriptor, preferably a MegaDescriptor/WildlifeTools-style descriptor. Do not fine-tune in this step.

This package does not infer identity and does not validate bobcat false matches without verified bobcat individual labels.
"""
    README.write_text(text, encoding="utf-8")


def write_audit(
    source_frame: pd.DataFrame,
    cloud_manifest: pd.DataFrame,
    copy_details: dict[str, Any],
    zip_counts: list[dict[str, Any]],
    zip_errors: list[str],
    status: str,
) -> dict[str, Any]:
    payload = {
        "source_manifest": rel(SOURCE_MANIFEST),
        "output_dir": rel(OUT_DIR),
        "original_manifest_rows": int(len(source_frame)),
        "unique_phase14_image_evidence_id": int(source_frame["phase14_image_evidence_id"].astype(str).nunique()),
        "cloud_manifest_rows": int(len(cloud_manifest)),
        "copied_images": copy_details["copied_images"],
        "missing_source_images": copy_details["missing_source_images"],
        "duplicate_output_filenames": copy_details["duplicate_output_filenames"],
        "missing_copied_images": copy_details["missing_copied_images"],
        "zip_count": int(len(zip_counts)),
        "zip_counts": zip_counts,
        "zip_integrity_errors": zip_errors,
        "source_quadrant_counts": {
            str(k): int(v) for k, v in cloud_manifest["source_quadrant"].value_counts().sort_index().items()
        },
        "species_axis_counts": {
            str(k): int(v) for k, v in cloud_manifest["species_axis"].value_counts().sort_index().items()
        },
        "evidence_axis_counts": {
            str(k): int(v) for k, v in cloud_manifest["evidence_axis"].value_counts().sort_index().items()
        },
        "environment_axis_counts": {
            str(k): int(v) for k, v in cloud_manifest["environment_axis"].value_counts().sort_index().items()
        },
        "extraction_script_copied": EXTRACTION_SCRIPT_TARGET.exists(),
        "status": status,
    }
    AUDIT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def validate_final(audit: dict[str, Any]) -> None:
    if audit["original_manifest_rows"] != EXPECTED_ROWS:
        raise ValueError("original_manifest_rows failed")
    if audit["unique_phase14_image_evidence_id"] != EXPECTED_ROWS:
        raise ValueError("unique_phase14_image_evidence_id failed")
    if audit["cloud_manifest_rows"] != EXPECTED_ROWS:
        raise ValueError("cloud_manifest_rows failed")
    if audit["copied_images"] != EXPECTED_ROWS:
        raise ValueError("copied_images failed")
    if audit["missing_source_images"]:
        raise FileNotFoundError("missing_source_images failed")
    if audit["duplicate_output_filenames"]:
        raise ValueError("duplicate_output_filenames failed")
    if audit["missing_copied_images"]:
        raise FileNotFoundError("missing_copied_images failed")
    if audit["zip_count"] != EXPECTED_ZIP_COUNT:
        raise ValueError("zip_count failed")
    if any(item["image_count"] != IMAGES_PER_ZIP for item in audit["zip_counts"]):
        raise ValueError("zip_counts failed")
    if audit["zip_integrity_errors"]:
        raise ValueError("zip_integrity_errors failed")
    if not audit["extraction_script_copied"]:
        raise FileNotFoundError("extraction_script_copied failed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, default=SOURCE_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global SOURCE_MANIFEST, OUT_DIR, IMAGE_DIR, CLOUD_MANIFEST, AUDIT_JSON, README, EXTRACTION_SCRIPT_TARGET
    SOURCE_MANIFEST = args.source_manifest
    OUT_DIR = args.out_dir
    IMAGE_DIR = OUT_DIR / "images/phase14_descriptor_images"
    CLOUD_MANIFEST = OUT_DIR / "phase14_2x2_descriptor_embedding_manifest_cloud.csv"
    AUDIT_JSON = OUT_DIR / "phase14_descriptor_embedding_cloud_package_audit.json"
    README = OUT_DIR / "README.md"
    EXTRACTION_SCRIPT_TARGET = OUT_DIR / "scripts/extract_phase14_megadescriptor_embeddings.py"

    if not SOURCE_MANIFEST.exists():
        raise FileNotFoundError(f"Missing source manifest: {SOURCE_MANIFEST}")
    if not EXTRACTION_SCRIPT_SOURCE.exists():
        raise FileNotFoundError(f"Missing extraction script: {EXTRACTION_SCRIPT_SOURCE}")
    source_frame = pd.read_csv(SOURCE_MANIFEST, low_memory=False)
    validate_source_manifest(source_frame)
    clean_output_dirs(OUT_DIR)
    cloud_raw, copy_details = copy_images(source_frame)
    cloud_manifest = write_cloud_manifest(cloud_raw)
    EXTRACTION_SCRIPT_TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EXTRACTION_SCRIPT_SOURCE, EXTRACTION_SCRIPT_TARGET)
    write_readme()
    zip_counts, zip_errors = zip_chunks(cloud_manifest)
    audit = write_audit(source_frame, cloud_manifest, copy_details, zip_counts, zip_errors, "complete")
    validate_final(audit)

    report = {
        "cloud_package_path": rel(OUT_DIR),
        "manifest_rows": audit["cloud_manifest_rows"],
        "unique_ids": audit["unique_phase14_image_evidence_id"],
        "copied_images": audit["copied_images"],
        "zip_count": audit["zip_count"],
        "zip_counts": audit["zip_counts"],
        "zip_integrity_status": "pass" if not audit["zip_integrity_errors"] else "fail",
        "source_quadrant_counts": audit["source_quadrant_counts"],
        "ready_for_kaggle_upload": True,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
