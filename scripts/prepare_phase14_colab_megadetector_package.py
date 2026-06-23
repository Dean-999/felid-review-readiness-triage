#!/usr/bin/env python3
"""Prepare Phase 14 bobcat/CzechLynx high-candidate image packages for Colab MegaDetector."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POOL = PROJECT_ROOT / "outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_combined_candidate_pool.csv"
DEFAULT_OUT = PROJECT_ROOT / "outputs/phase14/phase14_colab_megadetector_package"
COLAB_RUNNER = PROJECT_ROOT / "colab/phase14_megadetector_selection/run_phase14_megadetector_colab.py"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def clean_existing_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def build_manifest(pool_path: Path, max_per_dataset: int | None) -> pd.DataFrame:
    pool = pd.read_csv(pool_path, low_memory=False)
    high = pool[pool["strict_evidence_tier"].eq("high_confidence")].copy()
    high = high[high["environment_context"].isin(["urban_periurban", "wild"])].copy()
    high["dataset_label"] = high["environment_context"].map(
        {"urban_periurban": "bobcat", "wild": "czechlynx"}
    )
    high["candidate_source_path"] = high["evidence_image_path"].astype(str)
    high["candidate_source_exists"] = high["candidate_source_path"].map(lambda p: resolve(p).exists())
    high = high[high["candidate_source_exists"]].copy()

    sort_cols = [
        "dataset_label",
        "pool_source",
        "auto_evidence_score",
        "auto_quality_score",
        "blur_laplacian_var",
        "contrast_std",
    ]
    ascending = [True, True, False, False, False, False]
    sort_cols = [col for col in sort_cols if col in high.columns]
    ascending = ascending[: len(sort_cols)]
    high = high.sort_values(sort_cols, ascending=ascending).copy()

    if max_per_dataset:
        high = high.groupby("dataset_label", group_keys=False).head(max_per_dataset).copy()

    high["phase14_md_candidate_id"] = [
        f"phase14_md_{dataset}_{i:05d}"
        for dataset, i in high.groupby("dataset_label").cumcount().add(1).items()
    ]
    # The line above used Series.items index, not label. Rebuild deterministically per row.
    ids = []
    counters: dict[str, int] = {}
    for dataset in high["dataset_label"].tolist():
        counters[dataset] = counters.get(dataset, 0) + 1
        ids.append(f"phase14_md_{dataset}_{counters[dataset]:05d}")
    high["phase14_md_candidate_id"] = ids

    high["colab_image_relpath"] = high.apply(
        lambda r: f"images/{r['dataset_label']}/{r['phase14_md_candidate_id']}{Path(str(r['candidate_source_path'])).suffix.lower() or '.jpg'}",
        axis=1,
    )
    return high.reset_index(drop=True)


def build_packaged_manifest(manifest: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in manifest.iterrows():
        src = resolve(row["candidate_source_path"])
        out = row.to_dict()
        out["source_file_size_bytes"] = src.stat().st_size
        rows.append(out)
    return pd.DataFrame(rows)


def write_zip_chunks(package_manifest: pd.DataFrame, out_dir: Path, chunk_size: int) -> pd.DataFrame:
    rows = []
    for dataset, dataset_rows in package_manifest.groupby("dataset_label", sort=True):
        dataset_rows = dataset_rows.reset_index(drop=True)
        for chunk_index, start in enumerate(range(0, len(dataset_rows), chunk_size), start=1):
            chunk = dataset_rows.iloc[start : start + chunk_size].copy()
            zip_name = f"phase14_md_{dataset}_images_part_{chunk_index:02d}.zip"
            zip_path = out_dir / zip_name
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
                for _, row in chunk.iterrows():
                    src = resolve(row["candidate_source_path"])
                    zf.write(src, arcname=row["colab_image_relpath"])
            rows.append(
                {
                    "dataset_label": dataset,
                    "chunk_index": chunk_index,
                    "zip_path": rel(zip_path),
                    "rows": len(chunk),
                    "zip_size_bytes": zip_path.stat().st_size,
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", default=str(DEFAULT_POOL))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--max-per-dataset", type=int, default=None)
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument(
        "--zip-datasets",
        default="czechlynx",
        help="Comma-separated dataset labels to package as image zips. Bobcat can be downloaded in Colab from download_url.",
    )
    args = parser.parse_args()

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_root = out_dir

    manifest = build_manifest(resolve(args.pool), args.max_per_dataset)
    manifest.to_csv(out_dir / "phase14_colab_megadetector_manifest.csv", index=False)

    zip_datasets = {item.strip() for item in args.zip_datasets.split(",") if item.strip()}
    if args.manifest_only:
        packaged = manifest.copy()
        packaged["source_file_size_bytes"] = 0
        zip_index = pd.DataFrame()
    else:
        packaged = build_packaged_manifest(manifest)
        packaged.to_csv(out_dir / "phase14_colab_megadetector_packaged_manifest.csv", index=False)
        zippable = packaged[packaged["dataset_label"].isin(zip_datasets)].copy()
        zip_index = write_zip_chunks(zippable, zip_root, args.chunk_size)
        zip_index.to_csv(out_dir / "phase14_colab_megadetector_zip_index.csv", index=False)

    if COLAB_RUNNER.exists():
        shutil.copy2(COLAB_RUNNER, out_dir / COLAB_RUNNER.name)

    dataset_counts = {str(k): int(v) for k, v in manifest["dataset_label"].value_counts().sort_index().items()}
    summary = {
        "candidate_rows": int(len(manifest)),
        "candidate_counts_by_dataset": dataset_counts,
        "source_pool": rel(resolve(args.pool)),
        "chunk_size": args.chunk_size,
        "zip_images_from_source_without_copying": not args.manifest_only,
        "zip_datasets": sorted(zip_datasets),
        "non_zipped_datasets_should_be_downloaded_in_colab": sorted(set(dataset_counts) - zip_datasets),
        "zip_count": int(len(zip_index)),
        "zip_total_size_bytes": int(zip_index["zip_size_bytes"].sum()) if not zip_index.empty else 0,
        "outputs": {
            "manifest": rel(out_dir / "phase14_colab_megadetector_manifest.csv"),
            "packaged_manifest": rel(out_dir / "phase14_colab_megadetector_packaged_manifest.csv"),
            "zip_index": rel(out_dir / "phase14_colab_megadetector_zip_index.csv"),
            "package_dir": rel(out_dir),
            "colab_runner": rel(out_dir / COLAB_RUNNER.name),
        },
    }
    (out_dir / "phase14_colab_megadetector_package_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS phase14 Colab MegaDetector package "
        f"rows={summary['candidate_rows']} counts={dataset_counts} "
        f"zips={summary['zip_count']} out={rel(out_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
