#!/usr/bin/env python3
"""Prepare an identity-balanced 3000-image CzechLynx Phase 14 manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_MANIFEST = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_real_manifest.csv"
PHASE7A_IDS = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_phase7a_1000_internal_with_ids.csv"
OUT_DIR = PROJECT_ROOT / "data/interim/czechlynx/phase14"
DEFAULT_OUT = OUT_DIR / "czechlynx_phase14_3000_manifest.csv"
DEFAULT_AUDIT = OUT_DIR / "czechlynx_phase14_3000_manifest_audit.json"


def rel(path_text: str) -> str:
    path = Path(path_text)
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def normalized_existing_rows(phase7a: pd.DataFrame) -> pd.DataFrame:
    rows = phase7a.copy()
    rows["phase14_image_id"] = [f"czlx_phase14_{i:04d}" for i in range(len(rows))]
    rows["identity_label"] = rows["working_individual_id"]
    rows["phase14_source_role"] = "existing_phase7a_human_labeled"
    rows["phase14_label_status"] = "existing_human_label"
    rows["review_image_path_local"] = rows["review_image_path_local"].astype(str).map(rel)
    rows["local_image_path"] = rows["local_image_path"].astype(str).map(rel)
    return rows


def choose_new_rows(raw: pd.DataFrame, existing: pd.DataFrame, needed: int) -> pd.DataFrame:
    existing_paths = set(existing["path"].astype(str))
    existing_counts = existing["identity_label"].astype(str).value_counts().to_dict()
    candidates = raw[
        raw["image_exists"].eq(True)
        & raw["unique_name"].notna()
        & ~raw["path"].astype(str).isin(existing_paths)
    ].copy()
    candidates["identity_label"] = candidates["unique_name"].astype(str)
    candidates = candidates.sort_values(["identity_label", "date", "encounter", "path"]).reset_index(drop=True)

    selected_parts: list[pd.DataFrame] = []
    selected_paths: set[str] = set()
    current_counts = {str(k): int(v) for k, v in existing_counts.items()}

    # Fill identities in rounds to avoid domination by high-count individuals.
    max_cap = max(current_counts.values(), default=0)
    while sum(len(part) for part in selected_parts) < needed and max_cap < 80:
        max_cap += 1
        round_rows = []
        for identity, group in candidates.groupby("identity_label", sort=True):
            if current_counts.get(identity, 0) >= max_cap:
                continue
            available = group[~group["path"].astype(str).isin(selected_paths)]
            if available.empty:
                continue
            row = available.iloc[0]
            round_rows.append(row)
            selected_paths.add(str(row["path"]))
            current_counts[identity] = current_counts.get(identity, 0) + 1
            if sum(len(part) for part in selected_parts) + len(round_rows) >= needed:
                break
        if round_rows:
            selected_parts.append(pd.DataFrame(round_rows))
        else:
            break
    if not selected_parts:
        raise RuntimeError("no new CzechLynx rows selected")
    selected = pd.concat(selected_parts, ignore_index=True).head(needed).copy()
    selected["expanded_image_id"] = [f"czlx_phase14_new_{i:04d}" for i in range(len(selected))]
    selected["review_image_path_local"] = selected["local_image_path"].astype(str).map(rel)
    selected["local_image_path"] = selected["local_image_path"].astype(str).map(rel)
    selected["phase14_source_role"] = "new_phase14_machine_prefeature"
    selected["phase14_label_status"] = "ai_first_pass_needed"
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-manifest", default=str(RAW_MANIFEST))
    parser.add_argument("--phase7a-ids", default=str(PHASE7A_IDS))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--target", type=int, default=3000)
    args = parser.parse_args()

    raw = pd.read_csv(args.raw_manifest)
    phase7a = pd.read_csv(args.phase7a_ids)
    existing = normalized_existing_rows(phase7a)
    needed = args.target - len(existing)
    if needed < 0:
        raise ValueError("target must be at least existing Phase 7A row count")
    new_rows = choose_new_rows(raw, existing, needed)

    common_columns = [
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
    ]
    manifest = pd.concat(
        [existing[common_columns], new_rows[common_columns]],
        ignore_index=True,
    )
    manifest.insert(0, "phase14_review_index", range(1, len(manifest) + 1))
    manifest["source_dataset"] = "CzechLynx"
    manifest["context"] = "wild_known_id"
    manifest["species_label"] = "Eurasian lynx"
    manifest["scientific_name"] = "Lynx lynx"
    manifest["image_exists"] = [
        "yes" if (PROJECT_ROOT / str(path)).exists() else "no"
        for path in manifest["review_image_path_local"]
    ]

    output = Path(args.output)
    audit_path = Path(args.audit)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    if not audit_path.is_absolute():
        audit_path = PROJECT_ROOT / audit_path
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(output, index=False)

    counts = manifest["identity_label"].value_counts()
    audit: dict[str, Any] = {
        "output": str(output.relative_to(PROJECT_ROOT)),
        "row_count": int(len(manifest)),
        "existing_human_label_count": int(manifest["phase14_label_status"].eq("existing_human_label").sum()),
        "ai_first_pass_needed_count": int(manifest["phase14_label_status"].eq("ai_first_pass_needed").sum()),
        "unique_identity_count": int(manifest["identity_label"].nunique()),
        "identities_with_at_least_2_images": int((counts >= 2).sum()),
        "singleton_identity_count": int((counts == 1).sum()),
        "max_images_per_identity": int(counts.max()),
        "median_images_per_identity": float(counts.median()),
        "missing_review_images": int(manifest["image_exists"].ne("yes").sum()),
        "claim_boundary": "3000_image_manifest_extends_image_level_evidence_distribution_not_all_human_ground_truth",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 CzechLynx 3000 manifest "
        f"rows={len(manifest)} identities={audit['unique_identity_count']} output={output.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
