#!/usr/bin/env python3
"""Create direct-from-source CzechLynx split zips for Phase 16E Colab.

This script reads images directly from local_path_original and writes them into
split zip files. It does not create a staging image directory and does not copy
the CzechLynx image tree.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_candidate_model_filter_colab_package/phase16e_candidate_model_filter_manifest.csv"
)
PHASE16E_README = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_candidate_model_filter_colab_package/README_PHASE16E_COLAB.md"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16e_czechlynx_direct_zips"
ZIP_PREFIX = "phase16e_czechlynx_images_part"
ZIP_MANIFEST = OUTPUT_DIR / "phase16e_czechlynx_direct_zip_manifest.csv"
AUDIT_JSON = OUTPUT_DIR / "phase16e_czechlynx_direct_zip_audit.json"
README = OUTPUT_DIR / "README_PHASE16E_CZECHLYNX_ZIPS.md"

TARGET_QUADRANT = "wild_czechlynx_high_confidence"
EXPECTED_ROWS = 39_760
TARGET_ZIP_BYTES = int(1.5 * 1024**3)
MAX_ZIP_BYTES = int(2.0 * 1024**3)
HASH_CHUNK_BYTES = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_previous_outputs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUTPUT_DIR.glob(f"{ZIP_PREFIX}_*.zip"):
        path.unlink()
    for path in [ZIP_MANIFEST, AUDIT_JSON, README]:
        if path.exists():
            path.unlink()


def assign_zip_parts(df: pd.DataFrame) -> pd.DataFrame:
    part = 1
    current_size = 0
    parts: list[int] = []
    for size in df["file_size_bytes"]:
        if current_size > 0 and current_size + int(size) > TARGET_ZIP_BYTES:
            part += 1
            current_size = 0
        parts.append(part)
        current_size += int(size)
    out = df.copy()
    out["zip_part"] = parts
    out["zip_filename"] = out["zip_part"].map(
        lambda value: f"{ZIP_PREFIX}_{int(value):03d}.zip"
    )
    return out


def build_czechlynx_rows() -> pd.DataFrame:
    df = pd.read_csv(INPUT, low_memory=False)
    cz = df[df["target_quadrant"].eq(TARGET_QUADRANT)].copy()
    if len(cz) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} CzechLynx rows, found {len(cz)}")
    if not cz["candidate_id"].is_unique:
        raise ValueError("Duplicate candidate_id values found in CzechLynx rows")

    cz["local_path_original"] = cz["local_path_original"].fillna("").astype(str)
    cz["source_dataset"] = "CzechLynx"
    cz["local_path_exists"] = cz["local_path_original"].map(lambda value: Path(value).exists())
    missing = cz[~cz["local_path_exists"]]
    if len(missing):
        raise FileNotFoundError(f"Missing CzechLynx files: {len(missing)}")

    cz["file_size_bytes"] = cz["local_path_original"].map(lambda value: Path(value).stat().st_size)
    cz = assign_zip_parts(cz)
    suffixes = cz["local_path_original"].map(lambda value: Path(value).suffix.lower() or ".jpg")
    cz["zip_internal_path"] = [
        f"images/czechlynx/{candidate_id}{suffix}"
        for candidate_id, suffix in zip(cz["candidate_id"], suffixes)
    ]
    return cz


def write_zips(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for part, group in rows.groupby("zip_part", sort=True):
        zip_filename = f"{ZIP_PREFIX}_{int(part):03d}.zip"
        zip_path = OUTPUT_DIR / zip_filename
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
            for _, row in group.iterrows():
                source_path = Path(str(row["local_path_original"]))
                file_hash = sha256_file(source_path)
                zf.write(source_path, arcname=str(row["zip_internal_path"]))
                records.append(
                    {
                        "candidate_id": row["candidate_id"],
                        "target_quadrant": row["target_quadrant"],
                        "source_dataset": row["source_dataset"],
                        "local_path_original": row["local_path_original"],
                        "zip_part": int(part),
                        "zip_filename": zip_filename,
                        "zip_internal_path": row["zip_internal_path"],
                        "file_size_bytes": int(row["file_size_bytes"]),
                        "file_sha256": file_hash,
                    }
                )
        if zip_path.stat().st_size > MAX_ZIP_BYTES:
            raise ValueError(
                f"{zip_filename} is larger than 2GB: {zip_path.stat().st_size}"
            )
    return pd.DataFrame(records)


def verify_zip_integrity(manifest: pd.DataFrame) -> tuple[bool, dict[str, int | str]]:
    details: dict[str, int | str] = {}
    expected_by_zip = manifest.groupby("zip_filename").size().to_dict()
    for zip_filename, expected_count in expected_by_zip.items():
        zip_path = OUTPUT_DIR / str(zip_filename)
        if not zip_path.exists():
            details[str(zip_filename)] = "missing_zip"
            return False, details
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad_member = zf.testzip()
            if bad_member is not None:
                details[str(zip_filename)] = f"bad_member:{bad_member}"
                return False, details
            actual_count = len(zf.infolist())
            details[str(zip_filename)] = actual_count
            if actual_count != int(expected_count):
                return False, details
    return True, details


def append_phase16e_colab_readme() -> None:
    if not PHASE16E_README.exists():
        return
    marker = "## CzechLynx Direct Split Zip Usage"
    text = PHASE16E_README.read_text(encoding="utf-8")
    if marker in text:
        return
    addition = f"""

