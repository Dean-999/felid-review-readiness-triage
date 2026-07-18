#!/usr/bin/env python3
"""Build a large same-domain high-confidence candidate pool for Phase 16.

The output is metadata-first: it avoids copying or downloading images locally.
Bobcat candidates come from FCF rows already passing LILA MegaDetector geometry
prefiltering. CzechLynx candidates come from the local real-image manifest and
should be detector/quality/viewpoint rescored on cloud before final selection.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/expanded_high_confidence_candidate_pool"
SOURCE_REGISTRY_CSV = OUTPUT_DIR / "phase16_high_confidence_source_registry.csv"
CANDIDATE_MANIFEST_CSV = OUTPUT_DIR / "phase16_expanded_high_confidence_candidate_manifest.csv"
README = OUTPUT_DIR / "README.md"
AUDIT_JSON = OUTPUT_DIR / "phase16_expanded_high_confidence_candidate_pool_audit.json"

FCF_MD_HIGH = PROJECT_ROOT / "outputs/phase14/phase14_lila_md_prefilter/fcf_bobcat_md_high_prefilter_all_passed.csv"
CZECH_REAL = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_real_manifest.csv"
BOBCAT_CURRENT_HIGH = PROJECT_ROOT / "outputs/phase14/phase14_final_2x2_working_labels/phase14_bobcat_high_confidence_3000_working_final_labels.csv"
CZECH_CURRENT_HIGH = PROJECT_ROOT / "outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_high_confidence_3000_working_final_labels.csv"


def _read_current_bobcat_ids() -> set[str]:
    if not BOBCAT_CURRENT_HIGH.exists():
        return set()
    df = pd.read_csv(BOBCAT_CURRENT_HIGH, usecols=lambda col: col in {"image_id", "file_name"})
    values = set()
    for column in ["image_id", "file_name"]:
        if column in df.columns:
            values.update(df[column].dropna().astype(str))
    return values


def _read_current_czech_paths() -> set[str]:
    if not CZECH_CURRENT_HIGH.exists():
        return set()
    df = pd.read_csv(CZECH_CURRENT_HIGH, usecols=lambda col: col in {"path", "local_image_path", "candidate_source_path"})
    values = set()
    for column in ["path", "local_image_path", "candidate_source_path"]:
        if column in df.columns:
            values.update(df[column].dropna().astype(str))
    return values


def build_source_registry() -> pd.DataFrame:
    rows = [
        {
            "source_name": "fcf_bobcat_lila_md_high",
            "species_label": "bobcat",
            "scientific_name": "Lynx rufus",
            "environment_axis": "urban_periurban",
            "target_quadrant": "urban_bobcat_high_confidence",
            "source_role": "final_candidate_same_domain",
            "priority": 1,
            "use_in_final_3000": "yes_after_quality_viewpoint_manual_gate",
            "quality_rationale": "same species; LILA MegaDetector high-geometry prefilter already applied",
            "risk_notes": "individual IDs unavailable; final claims cannot use true bobcat identity accuracy",
            "source_url": "https://lila.science/datasets/felidae-conservation-fund/",
        },
        {
            "source_name": "czechlynx_real_all",
            "species_label": "Eurasian lynx",
            "scientific_name": "Lynx lynx",
            "environment_axis": "wild",
            "target_quadrant": "wild_czechlynx_high_confidence",
            "source_role": "final_candidate_same_domain",
            "priority": 1,
            "use_in_final_3000": "yes_after_quality_viewpoint_manual_gate",
            "quality_rationale": "same target species; local real-image pool with known-ID validation available internally",
            "risk_notes": "do not export sensitive location or identity fields in public/cloud manifests",
            "source_url": "https://wildlifedatasets.github.io/wildlife-datasets/datasets/",
        },
        {
            "source_name": "animalclef_czechlynx_or_related_lynx",
            "species_label": "lynx",
            "scientific_name": "Lynx spp.",
            "environment_axis": "benchmark",
            "target_quadrant": "none",
            "source_role": "selector_calibration_or_benchmark",
            "priority": 2,
            "use_in_final_3000": "no_unless_proven_same_domain_and_nonduplicate",
            "quality_rationale": "curated challenge data can support benchmark or selector calibration",
            "risk_notes": "must check overlap/provenance before any target-domain use",
            "source_url": "https://www.imageclef.org/",
        },
        {
            "source_name": "atrw_leopardid_hyenaid_wildlifereid10k",
            "species_label": "external animal Re-ID",
            "scientific_name": "multiple",
            "environment_axis": "external_support",
            "target_quadrant": "none",
            "source_role": "quality_viewpoint_selector_training",
            "priority": 3,
            "use_in_final_3000": "no",
            "quality_rationale": "cleaned Re-ID datasets can train viewpoint/flank/quality selectors",
            "risk_notes": "do not mix into wild-vs-urban target comparison",
            "source_url": "https://wildlifedatasets.github.io/wildlife-datasets/datasets/",
        },
    ]
    return pd.DataFrame(rows)


def build_bobcat_candidates() -> pd.DataFrame:
    current_ids = _read_current_bobcat_ids()
    df = pd.read_csv(FCF_MD_HIGH, low_memory=False)
    df = df.drop_duplicates("image_id").copy()
    out = pd.DataFrame(
        {
            "source_name": "fcf_bobcat_lila_md_high",
            "target_quadrant": "urban_bobcat_high_confidence",
            "species_label": "bobcat",
            "scientific_name": "Lynx rufus",
            "environment_axis": "urban_periurban",
            "candidate_role": "expanded_high_candidate",
            "source_priority": 1,
            "image_key": df["image_id"].astype(str),
            "phase16_image_uri": df["download_url"].fillna(df.get("azure_url", "")),
            "download_url": df.get("download_url", ""),
            "azure_url": df.get("azure_url", ""),
            "local_image_path": "",
            "local_exists": False,
            "license": "",
            "dataset_page": "https://lila.science/datasets/felidae-conservation-fund/",
            "has_detector_geometry": True,
            "needs_detector_or_pose": False,
            "md_best_confidence": pd.to_numeric(df.get("md_best_confidence"), errors="coerce"),
            "md_area_fraction": pd.to_numeric(df.get("md_area_fraction"), errors="coerce"),
            "md_width_fraction": pd.to_numeric(df.get("md_width_fraction"), errors="coerce"),
            "md_height_fraction": pd.to_numeric(df.get("md_height_fraction"), errors="coerce"),
            "md_aspect_ratio": pd.to_numeric(df.get("md_aspect_ratio"), errors="coerce"),
            "md_edge_touch": df.get("md_edge_touch", ""),
            "prefilter_score": pd.to_numeric(df.get("phase14_md_prefilter_score"), errors="coerce"),
        }
    )
    out["already_in_current_high_final"] = out["image_key"].isin(current_ids)
    out["cloud_action"] = "download_url_then_iqa_viewpoint_rescore"
    return out


def build_czech_candidates() -> pd.DataFrame:
    current_paths = _read_current_czech_paths()
    df = pd.read_csv(CZECH_REAL, low_memory=False)
    df = df[df["image_exists"].astype(bool)].drop_duplicates("path").copy()
    local_paths = df["local_image_path"].astype(str)
    public_safe_key = df["path"].astype(str)
    out = pd.DataFrame(
        {
            "source_name": "czechlynx_real_all",
            "target_quadrant": "wild_czechlynx_high_confidence",
            "species_label": "Eurasian lynx",
            "scientific_name": "Lynx lynx",
            "environment_axis": "wild",
            "candidate_role": "expanded_high_candidate",
            "source_priority": 1,
            "image_key": public_safe_key,
            "phase16_image_uri": local_paths,
            "download_url": "",
            "azure_url": "",
            "local_image_path": local_paths,
            "local_exists": True,
            "license": "CzechLynx local research dataset",
            "dataset_page": "https://wildlifedatasets.github.io/wildlife-datasets/datasets/",
            "has_detector_geometry": False,
            "needs_detector_or_pose": True,
            "md_best_confidence": pd.NA,
            "md_area_fraction": pd.NA,
            "md_width_fraction": pd.NA,
            "md_height_fraction": pd.NA,
            "md_aspect_ratio": pd.NA,
            "md_edge_touch": "",
            "prefilter_score": pd.NA,
        }
    )
    out["already_in_current_high_final"] = (
        out["image_key"].isin(current_paths) | out["local_image_path"].isin(current_paths)
    )
    out["cloud_action"] = "read_local_or_uploaded_file_then_detector_iqa_viewpoint_rescore"
    return out


def write_readme(manifest: pd.DataFrame, registry: pd.DataFrame) -> None:
    counts = manifest.groupby(["target_quadrant", "source_name"]).size().to_dict()
    README.write_text(
        f"""# Phase 16 Expanded High-Confidence Candidate Pool

