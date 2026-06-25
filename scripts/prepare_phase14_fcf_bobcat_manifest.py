#!/usr/bin/env python3
"""Prepare a stratified FCF/LILA bobcat manifest for Phase 14."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA_ZIP = Path("/tmp/felidae_conservation_fund_2020_2025.zip")
DATASET_ROOT = PROJECT_ROOT / "data/external/felidae_conservation_fund"
METADATA_DIR = DATASET_ROOT / "metadata"
MANIFEST_DIR = DATASET_ROOT / "manifests"
DEFAULT_FULL_MANIFEST = MANIFEST_DIR / "fcf_bobcat_all_manifest.csv"
DEFAULT_SAMPLE_MANIFEST = MANIFEST_DIR / "fcf_bobcat_3000_manifest.csv"
DEFAULT_AUDIT = MANIFEST_DIR / "fcf_bobcat_3000_manifest_audit.json"

GCP_BASE_URL = "https://storage.googleapis.com/public-datasets-lila/felidae-conservation-fund"
AZURE_BASE_URL = "https://lilawildlife.blob.core.windows.net/lila-wildlife/felidae-conservation-fund"
LICENSE = "Community Data License Agreement - Permissive 1.0"
DATASET_PAGE = "https://lila.science/datasets/felidae-conservation-fund/"
DATASET_NAME = "Felidae Conservation Fund 2020-2025"
RANDOM_SEED = 20260618


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def extract_metadata_json(metadata_zip: Path, metadata_dir: Path) -> Path:
    metadata_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(metadata_zip) as archive:
        json_names = [name for name in archive.namelist() if name.endswith(".json")]
        if len(json_names) != 1:
            raise ValueError(f"expected exactly one JSON metadata file, found {json_names}")
        output = metadata_dir / Path(json_names[0]).name
        if not output.exists() or output.stat().st_size != archive.getinfo(json_names[0]).file_size:
            output.write_bytes(archive.read(json_names[0]))
    return output


def load_bobcat_manifest(metadata_json: Path) -> pd.DataFrame:
    data = json.loads(metadata_json.read_text(encoding="utf-8"))
    categories = {int(category["id"]): category["name"] for category in data["categories"]}
    images = {image["id"]: image for image in data["images"]}
    rows: list[dict[str, Any]] = []
    for annotation in data["annotations"]:
        category_name = categories[int(annotation["category_id"])]
        if category_name != "bobcat":
            continue
        image = images[annotation["image_id"]]
        file_name = image["file_name"]
        dt = str(image.get("datetime", ""))
        location_id = str(image.get("location", "unknown"))
        rows.append(
            {
                "source_dataset": DATASET_NAME,
                "species_label": "bobcat",
                "scientific_name": "Lynx rufus",
                "image_id": image["id"],
                "file_name": file_name,
                "datetime": dt,
                "year": dt[:4] if len(dt) >= 4 else "unknown",
                "month": dt[:7] if len(dt) >= 7 else "unknown",
                "location_id": location_id,
                "annotation_id": annotation.get("id", ""),
                "category_id": int(annotation["category_id"]),
                "download_url": f"{GCP_BASE_URL}/{file_name}",
                "azure_url": f"{AZURE_BASE_URL}/{file_name}",
                "local_relative_path": f"data/external/felidae_conservation_fund/images/bobcat_3000/{file_name}",
                "license": LICENSE,
                "dataset_page": DATASET_PAGE,
            }
        )
    manifest = pd.DataFrame(rows).drop_duplicates("image_id").sort_values(["year", "location_id", "image_id"])
    return manifest.reset_index(drop=True)


def stratified_sample(manifest: pd.DataFrame, sample_size: int, seed: int) -> pd.DataFrame:
    if sample_size > len(manifest):
        raise ValueError(f"sample_size={sample_size} exceeds available bobcat images={len(manifest)}")
    sampled = (
        manifest.groupby(["year", "location_id"], group_keys=False)
        .sample(frac=1.0, random_state=seed)
        .assign(_stratum_order=lambda frame: frame.groupby(["year", "location_id"]).cumcount())
        .sort_values(["_stratum_order", "year", "location_id", "image_id"])
        .head(sample_size)
        .drop(columns=["_stratum_order"])
        .copy()
    )
    sampled = sampled.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    sampled.insert(0, "sample_index", range(1, len(sampled) + 1))
    return sampled


def write_audit(full: pd.DataFrame, sample: pd.DataFrame, audit_path: Path, metadata_json: Path) -> None:
    audit = {
        "dataset": DATASET_NAME,
        "dataset_page": DATASET_PAGE,
        "license": LICENSE,
        "metadata_json": relative(metadata_json),
        "full_bobcat_image_count": int(len(full)),
        "sample_bobcat_image_count": int(len(sample)),
        "full_location_count": int(full["location_id"].nunique()),
        "sample_location_count": int(sample["location_id"].nunique()),
        "full_year_counts": {str(k): int(v) for k, v in full["year"].value_counts().sort_index().items()},
        "sample_year_counts": {str(k): int(v) for k, v in sample["year"].value_counts().sort_index().items()},
        "sample_top_location_counts": {
            str(k): int(v) for k, v in sample["location_id"].value_counts().head(20).items()
        },
        "sampling_method": "round-robin stratified by year and location_id after deterministic within-stratum shuffle",
        "random_seed": RANDOM_SEED,
        "claim_boundary": "urban_periurban_camera_trap_stress_dataset_not_individual_id_validation",
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-zip", default=str(DEFAULT_METADATA_ZIP))
    parser.add_argument("--sample-size", type=int, default=3000)
    parser.add_argument("--full-manifest", default=str(DEFAULT_FULL_MANIFEST))
    parser.add_argument("--sample-manifest", default=str(DEFAULT_SAMPLE_MANIFEST))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    args = parser.parse_args()

    metadata_zip = Path(args.metadata_zip)
    if not metadata_zip.exists():
        raise FileNotFoundError(f"metadata zip not found: {metadata_zip}")
    full_manifest_path = Path(args.full_manifest)
    sample_manifest_path = Path(args.sample_manifest)
    audit_path = Path(args.audit)
    for path in [full_manifest_path, sample_manifest_path, audit_path]:
        if not path.is_absolute():
            path = PROJECT_ROOT / path
    full_manifest_path = PROJECT_ROOT / full_manifest_path if not full_manifest_path.is_absolute() else full_manifest_path
    sample_manifest_path = PROJECT_ROOT / sample_manifest_path if not sample_manifest_path.is_absolute() else sample_manifest_path
    audit_path = PROJECT_ROOT / audit_path if not audit_path.is_absolute() else audit_path

    metadata_json = extract_metadata_json(metadata_zip, METADATA_DIR)
    full = load_bobcat_manifest(metadata_json)
    sample = stratified_sample(full, args.sample_size, RANDOM_SEED)

    full_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    sample_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(full_manifest_path, index=False)
    sample.to_csv(sample_manifest_path, index=False)
    write_audit(full, sample, audit_path, metadata_json)

    print(
        "PASS phase14 FCF bobcat manifest "
        f"full={len(full)} sample={len(sample)} "
        f"locations={sample['location_id'].nunique()} "
        f"output={relative(sample_manifest_path)} audit={relative(audit_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
