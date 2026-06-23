#!/usr/bin/env python3
"""Prepare Phase 14 low-evidence top-up candidates for Colab MegaDetector.

Bobcat candidates are not downloaded locally; the Colab runner downloads them
from LILA URLs. CzechLynx candidates are local raw/review images and are zipped
for Colab upload.
"""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_low_evidence_topup_colab_package"
COLAB_RUNNER = PROJECT_ROOT / "colab/phase14_megadetector_selection/run_phase14_megadetector_colab.py"

BOBCAT_ALL = PROJECT_ROOT / "data/external/felidae_conservation_fund/manifests/fcf_bobcat_all_manifest.csv"
BOBCAT_MD_HIGH = PROJECT_ROOT / "outputs/phase14/phase14_lila_md_prefilter/fcf_bobcat_md_high_prefilter_all_passed.csv"
BOBCAT_HIGH_WORKING = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_final_2x2_working_labels/phase14_bobcat_high_confidence_3000_working_final_labels.csv"
)
BOBCAT_LOW_FINAL = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_colab_megadetector_low_evidence_final_selection/phase14_bobcat_megadetector_low_evidence_stress_final.csv"
)
CZECH_HIGH_WORKING = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_high_confidence_3000_working_final_labels.csv"
)
CZECH_LOW_FINAL = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_colab_megadetector_low_evidence_final_selection/phase14_czechlynx_megadetector_low_evidence_stress_final.csv"
)
LOW_GATED = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_colab_megadetector_low_evidence_final_selection/phase14_colab_megadetector_all_low_evidence_gated_candidates.csv"
)
HIGH_GATED = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_colab_megadetector_final_selection/phase14_colab_megadetector_all_gated_candidates.csv"
)
COMBINED_POOL = PROJECT_ROOT / "outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_combined_candidate_pool.csv"


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def collect_values(csv_path: Path, columns: list[str]) -> set[str]:
    if not csv_path.exists():
        return set()
    frame = pd.read_csv(csv_path, low_memory=False)
    values: set[str] = set()
    for col in columns:
        if col in frame.columns:
            values.update(frame[col].dropna().astype(str))
    return {v for v in values if v and v.lower() != "nan"}


def bobcat_candidates(limit: int) -> pd.DataFrame:
    all_manifest = pd.read_csv(BOBCAT_ALL, low_memory=False)
    md_high = pd.read_csv(BOBCAT_MD_HIGH, low_memory=False)
    used_ids = collect_values(BOBCAT_HIGH_WORKING, ["image_id"]) | collect_values(BOBCAT_LOW_FINAL, ["image_id"])
    used_ids |= collect_values(LOW_GATED, ["image_id"]) | collect_values(HIGH_GATED, ["image_id"])
    high_ids = set(md_high["image_id"].dropna().astype(str))

    candidates = all_manifest[
        ~all_manifest["image_id"].astype(str).isin(used_ids)
        & ~all_manifest["image_id"].astype(str).isin(high_ids)
    ].copy()
    candidates["dataset_label"] = "bobcat"
    candidates["evidence_set_label"] = "low_evidence_topup"
    candidates["candidate_source_path"] = candidates["local_relative_path"]
    candidates["candidate_source_exists"] = candidates["candidate_source_path"].map(lambda p: resolve(p).exists())
    candidates["phase14_low_topup_source"] = "fcf_not_currently_used_and_not_lila_md_high_prefilter"
    candidates = (
        candidates.groupby(["year", "location_id"], group_keys=False)
        .sample(frac=1.0, random_state=20260621)
        .assign(_stratum_order=lambda x: x.groupby(["year", "location_id"]).cumcount())
        .sort_values(["_stratum_order", "year", "location_id", "image_id"])
        .head(limit)
        .drop(columns=["_stratum_order"])
        .reset_index(drop=True)
    )
    candidates["phase14_md_candidate_id"] = [
        f"phase14_lowtopup_bobcat_{i:05d}" for i in range(1, len(candidates) + 1)
    ]
    candidates["colab_image_relpath"] = candidates["phase14_md_candidate_id"].map(
        lambda x: f"images/bobcat_low_topup/{x}.jpg"
    )
    return candidates


def first_path(row: pd.Series) -> str:
    for col in ["candidate_source_path", "evidence_image_path", "local_image_path", "review_image_path_local", "local_relative_path"]:
        value = row.get(col)
        if pd.notna(value) and str(value).strip() and str(value).lower() != "nan":
            return str(value)
    return ""


