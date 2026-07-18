#!/usr/bin/env python3
"""Package CzechLynx high-confidence top-up candidates for Colab MegaDetector screening."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "outputs/phase14/phase14_czechlynx_high_topup/phase14_czechlynx_high_topup_candidate_manifest.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_czechlynx_high_topup_colab_package"
COLAB_RUNNER = PROJECT_ROOT / "colab/phase14_megadetector_selection/run_phase14_megadetector_colab.py"


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def write_zip_chunks(package_manifest: pd.DataFrame, out_dir: Path, chunk_size: int) -> pd.DataFrame:
    rows = []
    for chunk_index, start in enumerate(range(0, len(package_manifest), chunk_size), start=1):
        chunk = package_manifest.iloc[start : start + chunk_size].copy()
        zip_path = out_dir / f"phase14_czechlynx_high_topup_images_part_{chunk_index:02d}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for _, row in chunk.iterrows():
                zf.write(resolve(row["candidate_source_path"]), arcname=row["colab_image_relpath"])
        rows.append(
            {
                "dataset_label": "czechlynx",
                "chunk_index": chunk_index,
                "zip_path": rel(zip_path),
                "rows": int(len(chunk)),
                "zip_size_bytes": int(zip_path.stat().st_size),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--chunk-size", type=int, default=1000)
    args = parser.parse_args()

    manifest_path = resolve(args.manifest)
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(manifest_path, low_memory=False).copy()
    manifest["dataset_label"] = "czechlynx"
    manifest["colab_image_relpath"] = manifest.apply(
        lambda r: (
            f"images/czechlynx_high_topup/{r['phase14_md_candidate_id']}"
            f"{Path(str(r['candidate_source_path'])).suffix.lower() or '.jpg'}"
        ),
        axis=1,
    )
    manifest["candidate_source_exists"] = manifest["candidate_source_path"].map(lambda p: resolve(p).exists())
    missing = manifest[~manifest["candidate_source_exists"]]
    if not missing.empty:
        raise FileNotFoundError(f"{len(missing)} candidate images are missing; first={missing.iloc[0]['candidate_source_path']}")

    package_manifest = manifest.copy()
    package_manifest["source_file_size_bytes"] = package_manifest["candidate_source_path"].map(lambda p: resolve(p).stat().st_size)
    manifest_out = out_dir / "phase14_colab_megadetector_manifest.csv"
    package_manifest.to_csv(manifest_out, index=False)
    package_manifest.to_csv(out_dir / "phase14_colab_megadetector_packaged_manifest.csv", index=False)
    zip_index = write_zip_chunks(package_manifest, out_dir, args.chunk_size)
    zip_index.to_csv(out_dir / "phase14_colab_megadetector_zip_index.csv", index=False)

    if COLAB_RUNNER.exists():
        shutil.copy2(COLAB_RUNNER, out_dir / COLAB_RUNNER.name)

    summary = {
        "candidate_rows": int(len(package_manifest)),
        "candidate_counts_by_dataset": {"czechlynx": int(len(package_manifest))},
        "source_manifest": rel(manifest_path),
        "chunk_size": args.chunk_size,
        "zip_count": int(len(zip_index)),
        "zip_total_size_bytes": int(zip_index["zip_size_bytes"].sum()) if not zip_index.empty else 0,
        "outputs": {
            "manifest": rel(manifest_out),
            "packaged_manifest": rel(out_dir / "phase14_colab_megadetector_packaged_manifest.csv"),
            "zip_index": rel(out_dir / "phase14_colab_megadetector_zip_index.csv"),
            "package_dir": rel(out_dir),
            "colab_runner": rel(out_dir / COLAB_RUNNER.name),
        },
    }
    (out_dir / "phase14_czechlynx_high_topup_colab_package_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS packaged CzechLynx high top-up Colab package "
        f"rows={summary['candidate_rows']} zips={summary['zip_count']} out={rel(out_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