{marker}

CzechLynx no longer requires a staging copy or one huge zip. Use:

```text
outputs/phase16/phase16e_czechlynx_direct_zips/phase16e_czechlynx_images_part_*.zip
outputs/phase16/phase16e_czechlynx_direct_zips/phase16e_czechlynx_direct_zip_manifest.csv
```

Colab flow:

```bash
mkdir -p /content/phase16e_work/extracted_images
for z in /content/drive/MyDrive/phase16e_czechlynx_direct_zips/phase16e_czechlynx_images_part_*.zip; do
  unzip -q "$z" -d /content/phase16e_work/extracted_images
done
```

Map CzechLynx rows from `source_mode=unavailable_local_path` to
`source_mode=drive_extracted_path` or `packaged_local`, then build paths from
`zip_internal_path`:

```text
/content/phase16e_work/extracted_images/{{zip_internal_path}}
```

This remains streaming/model filtering only. No final 3000 freeze. No simple top-3000.
"""
    PHASE16E_README.write_text(text.rstrip() + addition + "\n", encoding="utf-8")


def write_readme(audit: dict) -> None:
    zip_sizes = audit["each_zip_size_gb"]
    README.write_text(
        f"""# Phase 16E CzechLynx Direct Split Zips

## Goal

Provide CzechLynx high-confidence candidate images to Colab as split zips,
without creating a local staging image directory or copying 39760 images.

## Outputs

```text
phase16e_czechlynx_images_part_*.zip
phase16e_czechlynx_direct_zip_manifest.csv
phase16e_czechlynx_direct_zip_audit.json
```

Rows: {audit["expected_rows"]}

Zip parts: {audit["zip_part_count"]}

Zip sizes GB:

```json
{json.dumps(zip_sizes, indent=2)}
```

## Colab Usage

Upload these files to Google Drive:

```text
phase16e_czechlynx_images_part_*.zip
phase16e_czechlynx_direct_zip_manifest.csv
```

Extract:

```bash
mkdir -p /content/phase16e_work/extracted_images
for z in /content/drive/MyDrive/phase16e_czechlynx_direct_zips/phase16e_czechlynx_images_part_*.zip; do
  unzip -q "$z" -d /content/phase16e_work/extracted_images
done
```

Image path:

```text
/content/phase16e_work/extracted_images/images/czechlynx/{{candidate_id}}.jpg
```

Safer path mapping: read `zip_internal_path` from
`phase16e_czechlynx_direct_zip_manifest.csv`.

## Boundary

This only makes CzechLynx images accessible in Colab. Phase 16E still only runs
streaming model filtering. No final 3000 freeze. No simple top-3000.
""",
        encoding="utf-8",
    )


def main() -> None:
    clean_previous_outputs()
    rows = build_czechlynx_rows()
    duplicate_local_paths = int(rows["local_path_original"].duplicated().sum())
    existing_files = int(rows["local_path_exists"].sum())
    missing_files = int((~rows["local_path_exists"]).sum())
    total_input_size = int(rows["file_size_bytes"].sum())

    manifest = write_zips(rows)
    manifest.to_csv(ZIP_MANIFEST, index=False)
    zip_integrity_pass, zip_integrity_details = verify_zip_integrity(manifest)

    zip_paths = sorted(OUTPUT_DIR.glob(f"{ZIP_PREFIX}_*.zip"))
    each_zip_size_gb = {
        path.name: round(path.stat().st_size / 1024**3, 4)
        for path in zip_paths
    }
    total_zip_size = sum(path.stat().st_size for path in zip_paths)
    audit = {
        "input_manifest": str(INPUT),
        "output_dir": str(OUTPUT_DIR),
        "expected_rows": EXPECTED_ROWS,
        "manifest_rows": int(len(manifest)),
        "existing_files": existing_files,
        "missing_files": missing_files,
        "duplicate_candidate_id": int(rows["candidate_id"].duplicated().sum()),
        "duplicate_local_path_original": duplicate_local_paths,
        "total_input_size_gb": round(total_input_size / 1024**3, 4),
        "total_zip_size_gb": round(total_zip_size / 1024**3, 4),
        "zip_part_count": len(zip_paths),
        "each_zip_size_gb": each_zip_size_gb,
        "zip_integrity_pass": bool(zip_integrity_pass),
        "zip_integrity_details": zip_integrity_details,
        "claim_boundary": (
            "direct CzechLynx split zips for cloud access only; no final 3000 "
            "freeze and no simple top-3000"
        ),
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    write_readme(audit)
    append_phase16e_colab_readme()

    if len(manifest) != EXPECTED_ROWS:
        raise ValueError(f"Zip manifest row mismatch: {len(manifest)}")
    if missing_files != 0:
        raise FileNotFoundError(f"Missing files: {missing_files}")
    if not zip_integrity_pass:
        raise ValueError(f"Zip integrity failed: {zip_integrity_details}")

    print(f"PASS phase16e CzechLynx direct split zips rows={len(manifest)}")
    print(f"WROTE {OUTPUT_DIR}")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
