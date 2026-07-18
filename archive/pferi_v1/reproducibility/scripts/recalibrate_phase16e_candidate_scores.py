#!/usr/bin/env python3
"""Recalibrate Phase 16E candidate scores into quality-preserving tiers.

The Phase 16E runner's original `selection_eligible` gate is intentionally
treated as diagnostic only. This script replaces it with species-profile
percentile tiers while keeping hard validity requirements for image loading,
score availability, IQA availability, and side-view score availability.

This script does not freeze final 3000 and does not perform simple top-3000
selection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_candidate_model_filter/phase16e_candidate_model_filter_scores.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16e_recalibrated_candidate_scores"

SCORES_OUT = DEFAULT_OUTPUT_DIR / "phase16e_recalibrated_candidate_scores.csv"
AUDIT_OUT = DEFAULT_OUTPUT_DIR / "phase16e_recalibrated_candidate_scores_audit.json"
SUMMARY_OUT = DEFAULT_OUTPUT_DIR / "phase16e_recalibrated_candidate_scores_summary.md"

FINAL_SCORE = "final_candidate_score"
IQA_SCORE = "iqa_quality_proxy_score"
SIDE_SCORE = "clip_side_view_score"

TIER_COLUMNS = [
    "strict_recalibrated_eligible",
    "balanced_recalibrated_eligible",
    "broad_recalibrated_eligible",
    "recommended_recalibrated_eligible",
]

QUALITY_POLICY = "quality-preserving recalibration; not relaxed selection"
RECOMMENDED_TIER = "balanced"

SPECIES_PROFILES: dict[str, dict[str, Any]] = {
    "czechlynx": {
        "display_name": "CzechLynx",
        "allow_missing_side_score": False,
        "tiers": {
            "strict": {"final_percentile": 0.90, "iqa_percentile": 0.40},
            "balanced": {"final_percentile": 0.80, "iqa_percentile": 0.25},
            "broad": {"final_percentile": 0.75, "iqa_percentile": None},
        },
    },
    "bobcat": {
        "display_name": "Bobcat",
        "allow_missing_side_score": False,
        "tiers": {
            "strict": {"final_percentile": 0.75, "iqa_percentile": 0.40},
            "balanced": {"final_percentile": 0.60, "iqa_percentile": 0.25},
            "broad": {"final_percentile": 0.40, "iqa_percentile": None},
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build strict/balanced/broad Phase 16E recalibrated eligibility tiers."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def infer_species_profile(row: pd.Series) -> str:
    text = " ".join(
        str(row.get(column, ""))
        for column in ["target_quadrant", "species_label", "scientific_name", "candidate_id"]
    ).lower()
    if "bobcat" in text or "lynx rufus" in text:
        return "bobcat"
    if "czechlynx" in text or "czech" in text or "lynx lynx" in text:
        return "czechlynx"
    return "unknown"


def percentile_threshold(series: pd.Series, percentile: float | None) -> float | None:
    if percentile is None:
        return None
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    return float(numeric.quantile(percentile))


def threshold_pass(series: pd.Series, threshold: float | None) -> pd.Series:
    if threshold is None:
        return pd.Series(True, index=series.index)
    return pd.to_numeric(series, errors="coerce").ge(threshold).fillna(False)


def build_hard_validity(df: pd.DataFrame) -> tuple[pd.Series, dict[str, int]]:
    image_load = bool_series(df["image_load_success"]) if "image_load_success" in df.columns else pd.Series(False, index=df.index)
    if "scoring_valid_for_selection" in df.columns:
        scoring_valid = bool_series(df["scoring_valid_for_selection"])
    else:
        scoring_valid = pd.Series(True, index=df.index)

    final_present = pd.to_numeric(df.get(FINAL_SCORE), errors="coerce").notna()
    iqa_present = pd.to_numeric(df.get(IQA_SCORE), errors="coerce").notna()

    side_numeric = pd.to_numeric(df.get(SIDE_SCORE), errors="coerce")
    side_present = side_numeric.notna()
    allow_missing_side = df["species_profile"].map(
        lambda name: bool(SPECIES_PROFILES.get(str(name), {}).get("allow_missing_side_score", False))
    )

    hard_valid = image_load & scoring_valid & final_present & iqa_present & (side_present | allow_missing_side)
    diagnostics = {
        "image_load_success_true": int(image_load.sum()),
        "scoring_valid_for_selection_true": int(scoring_valid.sum()),
        "final_candidate_score_present": int(final_present.sum()),
        "iqa_quality_proxy_score_present": int(iqa_present.sum()),
        "clip_side_view_score_present_or_allowed_missing": int((side_present | allow_missing_side).sum()),
        "hard_recalibration_valid_count": int(hard_valid.sum()),
    }
    return hard_valid, diagnostics


def apply_profile_tiers(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    out = df.copy()
    out["species_profile"] = out.apply(infer_species_profile, axis=1)
    out["side_score_missing_allowed_by_species_profile"] = out["species_profile"].map(
        lambda name: bool(SPECIES_PROFILES.get(str(name), {}).get("allow_missing_side_score", False))
    )

    hard_valid, diagnostics = build_hard_validity(out)
    out["hard_recalibration_valid"] = hard_valid
    out["hard_recalibration_invalid_reason"] = ""
    out.loc[~hard_valid, "hard_recalibration_invalid_reason"] = "failed_hard_validity_requirements"

    for column in TIER_COLUMNS:
        out[column] = False

    thresholds_by_profile: dict[str, dict[str, Any]] = {}
    counts_by_profile: dict[str, dict[str, int]] = {}

    for profile_name, profile in SPECIES_PROFILES.items():
        profile_mask = out["species_profile"].eq(profile_name)
        valid_mask = profile_mask & out["hard_recalibration_valid"]
        valid = out.loc[valid_mask]

        thresholds_by_profile[profile_name] = {}
        counts_by_profile[profile_name] = {
            "rows": int(profile_mask.sum()),
            "hard_valid_rows": int(valid_mask.sum()),
        }

        for tier_name, rule in profile["tiers"].items():
            final_threshold = percentile_threshold(valid[FINAL_SCORE], rule["final_percentile"])
            iqa_threshold = percentile_threshold(valid[IQA_SCORE], rule["iqa_percentile"])
            thresholds_by_profile[profile_name][tier_name] = {
                "final_candidate_score_percentile": rule["final_percentile"],
                "final_candidate_score_threshold": final_threshold,
                "iqa_quality_proxy_score_percentile": rule["iqa_percentile"],
                "iqa_quality_proxy_score_threshold": iqa_threshold,
                "computed_on_hard_valid_rows": int(valid_mask.sum()),
                "allow_missing_side_score": bool(profile["allow_missing_side_score"]),
            }

            tier_column = f"{tier_name}_recalibrated_eligible"
            if valid.empty or final_threshold is None:
                out.loc[profile_mask, tier_column] = False
                counts_by_profile[profile_name][tier_column] = 0
                continue

            eligible = valid_mask & threshold_pass(out[FINAL_SCORE], final_threshold)
            if iqa_threshold is not None:
                eligible = eligible & threshold_pass(out[IQA_SCORE], iqa_threshold)
            out.loc[profile_mask, tier_column] = eligible.loc[profile_mask]
            counts_by_profile[profile_name][tier_column] = int(eligible.sum())

    known_profile = out["species_profile"].isin(SPECIES_PROFILES)
    out.loc[known_profile, "recommended_recalibrated_eligible"] = out.loc[
        known_profile, "balanced_recalibrated_eligible"
    ]
    out["recommended_recalibrated_tier"] = RECOMMENDED_TIER
    out["quality_policy"] = QUALITY_POLICY

    thresholds = {
        "strict_thresholds": {
            profile: values["strict"] for profile, values in thresholds_by_profile.items()
        },
        "balanced_thresholds": {
            profile: values["balanced"] for profile, values in thresholds_by_profile.items()
        },
        "broad_thresholds": {
            profile: values["broad"] for profile, values in thresholds_by_profile.items()
        },
    }
    audit = {
        "input_rows": int(len(out)),
        "species_profile_counts": {str(k): int(v) for k, v in out["species_profile"].value_counts(dropna=False).items()},
        **diagnostics,
        "strict_recalibrated_eligible_count": int(out["strict_recalibrated_eligible"].sum()),
        "balanced_recalibrated_eligible_count": int(out["balanced_recalibrated_eligible"].sum()),
        "broad_recalibrated_eligible_count": int(out["broad_recalibrated_eligible"].sum()),
        "recommended_recalibrated_eligible_count": int(out["recommended_recalibrated_eligible"].sum()),
        "counts_by_profile": counts_by_profile,
        **thresholds,
        "recommended_tier": RECOMMENDED_TIER,
        "quality_policy": QUALITY_POLICY,
        "selection_boundary": "recalibrated eligibility only; no final 3000 freeze and no simple top-3000",
    }
    return out, audit


def write_summary(audit: dict[str, Any], output_csv: Path, summary_md: Path) -> None:
    lines = [
        "# Phase 16E Recalibrated Candidate Score Tiers",
        "",
        "The recalibration replaces the overly conservative runner gate with percentile-based quality tiers.",
        "It does not lower the quality standard. The broad tier is a reserve pool only and must not be used directly as final 3000.",
        "",
        "Recommended default tier: `balanced_recalibrated_eligible`.",
        "",
        "Quality policy:",
        "",
        f"```text\n{QUALITY_POLICY}\n```",
        "",
        "## Counts",
        "",
        "| metric | count |",
        "| --- | ---: |",
        f"| input rows | {audit['input_rows']} |",
        f"| hard valid rows | {audit['hard_recalibration_valid_count']} |",
        f"| strict eligible | {audit['strict_recalibrated_eligible_count']} |",
        f"| balanced eligible | {audit['balanced_recalibrated_eligible_count']} |",
        f"| broad eligible | {audit['broad_recalibrated_eligible_count']} |",
        f"| recommended eligible | {audit['recommended_recalibrated_eligible_count']} |",
        "",
        "## Species Profiles",
        "",
        "| profile | rows | hard valid | strict | balanced | broad |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for profile, counts in audit["counts_by_profile"].items():
        lines.append(
            "| {profile} | {rows} | {hard} | {strict} | {balanced} | {broad} |".format(
                profile=profile,
                rows=counts.get("rows", 0),
                hard=counts.get("hard_valid_rows", 0),
                strict=counts.get("strict_recalibrated_eligible", 0),
                balanced=counts.get("balanced_recalibrated_eligible", 0),
                broad=counts.get("broad_recalibrated_eligible", 0),
            )
        )

    lines.extend(
        [
            "",
            "## Hard Validity Requirements",
            "",
            "- `image_load_success == true`.",
            "- `scoring_valid_for_selection == true` when that column exists.",
            "- `final_candidate_score` is present.",
            "- `iqa_quality_proxy_score` is present.",
            "- `clip_side_view_score` is present unless the species profile explicitly allows a missing side score.",
            "",
            "## Threshold Policy",
            "",
            "- CzechLynx strict: final score >= 90th percentile and IQA >= 40th percentile.",
            "- CzechLynx balanced: final score >= 80th percentile and IQA >= 25th percentile.",
            "- CzechLynx broad: final score >= 75th percentile after hard validity.",
            "- Bobcat strict: final score >= 75th percentile and IQA >= 40th percentile.",
            "- Bobcat balanced: final score >= 60th percentile and IQA >= 25th percentile.",
            "- Bobcat broad: final score >= 40th percentile after hard validity.",
            "",
            "## Output",
            "",
            f"```text\n{output_csv}\n```",
            "",
            "## Boundary",
            "",
            "These tiers are candidate-pool recalibration, not final selection. Final 3000 selection still requires constrained selection, laterality balance, duplicate controls, and manual audit calibration.",
        ]
    )
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = args.input
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / SCORES_OUT.name
    audit_json = output_dir / AUDIT_OUT.name
    summary_md = output_dir / SUMMARY_OUT.name

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input scores CSV not found: {input_path}. Pass --input path/to/phase16e_candidate_model_filter_scores.csv"
        )

    df = pd.read_csv(input_path, low_memory=False)
    required = ["image_load_success", FINAL_SCORE, IQA_SCORE]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required score columns: {missing}")
    if SIDE_SCORE not in df.columns:
        df[SIDE_SCORE] = pd.NA

    out, audit = apply_profile_tiers(df)
    audit["input_path"] = str(input_path)
    audit["output_csv"] = str(output_csv)
    audit["audit_json"] = str(audit_json)
    audit["summary_md"] = str(summary_md)

    out.to_csv(output_csv, index=False)
    audit_json.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    write_summary(audit, output_csv, summary_md)

    print(f"PASS phase16e recalibration rows={len(out)}")
    print(
        json.dumps(
            {
                "strict": audit["strict_recalibrated_eligible_count"],
                "balanced": audit["balanced_recalibrated_eligible_count"],
                "broad": audit["broad_recalibrated_eligible_count"],
                "recommended_tier": audit["recommended_tier"],
            },
            indent=2,
        )
    )
    print(f"WROTE {output_dir}")


if __name__ == "__main__":
    main()
