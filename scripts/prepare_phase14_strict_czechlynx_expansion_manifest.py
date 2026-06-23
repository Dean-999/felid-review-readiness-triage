#!/usr/bin/env python3
"""Prepare extra non-overlapping CzechLynx candidates for strict 2x2 rescreening."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_MANIFEST = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_real_manifest.csv"
CURRENT_POOL = PROJECT_ROOT / "outputs/phase14/phase14_2x2_evidence_sets/phase14_2x2_combined_evidence_pool.csv"
OUT_DIR = PROJECT_ROOT / "data/interim/czechlynx/phase14"
DEFAULT_OUTPUT = OUT_DIR / "czechlynx_phase14_strict_2x2_extra_15000_manifest.csv"
DEFAULT_AUDIT = OUT_DIR / "czechlynx_phase14_strict_2x2_extra_15000_manifest_audit.json"


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path_text: object) -> str:
    path = Path(str(path_text))
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def choose_identity_balanced(raw: pd.DataFrame, used_paths: set[str], sample_size: int) -> pd.DataFrame:
    candidates = raw[
        raw["image_exists"].eq(True)
        & raw["unique_name"].notna()
        & ~raw["local_image_path"].astype(str).map(rel).isin(used_paths)
        & ~raw["path"].astype(str).isin(used_paths)
    ].copy()
    candidates["identity_label"] = candidates["unique_name"].astype(str)
    candidates = candidates.sort_values(["identity_label", "date", "encounter", "path"]).reset_index(drop=True)

    selected_rows: list[pd.Series] = []
    selected_paths: set[str] = set()
    groups = {str(k): g.reset_index(drop=True) for k, g in candidates.groupby("identity_label", sort=True)}
    depth = 0
    while len(selected_rows) < sample_size:
        added = 0
        for identity in sorted(groups):
            group = groups[identity]
            if depth >= len(group):
                continue
            row = group.iloc[depth]
            path_key = rel(row["local_image_path"])
            if path_key in selected_paths:
                continue
            selected_rows.append(row)
            selected_paths.add(path_key)
            added += 1
            if len(selected_rows) >= sample_size:
                break
        if added == 0:
            break
        depth += 1
    if len(selected_rows) < sample_size:
        raise ValueError(f"only selected {len(selected_rows)} rows, requested {sample_size}")

    selected = pd.DataFrame(selected_rows).reset_index(drop=True)
    selected.insert(0, "phase14_review_index", range(1, len(selected) + 1))
    selected["expanded_image_id"] = [f"czlx_phase14_strict_extra_{i:05d}" for i in range(1, len(selected) + 1)]
    selected["identity_label"] = selected["unique_name"].astype(str)
    selected["review_image_path_local"] = selected["local_image_path"].map(rel)
    selected["local_image_path"] = selected["local_image_path"].map(rel)
    selected["phase14_source_role"] = "phase14_strict_2x2_nonoverlap_expansion_candidate"
    selected["phase14_label_status"] = "ai_first_pass_needed"
    selected["source_dataset"] = "CzechLynx"
    selected["context"] = "wild_known_id"
    selected["species_label"] = "Eurasian lynx"
    selected["scientific_name"] = "Lynx lynx"
    selected["image_exists"] = [
        "yes" if (PROJECT_ROOT / str(path)).exists() else "no"
        for path in selected["review_image_path_local"]
    ]
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-manifest", default=str(RAW_MANIFEST))
    parser.add_argument("--current-pool", default=str(CURRENT_POOL))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--sample-size", type=int, default=15000)
    args = parser.parse_args()

    raw = pd.read_csv(resolve(args.raw_manifest))
    current = pd.read_csv(resolve(args.current_pool), low_memory=False)
    current_czech = current[current["dataset_role"].astype(str).eq("czechlynx")].copy()
    used_paths = set(current_czech["evidence_image_path"].astype(str))
    selected = choose_identity_balanced(raw, used_paths, args.sample_size)

    output = resolve(args.output)
    audit_path = resolve(args.audit)
    output.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "phase14_review_index",
        "expanded_image_id",
        "identity_label",
        "source",
        "date",
        "encounter",
        "path",
        "local_image_path",
        "review_image_path_local",
        "relative_age",
        "coat_pattern",
        "phase14_source_role",
        "phase14_label_status",
        "source_dataset",
        "context",
        "species_label",
        "scientific_name",
        "image_exists",
    ]
    selected[columns].to_csv(output, index=False)

    overlap = int(selected["review_image_path_local"].astype(str).isin(used_paths).sum())
    counts = selected["identity_label"].astype(str).value_counts()
    audit = {
        "raw_manifest": rel(resolve(args.raw_manifest)),
        "current_pool": rel(resolve(args.current_pool)),
        "output": rel(output),
        "raw_count": int(len(raw)),
        "current_czech_pool_count": int(len(current_czech)),
        "used_path_count": int(len(used_paths)),
        "sample_count": int(len(selected)),
        "overlap_with_current_pool": overlap,
        "identity_count": int(counts.size),
        "min_images_per_identity": int(counts.min()),
        "median_images_per_identity": float(counts.median()),
        "max_images_per_identity": int(counts.max()),
        "missing_images": int(selected["image_exists"].ne("yes").sum()),
        "sampling_method": "non-overlap identity-balanced round-robin over unused CzechLynx raw images",
        "claim_boundary": "extra candidates for strict 2x2 rescreening, not human-reviewed labels",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = "PASS" if overlap == 0 and audit["missing_images"] == 0 else "FAIL"
    print(
        f"{status} phase14 strict CzechLynx expansion manifest "
        f"rows={len(selected)} identities={counts.size} output={rel(output)}"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
