#!/usr/bin/env python3
"""Build Phase 16E2 Bobcat 20k candidate-pool expansion.

This script expands the Bobcat high-confidence candidate *pool* for later
model filtering and constrained selection. It does not freeze final 3000, does
not simple top-3000, and does not modify Phase 16D inputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PHASE16E_MANIFEST = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_candidate_model_filter_colab_package/phase16e_candidate_model_filter_manifest.csv"
)
FCF_ALL_MANIFEST = (
    PROJECT_ROOT / "data/external/felidae_conservation_fund/manifests/fcf_bobcat_all_manifest.csv"
)
FCF_MD_PREFILTER = (
    PROJECT_ROOT
    / "data/external/felidae_conservation_fund/manifests/fcf_bobcat_md_prefilter_top2800_manifest.csv"
)
FCF_AUTO_PREFEATURES = [
    PROJECT_ROOT / "data/external/felidae_conservation_fund/labels/fcf_bobcat_3000_auto_prefeatures.csv",
    PROJECT_ROOT
    / "data/external/felidae_conservation_fund/labels/fcf_bobcat_phase14_2x2_expansion_6000_auto_prefeatures.csv",
]

OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16e2_bobcat_20k_candidate_pool"
MANIFEST_OUT = OUTPUT_DIR / "phase16e2_bobcat_20k_candidate_manifest.csv"
REGISTRY_OUT = OUTPUT_DIR / "phase16e2_bobcat_20k_source_registry.csv"
AUDIT_OUT = OUTPUT_DIR / "phase16e2_bobcat_20k_candidate_audit.json"
SUMMARY_OUT = OUTPUT_DIR / "phase16e2_bobcat_20k_candidate_summary.md"

PREFERRED_TARGET = 20_000
ACCEPTABLE_TARGET = 15_000
MINIMUM_TARGET = 12_000
EXPECTED_TIER1 = 6_412

TARGET_QUADRANT = "urban_bobcat_high_confidence"
SPECIES_LABEL = "bobcat"
SCIENTIFIC_NAME = "Lynx rufus"

SENSITIVE_COLUMNS = {
    "unique_name",
    "identity",
    "identity_label",
    "individual",
    "individual_id",
    "animal_id",
    "lynx_id",
    "latitude",
    "longitude",
    "trap_id",
    "location",
    "location_id",
    "cell_code",
    "camera",
    "camera_id",
}

OUTPUT_COLUMNS = [
    "candidate_id",
    "target_quadrant",
    "species_label",
    "scientific_name",
    "environment_axis",
    "source_dataset",
    "source_tier",
    "source_role",
    "source_mode",
    "image_uri",
    "prefilter_score",
    "md_confidence",
    "md_area_fraction",
    "md_width_fraction",
    "md_height_fraction",
    "md_aspect_ratio",
    "md_edge_touch",
    "bbox_x0",
    "bbox_y0",
    "bbox_x1",
    "bbox_y1",
    "duplicate_key",
    "original_source_key",
    "identity_label_available",
    "topup_reason",
]


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input missing: {path}")
    return pd.read_csv(path, low_memory=False)


def is_url(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    parsed = urlparse(str(value).strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_url(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def first_present(row: pd.Series, columns: list[str], default: object = "") -> object:
    for column in columns:
        if column in row and not pd.isna(row[column]) and str(row[column]).strip() != "":
            return row[column]
    return default


def make_empty_bbox_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in ["bbox_x0", "bbox_y0", "bbox_x1", "bbox_y1"]:
        if column not in df.columns:
            df[column] = pd.NA
    return df


def load_tier1() -> pd.DataFrame:
    df = read_csv_required(PHASE16E_MANIFEST)
    tier1 = df[
        (df["target_quadrant"].astype(str) == TARGET_QUADRANT)
        & (df["species_label"].astype(str).str.lower() == SPECIES_LABEL)
        & (df["source_mode"].astype(str) == "url")
        & (df["image_uri"].map(is_url))
    ].copy()
    tier1["source_tier"] = 1
    tier1["source_role"] = "fcf_high_geometry_primary"
    tier1["source_dataset"] = "Felidae Conservation Fund 2020-2025"
    tier1["environment_axis"] = "urban_periurban"
    tier1["duplicate_key"] = tier1["image_uri"].map(normalize_url)
    tier1["original_source_key"] = tier1.get("image_key", tier1["duplicate_key"])
    tier1["identity_label_available"] = False
    tier1["topup_reason"] = "phase16d_phase16e_fcf_high_geometry_retained"
    tier1 = tier1.rename(
        columns={
            "md_best_confidence": "md_confidence",
        }
    )
    tier1["bbox_x0"] = pd.NA
    tier1["bbox_y0"] = pd.NA
    tier1["bbox_x1"] = pd.NA
    tier1["bbox_y1"] = pd.NA
    tier1["image_uri"] = tier1["image_uri"].map(normalize_url)
    tier1["source_mode"] = "url"
    return tier1


def load_md_prefilter() -> pd.DataFrame:
    if not FCF_MD_PREFILTER.exists():
        return pd.DataFrame()
    md = pd.read_csv(FCF_MD_PREFILTER, low_memory=False)
    keep = [
        "image_id",
        "phase14_md_prefilter_score",
        "md_best_confidence",
        "md_area_fraction",
        "md_width_fraction",
        "md_height_fraction",
        "md_aspect_ratio",
        "md_edge_touch",
    ]
    keep = [column for column in keep if column in md.columns]
    md = md[keep].drop_duplicates(subset=["image_id"], keep="first")
    md = md.rename(
        columns={
            "phase14_md_prefilter_score": "prefilter_score_md",
            "md_best_confidence": "md_confidence_md",
            "md_area_fraction": "md_area_fraction_md",
            "md_width_fraction": "md_width_fraction_md",
            "md_height_fraction": "md_height_fraction_md",
            "md_aspect_ratio": "md_aspect_ratio_md",
            "md_edge_touch": "md_edge_touch_md",
        }
    )
    return md


def load_auto_prefeatures() -> pd.DataFrame:
    frames = []
    for path in FCF_AUTO_PREFEATURES:
        if not path.exists():
            continue
        df = pd.read_csv(path, low_memory=False)
        keep = [
            "image_id",
            "auto_quality_score",
            "auto_evidence_score",
            "auto_review_bucket",
            "auto_failure_flags",
        ]
        keep = [column for column in keep if column in df.columns]
        frames.append(df[keep])
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(
        by=[column for column in ["auto_evidence_score", "auto_quality_score"] if column in out.columns],
        ascending=False,
        na_position="last",
    )
    out = out.drop_duplicates(subset=["image_id"], keep="first")
    return out


def build_tier2(existing_urls: set[str], existing_keys: set[str], needed: int) -> pd.DataFrame:
    all_df = read_csv_required(FCF_ALL_MANIFEST)
    bobcat = all_df[
        (all_df["species_label"].astype(str).str.lower() == SPECIES_LABEL)
        & (all_df["download_url"].map(is_url))
    ].copy()
    bobcat["image_uri"] = bobcat["download_url"].map(normalize_url)
    bobcat["original_source_key"] = bobcat["image_id"].astype(str)
    bobcat["duplicate_key"] = bobcat["image_uri"]
    bobcat = bobcat[
        ~bobcat["image_uri"].isin(existing_urls)
        & ~bobcat["original_source_key"].isin(existing_keys)
    ].copy()

    md = load_md_prefilter()
    if not md.empty:
        bobcat = bobcat.merge(md, on="image_id", how="left")
    auto = load_auto_prefeatures()
    if not auto.empty:
        bobcat = bobcat.merge(auto, on="image_id", how="left")

    bobcat["prefilter_score"] = pd.to_numeric(
        bobcat.get("prefilter_score_md", pd.Series(index=bobcat.index, dtype=float)),
        errors="coerce",
    )
    bobcat["md_confidence"] = pd.to_numeric(
        bobcat.get("md_confidence_md", pd.Series(index=bobcat.index, dtype=float)),
        errors="coerce",
    )
    for src, dest in [
        ("md_area_fraction_md", "md_area_fraction"),
        ("md_width_fraction_md", "md_width_fraction"),
        ("md_height_fraction_md", "md_height_fraction"),
        ("md_aspect_ratio_md", "md_aspect_ratio"),
        ("md_edge_touch_md", "md_edge_touch"),
    ]:
        bobcat[dest] = bobcat[src] if src in bobcat.columns else pd.NA

    bobcat["auto_quality_score"] = pd.to_numeric(
        bobcat.get("auto_quality_score", pd.Series(index=bobcat.index, dtype=float)),
        errors="coerce",
    )
    bobcat["auto_evidence_score"] = pd.to_numeric(
        bobcat.get("auto_evidence_score", pd.Series(index=bobcat.index, dtype=float)),
        errors="coerce",
    )
    bobcat["has_md_score"] = bobcat["prefilter_score"].notna()
    bobcat["has_auto_evidence"] = bobcat["auto_evidence_score"].notna()
    bobcat["tier2_rank_score"] = (
        bobcat["prefilter_score"].fillna(0) * 100
        + bobcat["auto_evidence_score"].fillna(0) * 10
        + bobcat["auto_quality_score"].fillna(0)
    )
    bobcat = bobcat.sort_values(
        by=[
            "has_md_score",
            "has_auto_evidence",
            "tier2_rank_score",
            "year",
            "image_id",
        ],
        ascending=[False, False, False, False, True],
        na_position="last",
    )
    if needed > 0:
        bobcat = bobcat.head(needed).copy()
    else:
        bobcat = bobcat.head(0).copy()

    bobcat["target_quadrant"] = TARGET_QUADRANT
    bobcat["species_label"] = SPECIES_LABEL
    bobcat["scientific_name"] = SCIENTIFIC_NAME
    bobcat["environment_axis"] = "urban_periurban"
    bobcat["source_tier"] = 2
    bobcat["source_role"] = "fcf_next_best_topup"
    bobcat["source_mode"] = "url"
    bobcat["identity_label_available"] = False
    bobcat["topup_reason"] = (
        "same_dataset_fcf_species_level_bobcat_url_topup_for_model_filtering_margin"
    )
    bobcat = make_empty_bbox_columns(bobcat)
    return bobcat


def build_external_tier3_registry_note(current_total: int) -> dict:
    if current_total >= PREFERRED_TARGET:
        return {
            "tier3_used": False,
            "tier3_reason": "not_needed_fcf_tier1_plus_tier2_reached_preferred_target",
            "missing_dependency": "",
        }
    return {
        "tier3_used": False,
        "tier3_reason": (
            "not_available_locally; external LILA species-level bobcat source manifests "
            "would be required before Tier 3 can be used"
        ),
        "missing_dependency": (
            "No local Caltech Camera Traps / Snapshot / NACTI / other LILA bobcat "
            "species-level source manifest with image URLs was found under data/ or outputs/."
        ),
    }


def format_manifest(tier1: pd.DataFrame, tier2: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([tier1, tier2], ignore_index=True, sort=False)
    combined = combined.drop_duplicates(subset=["image_uri"], keep="first").copy()
    combined = combined.head(PREFERRED_TARGET).copy()
    combined["candidate_id"] = [
        f"p16e2_bobcat_{index:05d}" for index in range(1, len(combined) + 1)
    ]
    for column in OUTPUT_COLUMNS:
        if column not in combined.columns:
            combined[column] = pd.NA
    combined["target_quadrant"] = TARGET_QUADRANT
    combined["species_label"] = SPECIES_LABEL
    combined["scientific_name"] = SCIENTIFIC_NAME
    combined["source_mode"] = "url"
    combined["identity_label_available"] = combined["identity_label_available"].fillna(False).astype(bool)
    combined["image_uri"] = combined["image_uri"].map(normalize_url)
    combined["duplicate_key"] = combined["duplicate_key"].fillna(combined["image_uri"])
    return combined[OUTPUT_COLUMNS]


def build_registry(tier1: pd.DataFrame, tier2: pd.DataFrame, tier3_note: dict) -> pd.DataFrame:
    rows = [
        {
            "source_tier": 1,
            "source_role": "fcf_high_geometry_primary",
            "source_dataset": "Felidae Conservation Fund 2020-2025",
            "source_input_path": str(PHASE16E_MANIFEST.relative_to(PROJECT_ROOT)),
            "rows_contributed": int(len(tier1)),
            "identity_label_available": False,
            "topup_reason": "retain current Phase 16D/16E high-geometry Bobcat candidates",
            "used": True,
        },
        {
            "source_tier": 2,
            "source_role": "fcf_next_best_topup",
            "source_dataset": "Felidae Conservation Fund 2020-2025",
            "source_input_path": str(FCF_ALL_MANIFEST.relative_to(PROJECT_ROOT)),
            "rows_contributed": int(len(tier2)),
            "identity_label_available": False,
            "topup_reason": "same-source URL Bobcat expansion before model filtering",
            "used": bool(len(tier2) > 0),
        },
        {
            "source_tier": 3,
            "source_role": "external_species_level_bobcat_topup",
            "source_dataset": "Caltech/Snapshot/NACTI/other LILA bobcat species-level sources",
            "source_input_path": "",
            "rows_contributed": 0,
            "identity_label_available": False,
            "topup_reason": tier3_note["tier3_reason"],
            "used": bool(tier3_note["tier3_used"]),
        },
    ]
    return pd.DataFrame(rows)


def build_audit(manifest: pd.DataFrame, tier1: pd.DataFrame, tier2: pd.DataFrame, tier3_note: dict) -> dict:
    sensitive_leaks = sorted(SENSITIVE_COLUMNS.intersection(manifest.columns))
    tier_counts = {
        str(key): int(value)
        for key, value in manifest["source_tier"].value_counts(dropna=False).sort_index().items()
    }
    tier1_urls = set(tier1["image_uri"].map(normalize_url))
    output_tier1_urls = set(
        manifest.loc[manifest["source_tier"] == 1, "image_uri"].map(normalize_url)
    )
    target_status = (
        "preferred_target_reached"
        if len(manifest) >= PREFERRED_TARGET
        else "acceptable_target_reached"
        if len(manifest) >= ACCEPTABLE_TARGET
        else "minimum_target_reached"
        if len(manifest) >= MINIMUM_TARGET
        else "target_not_reached"
    )
    explanation = ""
    if len(manifest) < PREFERRED_TARGET:
        explanation = (
            "FCF Tier 1 + Tier 2 did not reach preferred 20k. Tier 3 requires a local "
            "external species-level Bobcat source manifest with URLs before use."
        )
    return {
        "phase": "16E2",
        "output_dir": str(OUTPUT_DIR),
        "manifest": str(MANIFEST_OUT),
        "source_registry": str(REGISTRY_OUT),
        "summary": str(SUMMARY_OUT),
        "total_candidates": int(len(manifest)),
        "preferred_target": PREFERRED_TARGET,
        "acceptable_target": ACCEPTABLE_TARGET,
        "minimum_target": MINIMUM_TARGET,
        "target_status": target_status,
        "target_explanation": explanation,
        "count_by_source_tier": tier_counts,
        "url_non_null_count": int(manifest["image_uri"].map(is_url).sum()),
        "duplicate_candidate_id_count": int(manifest["candidate_id"].duplicated().sum()),
        "duplicate_image_uri_count": int(manifest["image_uri"].duplicated().sum()),
        "overlap_with_tier1_count": int(len(output_tier1_urls.intersection(tier1_urls))),
        "tier1_expected_count": EXPECTED_TIER1,
        "tier1_input_count": int(len(tier1)),
        "tier1_all_retained": bool(len(output_tier1_urls.intersection(tier1_urls)) == len(tier1_urls)),
        "tier2_available_after_tier1_exclusion": int(len(tier2)),
        "tier2_md_confidence_non_null_count": int(
            pd.to_numeric(
                manifest.loc[manifest["source_tier"] == 2, "md_confidence"],
                errors="coerce",
            ).notna().sum()
        ),
        "tier2_prefilter_score_non_null_count": int(
            pd.to_numeric(
                manifest.loc[manifest["source_tier"] == 2, "prefilter_score"],
                errors="coerce",
            ).notna().sum()
        ),
        "tier2_detection_basis": (
            "FCF species annotation and public URL availability; MD geometry was not "
            "available for Tier 2 rows in local manifests, so Tier 2 must pass Phase "
            "16E model filtering before any high-confidence use."
        ),
        "source_dataset_distribution": {
            str(key): int(value)
            for key, value in manifest["source_dataset"].value_counts(dropna=False).sort_index().items()
        },
        "sensitive_columns_leaked": sensitive_leaks,
        "tier3": tier3_note,
        "expected_final_use": (
            "recalibrated candidate pool for model filtering, constrained selection, "
            "laterality/viewpoint calibration, duplicate control, and manual audit; not final 3000"
        ),
        "claim_boundary": (
            "No final 3000 freeze, no simple top-3000, no external species-level top-up "
            "silently treated as Re-ID clean data, Phase 16D candidate pool unchanged."
        ),
    }


def write_summary(manifest: pd.DataFrame, audit: dict) -> None:
    tier_table = manifest["source_tier"].value_counts().sort_index()
    dataset_table = manifest["source_dataset"].value_counts().sort_values(ascending=False)
    lines = [
        "# Phase 16E2 Bobcat 20k Candidate Pool",
        "",
        "## Purpose",
        "",
        "This output expands the urban Bobcat high-confidence candidate pool for later model filtering and constrained selection. It is not a final 3000 set.",
        "",
        "## Counts",
        "",
        f"- Total candidates: {audit['total_candidates']}",
        f"- Preferred target: {PREFERRED_TARGET}",
        f"- Acceptable target: {ACCEPTABLE_TARGET}+",
        f"- Minimum target: {MINIMUM_TARGET}",
        f"- Target status: {audit['target_status']}",
        f"- URL rows: {audit['url_non_null_count']}",
        f"- Tier 2 rows with MD confidence: {audit['tier2_md_confidence_non_null_count']}",
        f"- Tier 2 rows with prefilter score: {audit['tier2_prefilter_score_non_null_count']}",
        "",
        "## Tier Counts",
        "",
        "| source_tier | count |",
        "| ---: | ---: |",
    ]
    for key, value in tier_table.items():
        lines.append(f"| {key} | {int(value)} |")
    lines.extend(["", "## Source Dataset Distribution", "", "| source_dataset | count |", "| --- | ---: |"])
    for key, value in dataset_table.items():
        lines.append(f"| {key} | {int(value)} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Do not freeze final 3000 from this manifest.",
            "- Do not use simple top-3000.",
            "- Tier 2 rows are same-source FCF species-level Bobcat URL candidates for model filtering margin.",
            "- Tier 2 does not have local MD geometry in this manifest; it must pass Phase 16E IQA/OpenCLIP/optional pose filtering before any high-confidence use.",
            "- External Tier 3 was not used because FCF Tier 1 + Tier 2 reached the preferred target.",
            "- Identity labels are not available for these Bobcat rows unless separately verified.",
            "",
        ]
    )
    SUMMARY_OUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tier1 = load_tier1()
    if len(tier1) != EXPECTED_TIER1:
        raise ValueError(f"Unexpected Tier 1 count: {len(tier1)} != {EXPECTED_TIER1}")

    tier1_urls = set(tier1["image_uri"].map(normalize_url))
    tier1_keys = set(tier1["original_source_key"].astype(str))
    needed = PREFERRED_TARGET - len(tier1)
    tier2 = build_tier2(tier1_urls, tier1_keys, needed)
    tier3_note = build_external_tier3_registry_note(len(tier1) + len(tier2))
    manifest = format_manifest(tier1, tier2)
    registry = build_registry(tier1, tier2, tier3_note)
    audit = build_audit(manifest, tier1, tier2, tier3_note)

    if audit["sensitive_columns_leaked"]:
        raise ValueError(f"Sensitive columns leaked: {audit['sensitive_columns_leaked']}")
    if audit["duplicate_candidate_id_count"] != 0:
        raise ValueError("Duplicate candidate_id detected")
    if audit["duplicate_image_uri_count"] != 0:
        raise ValueError("Duplicate image_uri detected")
    if audit["url_non_null_count"] != audit["total_candidates"]:
        raise ValueError("Some output rows do not have valid URLs")
    if audit["total_candidates"] < MINIMUM_TARGET:
        raise ValueError(f"Candidate pool below minimum target: {audit['total_candidates']}")

    manifest.to_csv(MANIFEST_OUT, index=False)
    registry.to_csv(REGISTRY_OUT, index=False)
    AUDIT_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    write_summary(manifest, audit)

    print(f"PASS phase16e2 Bobcat candidate pool rows={len(manifest)}")
    print(json.dumps(audit["count_by_source_tier"], indent=2))
    print(f"WROTE {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