def czechlynx_candidates(limit: int) -> pd.DataFrame:
    pool = pd.read_csv(COMBINED_POOL, low_memory=False)
    pool = pool[pool["source_dataset"].eq("CzechLynx") & pool["strict_evidence_tier"].eq("low_evidence_stress")].copy()
    pool["candidate_source_path"] = pool.apply(first_path, axis=1)
    used_paths = collect_values(CZECH_HIGH_WORKING, ["candidate_source_path", "local_image_path", "review_image_path_local"])
    used_paths |= collect_values(CZECH_LOW_FINAL, ["candidate_source_path", "local_image_path", "review_image_path_local"])
    used_paths |= collect_values(LOW_GATED, ["candidate_source_path", "local_image_path", "review_image_path_local"])
    used_paths |= collect_values(HIGH_GATED, ["candidate_source_path", "local_image_path", "review_image_path_local"])
    pool = pool[~pool["candidate_source_path"].astype(str).isin(used_paths)].copy()
    pool["candidate_source_exists"] = pool["candidate_source_path"].map(lambda p: resolve(p).exists())
    pool = pool[pool["candidate_source_exists"]].copy()
    pool["dataset_label"] = "czechlynx"
    pool["evidence_set_label"] = "low_evidence_topup"
    pool["phase14_low_topup_source"] = "strict_low_evidence_unused_czechlynx_pool"
    for col in ["auto_evidence_score", "auto_quality_score", "blur_laplacian_var", "contrast_std"]:
        if col not in pool.columns:
            pool[col] = 0
        pool[col] = pd.to_numeric(pool[col], errors="coerce").fillna(0)
    pool = pool.sort_values(
        ["auto_evidence_score", "auto_quality_score", "blur_laplacian_var", "contrast_std", "candidate_source_path"],
        ascending=[True, True, True, True, True],
    ).head(limit).reset_index(drop=True)
    pool["phase14_md_candidate_id"] = [
        f"phase14_lowtopup_czechlynx_{i:05d}" for i in range(1, len(pool) + 1)
    ]
    pool["colab_image_relpath"] = pool.apply(
        lambda row: (
            f"images/czechlynx_low_topup/{row['phase14_md_candidate_id']}"
            f"{Path(str(row['candidate_source_path'])).suffix.lower() or '.jpg'}"
        ),
        axis=1,
    )
    return pool


def write_zip_chunks(package_manifest: pd.DataFrame, out_dir: Path, chunk_size: int) -> pd.DataFrame:
    rows = []
    czech = package_manifest[package_manifest["dataset_label"].eq("czechlynx")].reset_index(drop=True)
    for chunk_index, start in enumerate(range(0, len(czech), chunk_size), start=1):
        chunk = czech.iloc[start : start + chunk_size].copy()
        zip_path = out_dir / f"phase14_lowtopup_czechlynx_images_part_{chunk_index:02d}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for _, row in chunk.iterrows():
                zf.write(resolve(row["candidate_source_path"]), arcname=row["colab_image_relpath"])
        rows.append(
            {
                "dataset_label": "czechlynx",
                "chunk_index": chunk_index,
                "zip_path": rel(zip_path),
                "rows": len(chunk),
                "zip_size_bytes": zip_path.stat().st_size,
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--bobcat-count", type=int, default=1500)
    parser.add_argument("--czechlynx-count", type=int, default=2500)
    parser.add_argument("--chunk-size", type=int, default=1000)
    args = parser.parse_args()

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bobcat = bobcat_candidates(args.bobcat_count)
    czech = czechlynx_candidates(args.czechlynx_count)
    manifest = pd.concat([bobcat, czech], ignore_index=True, sort=False)
    manifest.to_csv(out_dir / "phase14_colab_megadetector_manifest.csv", index=False)
    manifest.to_csv(out_dir / "phase14_colab_megadetector_packaged_manifest.csv", index=False)
    zip_index = write_zip_chunks(manifest, out_dir, args.chunk_size)
    zip_index.to_csv(out_dir / "phase14_colab_megadetector_zip_index.csv", index=False)
    if COLAB_RUNNER.exists():
        shutil.copy2(COLAB_RUNNER, out_dir / COLAB_RUNNER.name)

    summary = {
        "candidate_counts_by_dataset": {
            "bobcat": int(len(bobcat)),
            "czechlynx": int(len(czech)),
        },
        "bobcat_candidate_rule": "FCF all bobcat minus current high/low/gated usage and minus LILA MD high-prefilter passed rows; downloaded in Colab from URL",
        "czechlynx_candidate_rule": "CzechLynx strict low-evidence unused pool sorted toward weakest auto evidence; zipped for Colab",
        "zip_count": int(len(zip_index)),
        "zip_total_size_bytes": int(zip_index["zip_size_bytes"].sum()) if not zip_index.empty else 0,
        "outputs": {
            "manifest": rel(out_dir / "phase14_colab_megadetector_manifest.csv"),
            "packaged_manifest": rel(out_dir / "phase14_colab_megadetector_packaged_manifest.csv"),
            "zip_index": rel(out_dir / "phase14_colab_megadetector_zip_index.csv"),
            "colab_runner": rel(out_dir / "run_phase14_megadetector_colab.py"),
        },
    }
    (out_dir / "phase14_low_evidence_topup_package_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS phase14 low-evidence topup Colab package "
        f"bobcat={len(bobcat)} czechlynx={len(czech)} zips={len(zip_index)} out={rel(out_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
