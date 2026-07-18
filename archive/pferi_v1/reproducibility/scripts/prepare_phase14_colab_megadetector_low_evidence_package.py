#!/usr/bin/env python3
"""Prepare Phase 14 low-evidence stress candidates for Colab MegaDetector conflict screening."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOBCAT_LOW = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_bobcat_low_evidence_stress_3000.csv"
)
DEFAULT_CZECHLYNX_LOW = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_czechlynx_low_evidence_stress_3000.csv"
)
DEFAULT_OUT = PROJECT_ROOT / "outputs/phase14/phase14_colab_megadetector_low_evidence_package"
COLAB_RUNNER = PROJECT_ROOT / "colab/phase14_megadetector_selection/run_phase14_megadetector_colab.py"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def source_path(row: pd.Series) -> str:
    for col in ["evidence_image_path", "local_image_path", "review_image_path_local", "local_relative_path"]:
        value = row.get(col)
        if pd.notna(value) and str(value).strip() and str(value).lower() != "nan":
            return str(value)
    raise ValueError("row has no usable local image path")


def load_low_set(path: Path, dataset_label: str, max_rows: int | None) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False).copy()
    frame["dataset_label"] = dataset_label
    frame["evidence_set_label"] = "low_evidence_stress"
    frame["candidate_source_path"] = frame.apply(source_path, axis=1)
    frame["candidate_source_exists"] = frame["candidate_source_path"].map(lambda p: resolve(p).exists())
    missing = frame[~frame["candidate_source_exists"]]
    if not missing.empty:
        raise FileNotFoundError(
            f"{len(missing)} {dataset_label} low-evidence rows do not resolve to local files; "
            f"first missing path: {missing.iloc[0]['candidate_source_path']}"
        )
    sort_cols = [
        "dataset_label",
        "strict_set_index",
        "auto_evidence_score",
        "auto_quality_score",
        "blur_laplacian_var",
        "contrast_std",
    ]
    ascending = [True, True, True, True, True, True]
    sort_cols = [col for col in sort_cols if col in frame.columns]
    ascending = ascending[: len(sort_cols)]
    frame = frame.sort_values(sort_cols, ascending=ascending).copy()
    if max_rows:
        frame = frame.head(max_rows).copy()
    ids = []
    for i in range(1, len(frame) + 1):
        ids.append(f"phase14_md_low_{dataset_label}_{i:05d}")
    frame["phase14_md_candidate_id"] = ids
    frame["colab_image_relpath"] = frame.apply(
        lambda r: (
            f"images/{r['dataset_label']}_low/{r['phase14_md_candidate_id']}"
            f"{Path(str(r['candidate_source_path'])).suffix.lower() or '.jpg'}"
        ),
        axis=1,
    )
    return frame.reset_index(drop=True)


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
            zip_name = f"phase14_md_low_{dataset}_images_part_{chunk_index:02d}.zip"
            zip_path = out_dir / zip_name
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
                for _, row in chunk.iterrows():
                    src = resolve(row["candidate_source_path"])
                    zf.write(src, arcname=row["colab_image_relpath"])
            rows.append(
                {
                    "dataset_label": dataset,
                    "evidence_set_label": "low_evidence_stress",
                    "chunk_index": chunk_index,
                    "zip_path": rel(zip_path),
                    "rows": len(chunk),
                    "zip_size_bytes": zip_path.stat().st_size,
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bobcat-low", default=str(DEFAULT_BOBCAT_LOW))
    parser.add_argument("--czechlynx-low", default=str(DEFAULT_CZECHLYNX_LOW))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--max-per-dataset", type=int, default=3000)
    parser.add_argument(
        "--zip-datasets",
        default="czechlynx",
        help="Comma-separated dataset labels to package as image zips. Bobcat can be downloaded in Colab from download_url.",
    )
    args = parser.parse_args()

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    bobcat = load_low_set(resolve(args.bobcat_low), "bobcat", args.max_per_dataset)
    czechlynx = load_low_set(resolve(args.czechlynx_low), "czechlynx", args.max_per_dataset)
    manifest = pd.concat([bobcat, czechlynx], ignore_index=True)
    manifest.to_csv(out_dir / "phase14_colab_megadetector_manifest.csv", index=False)

    packaged = build_packaged_manifest(manifest)
    packaged.to_csv(out_dir / "phase14_colab_megadetector_packaged_manifest.csv", index=False)

    zip_datasets = {item.strip() for item in args.zip_datasets.split(",") if item.strip()}
    zippable = packaged[packaged["dataset_label"].isin(zip_datasets)].copy()
    zip_index = write_zip_chunks(zippable, out_dir, args.chunk_size)
    zip_index.to_csv(out_dir / "phase14_colab_megadetector_zip_index.csv", index=False)

    if COLAB_RUNNER.exists():
        shutil.copy2(COLAB_RUNNER, out_dir / COLAB_RUNNER.name)

    dataset_counts = {str(k): int(v) for k, v in manifest["dataset_label"].value_counts().sort_index().items()}
    summary = {
        "candidate_rows": int(len(manifest)),
        "candidate_counts_by_dataset": dataset_counts,
        "evidence_set_label": "low_evidence_stress",
        "source_low_sets": {
            "bobcat": rel(resolve(args.bobcat_low)),
            "czechlynx": rel(resolve(args.czechlynx_low)),
        },
        "chunk_size": args.chunk_size,
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
    (out_dir / "phase14_colab_megadetector_low_evidence_package_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS phase14 Colab MegaDetector low-evidence package "
        f"rows={summary['candidate_rows']} counts={dataset_counts} "
        f"zips={summary['zip_count']} out={rel(out_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
