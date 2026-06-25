#!/usr/bin/env python3
"""Prepare non-overlapping FCF bobcat expansion candidates for 2x2 evidence sets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/manifests"
DEFAULT_ALL = MANIFEST_DIR / "fcf_bobcat_all_manifest.csv"
DEFAULT_EXISTING = MANIFEST_DIR / "fcf_bobcat_3000_manifest.csv"
DEFAULT_OUTPUT = MANIFEST_DIR / "fcf_bobcat_phase14_2x2_expansion_6000_manifest.csv"
DEFAULT_AUDIT = MANIFEST_DIR / "fcf_bobcat_phase14_2x2_expansion_6000_manifest_audit.json"
EXPANSION_IMAGE_ROOT = "data/external/felidae_conservation_fund/images/bobcat_phase14_2x2_expansion_6000"
RANDOM_SEED = 20260619


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def stratified_round_robin(manifest: pd.DataFrame, sample_size: int, seed: int) -> pd.DataFrame:
    if sample_size > len(manifest):
        raise ValueError(f"sample_size={sample_size} exceeds unused candidates={len(manifest)}")
    sampled = (
        manifest.groupby(["year", "location_id"], group_keys=False)
        .sample(frac=1.0, random_state=seed)
        .assign(_stratum_order=lambda frame: frame.groupby(["year", "location_id"]).cumcount())
        .sort_values(["_stratum_order", "year", "location_id", "image_id"])
        .head(sample_size)
        .drop(columns=["_stratum_order"])
        .sample(frac=1.0, random_state=seed)
        .reset_index(drop=True)
    )
    sampled.insert(0, "expansion_index", range(1, len(sampled) + 1))
    sampled["sample_index"] = sampled["expansion_index"]
    sampled["phase14_2x2_source_role"] = "bobcat_nonoverlap_expansion_candidate"
    sampled["local_relative_path"] = sampled["file_name"].map(lambda name: f"{EXPANSION_IMAGE_ROOT}/{name}")
    return sampled


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-manifest", default=str(DEFAULT_ALL))
    parser.add_argument("--existing-manifest", default=str(DEFAULT_EXISTING))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--sample-size", type=int, default=6000)
    args = parser.parse_args()

    all_manifest = pd.read_csv(resolve(args.all_manifest))
    existing = pd.read_csv(resolve(args.existing_manifest))
    used_ids = set(existing["image_id"].astype(str))
    used_files = set(existing["file_name"].astype(str))
    unused = all_manifest[
        ~all_manifest["image_id"].astype(str).isin(used_ids)
        & ~all_manifest["file_name"].astype(str).isin(used_files)
    ].copy()

    sample = stratified_round_robin(unused, args.sample_size, RANDOM_SEED)
    output = resolve(args.output)
    audit_path = resolve(args.audit)
    output.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(output, index=False)

    overlap_ids = int(sample["image_id"].astype(str).isin(used_ids).sum())
    overlap_files = int(sample["file_name"].astype(str).isin(used_files).sum())
    audit = {
        "all_manifest": str(resolve(args.all_manifest).relative_to(PROJECT_ROOT)),
        "existing_manifest": str(resolve(args.existing_manifest).relative_to(PROJECT_ROOT)),
        "output": str(output.relative_to(PROJECT_ROOT)),
        "all_bobcat_count": int(len(all_manifest)),
        "existing_count": int(len(existing)),
        "unused_count": int(len(unused)),
        "sample_count": int(len(sample)),
        "overlap_image_id_with_existing": overlap_ids,
        "overlap_file_name_with_existing": overlap_files,
        "location_count": int(sample["location_id"].nunique()),
        "year_counts": {str(k): int(v) for k, v in sample["year"].value_counts().sort_index().items()},
        "sampling_method": "non-overlap year-location round-robin stratified sample",
        "random_seed": RANDOM_SEED,
        "claim_boundary": "expansion_candidates_for_2x2_evidence_routing_not_identity_validation",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = "PASS" if overlap_ids == 0 and overlap_files == 0 else "FAIL"
    print(
        f"{status} phase14 2x2 bobcat expansion manifest "
        f"rows={len(sample)} unused_pool={len(unused)} locations={sample['location_id'].nunique()} "
        f"output={output.relative_to(PROJECT_ROOT)}"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