Purpose: provide a large, quality-first candidate pool before selecting the
final 3000 high-confidence images per target quadrant.

Rows: {len(manifest)}

Counts:

```json
{json.dumps({str(k): int(v) for k, v in counts.items()}, indent=2)}
```

Files:

```text
phase16_high_confidence_source_registry.csv
phase16_expanded_high_confidence_candidate_manifest.csv
phase16_expanded_high_confidence_candidate_pool_audit.json
```

Selection rule:

```text
Do not select final high-confidence images from raw candidate counts. First run
detector/pose if needed, no-reference IQA on animal crop, viewpoint/laterality
classification, PF-ERI evidence gating, and manual audit. Final target remains
3000 per high-confidence quadrant if enough high-quality images pass.
```

Source boundary:

```text
FCF and CzechLynx are same-domain final candidate sources. External curated
animal Re-ID datasets are selector-training and benchmark-support sources only
unless provenance and domain compatibility are explicitly justified.
```
""",
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    registry = build_source_registry()
    manifest = pd.concat(
        [
            build_bobcat_candidates().dropna(axis=1, how="all"),
            build_czech_candidates().dropna(axis=1, how="all"),
        ],
        ignore_index=True,
        sort=False,
    )
    manifest = manifest.drop_duplicates(["source_name", "image_key"]).reset_index(drop=True)
    manifest.insert(0, "phase16_expanded_candidate_index", range(1, len(manifest) + 1))
    registry.to_csv(SOURCE_REGISTRY_CSV, index=False)
    manifest.to_csv(CANDIDATE_MANIFEST_CSV, index=False)
    write_readme(manifest, registry)
    audit = {
        "source_registry": str(SOURCE_REGISTRY_CSV),
        "candidate_manifest": str(CANDIDATE_MANIFEST_CSV),
        "rows": int(len(manifest)),
        "source_counts": {
            str(key): int(value)
            for key, value in manifest["source_name"].value_counts().sort_index().items()
        },
        "target_counts": {
            str(key): int(value)
            for key, value in manifest["target_quadrant"].value_counts().sort_index().items()
        },
        "same_domain_final_candidate_sources": [
            "fcf_bobcat_lila_md_high",
            "czechlynx_real_all",
        ],
        "claim_boundary": (
            "candidate pool only; final high-confidence images require returned "
            "quality/viewpoint scores and manual calibration"
        ),
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"PASS phase16 expanded high-confidence candidate pool rows={len(manifest)}")
    print(f"WROTE {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
