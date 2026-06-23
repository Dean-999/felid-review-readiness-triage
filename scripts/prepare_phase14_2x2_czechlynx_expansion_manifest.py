#!/usr/bin/env python3
"""Prepare non-overlapping CzechLynx expansion candidates for 2x2 evidence sets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_MANIFEST = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_real_manifest.csv"
EXISTING_MANIFEST = PROJECT_ROOT / "data/interim/czechlynx/phase14/czechlynx_phase14_3000_manifest.csv"
OUT_DIR = PROJECT_ROOT / "data/interim/czechlynx/phase14"
DEFAULT_OUTPUT = OUT_DIR / "czechlynx_phase14_2x2_expansion_6000_manifest.csv"
DEFAULT_AUDIT = OUT_DIR / "czechlynx_phase14_2x2_expansion_6000_manifest_audit.json"


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path_text: object) -> str:
    path = Path(str(path_text))
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def choose_identity_balanced(raw: pd.DataFrame, existing: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    used_paths = set(existing["path"].astype(str))
    used_review_paths = set(existing["review_image_path_local"].astype(str))
    existing_counts = existing["identity_label"].astype(str).value_counts().to_dict()
    candidates = raw[
        raw["image_exists"].eq(True)
        & raw["unique_name"].notna()
        & ~raw["path"].astype(str).isin(used_paths)
        & ~raw["local_image_path"].astype(str).map(rel).isin(used_review_paths)
    ].copy()
    candidates["identity_label"] = candidates["unique_name"].astype(str)
    candidates = candidates.sort_values(["identity_label", "date", "encounter", "path"]).reset_index(drop=True)

    selected_rows: list[pd.Series] = []
    selected_paths: set[str] = set()
    counts = {str(k): int(v) for k, v in existing_counts.items()}
    cap = 0
    while len(selected_rows) < sample_size:
        cap += 1
        round_added = 0
        for identity, group in candidates.groupby("identity_label", sort=True):
            if counts.get(identity, 0) >= cap:
                continue
            available = group[~group["path"].astype(str).isin(selected_paths)]
            if available.empty:
                continue
            row = available.iloc[0]
            selected_rows.append(row)
            selected_paths.add(str(row["path"]))
            counts[identity] = counts.get(identity, 0) + 1
            round_added += 1
            if len(selected_rows) >= sample_size:
                break
        if round_added == 0 and cap > max(counts.values(), default=0) + sample_size:
            break
    if len(selected_rows) < sample_size:
        raise ValueError(f"only selected {len(selected_rows)} rows, requested {sample_size}")
    selected = pd.DataFrame(selected_rows).reset_index(drop=True)
    selected.insert(0, "phase14_review_index", range(1, len(selected) + 1))
    selected["expanded_image_id"] = [f"czlx_phase14_2x2_extra_{i:04d}" for i in range(1, len(selected) + 1)]
    selected["identity_label"] = selected["unique_name"].astype(str)
    selected["review_image_path_local"] = selected["local_image_path"].map(rel)
    selected["local_image_path"] = selected["local_image_path"].map(rel)
    selected["phase14_source_role"] = "phase14_2x2_nonoverlap_expansion_candidate"
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
    parser.add_argument("--existing-manifest", default=str(EXISTING_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--sample-size", type=int, default=6000)
    args = parser.parse_args()

    raw = pd.read_csv(resolve(args.raw_manifest))
    existing = pd.read_csv(resolve(args.existing_manifest))
    selected = choose_identity_balanced(raw, existing, args.sample_size)
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

    used_paths = set(existing["path"].astype(str))
    overlap_paths = int(selected["path"].astype(str).isin(used_paths).sum())
    counts = selected["identity_label"].value_counts()
    audit = {
        "raw_manifest": str(resolve(args.raw_manifest).relative_to(PROJECT_ROOT)),
        "existing_manifest": str(resolve(args.existing_manifest).relative_to(PROJECT_ROOT)),
        "output": str(output.relative_to(PROJECT_ROOT)),
        "raw_count": int(len(raw)),
        "existing_count": int(len(existing)),
        "sample_count": int(len(selected)),
        "overlap_path_with_existing": overlap_paths,
        "identity_count": int(selected["identity_label"].nunique()),
        "min_images_per_identity_in_expansion": int(counts.min()),
        "median_images_per_identity_in_expansion": float(counts.median()),
        "max_images_per_identity_in_expansion": int(counts.max()),
        "missing_images": int(selected["image_exists"].ne("yes").sum()),
        "sampling_method": "non-overlap identity-balanced round-robin over CzechLynx raw manifest",
        "claim_boundary": "expansion_candidates_for_2x2_evidence_routing_with_known_ids",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = "PASS" if overlap_paths == 0 and audit["missing_images"] == 0 else "FAIL"
    print(
        f"{status} phase14 2x2 CzechLynx expansion manifest "
        f"rows={len(selected)} identities={selected['identity_label'].nunique()} "
        f"output={output.relative_to(PROJECT_ROOT)}"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
