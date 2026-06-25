#!/usr/bin/env python3
"""Replace unreadable FCF bobcat sample rows from the full manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/manifests"
DEFAULT_FULL = MANIFEST_DIR / "fcf_bobcat_all_manifest.csv"
DEFAULT_SAMPLE = MANIFEST_DIR / "fcf_bobcat_3000_manifest.csv"
DEFAULT_PREFEATURES = PROJECT_ROOT / "data/external/felidae_conservation_fund/labels/fcf_bobcat_3000_auto_prefeatures.csv"
DEFAULT_AUDIT = MANIFEST_DIR / "fcf_bobcat_3000_manifest_repair_audit.json"


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def choose_replacement(full: pd.DataFrame, used: set[str], year: object, location_id: object) -> pd.Series:
    candidates = full[~full["image_id"].astype(str).isin(used)].copy()
    exact = candidates[(candidates["year"].astype(str) == str(year)) & (candidates["location_id"].astype(str) == str(location_id))]
    if len(exact):
        return exact.sort_values("image_id").iloc[0]
    same_year = candidates[candidates["year"].astype(str) == str(year)]
    if len(same_year):
        return same_year.sort_values(["location_id", "image_id"]).iloc[0]
    return candidates.sort_values(["year", "location_id", "image_id"]).iloc[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", default=str(DEFAULT_FULL))
    parser.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    parser.add_argument("--prefeatures", default=str(DEFAULT_PREFEATURES))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    args = parser.parse_args()

    full_path = PROJECT_ROOT / args.full if not Path(args.full).is_absolute() else Path(args.full)
    sample_path = PROJECT_ROOT / args.sample if not Path(args.sample).is_absolute() else Path(args.sample)
    prefeatures_path = PROJECT_ROOT / args.prefeatures if not Path(args.prefeatures).is_absolute() else Path(args.prefeatures)
    audit_path = PROJECT_ROOT / args.audit if not Path(args.audit).is_absolute() else Path(args.audit)

    full = pd.read_csv(full_path)
    sample = pd.read_csv(sample_path)
    prefeatures = pd.read_csv(prefeatures_path)
    failed = prefeatures[~prefeatures["auto_prefeature_status"].eq("ok")].copy()
    if failed.empty:
        print("PASS phase14 FCF bobcat manifest repair no_failed_rows=1")
        return 0

    used = set(sample["image_id"].astype(str))
    replacements = []
    repaired = sample.copy()
    for _, row in failed.sort_values("sample_index").iterrows():
        sample_index = int(row["sample_index"])
        replacement = choose_replacement(full, used, row["year"], row["location_id"]).copy()
        used.add(str(replacement["image_id"]))
        replacement_values = replacement.to_dict()
        replacement_values["sample_index"] = sample_index
        mask = repaired["sample_index"].eq(sample_index)
        if int(mask.sum()) != 1:
            raise ValueError(f"expected exactly one sample row for sample_index={sample_index}")
        for column in repaired.columns:
            repaired.loc[mask, column] = replacement_values.get(column, pd.NA)
        replacements.append(
            {
                "sample_index": sample_index,
                "old_image_id": row["image_id"],
                "new_image_id": replacement["image_id"],
                "old_year": str(row["year"]),
                "new_year": str(replacement["year"]),
                "old_location_id": str(row["location_id"]),
                "new_location_id": str(replacement["location_id"]),
            }
        )

    repaired = repaired.sort_values("sample_index")
    repaired.to_csv(sample_path, index=False)
    audit = {
        "sample_manifest": relative(sample_path),
        "prefeatures_source": relative(prefeatures_path),
        "replacement_count": len(replacements),
        "replacements": replacements,
        "claim_boundary": "manifest_repair_replaces_unreadable_images_without_changing_sample_size",
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS phase14 FCF bobcat manifest repair "
        f"replacements={len(replacements)} output={relative(sample_path)} audit={relative(audit_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
