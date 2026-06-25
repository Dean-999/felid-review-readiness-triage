#!/usr/bin/env python3
"""Build the Phase 14 unified 2x2 image evidence table.

This is the image-level substrate for the Phase 14 pair and risk-control
pipeline. It does not edit source labels or images. It standardizes the four
working-final 3000-image quadrants into one table with transparent provenance,
detector geometry, visual evidence components, and risk-control roles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_final_2x2_working_labels"
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_algorithm_inputs"
OUT_TABLE = OUT_DIR / "phase14_2x2_image_evidence_table.csv"
OUT_SUMMARY = OUT_DIR / "phase14_2x2_image_evidence_summary.csv"
OUT_AUDIT = OUT_DIR / "phase14_2x2_image_evidence_table_audit.json"

WORKING_FINAL_INPUTS = {
    "urban_bobcat_high_confidence": INPUT_DIR / "phase14_bobcat_high_confidence_3000_working_final_labels.csv",
    "wild_czechlynx_high_confidence": INPUT_DIR / "phase14_czechlynx_high_confidence_3000_working_final_labels.csv",
    "urban_bobcat_low_evidence_stress": INPUT_DIR / "phase14_bobcat_low_evidence_stress_3000_working_final_labels.csv",
    "wild_czechlynx_low_evidence_stress": INPUT_DIR / "phase14_czechlynx_low_evidence_stress_3000_working_final_labels.csv",
}

PATH_COLUMNS = [
    "candidate_source_path",
    "local_image_path",
    "review_image_path_local",
    "local_relative_path",
    "path",
]

OUTPUT_COLUMNS = [
    "phase14_image_evidence_id",
    "source_quadrant",
    "environment_axis",
    "species_axis",
    "evidence_axis",
    "source_dataset",
    "species_label",
    "scientific_name",
    "image_key",
    "image_path",
    "image_exists",
    "has_identity_label",
    "identity_label_available_for_validation",
    "identity_label_internal_present",
    "source_component",
    "human_label_status",
    "human_label_provenance",
    "human_review_bucket",
    "human_review_confidence",
    "strict_evidence_tier",
    "strict_evidence_role",
    "strict_training_eligible",
    "strict_stress_test_eligible",
    "manual_audit_needed",
    "label_prior_score",
    "md_detected",
    "md_best_confidence",
    "md_area_fraction",
    "md_width_fraction",
    "md_height_fraction",
    "md_aspect_ratio",
    "md_edge_touch",
    "detector_geometry_score",
    "pattern_visibility_raw",
    "side_flank_visibility_raw",
    "body_visibility_raw",
    "blur_level_raw",
    "occlusion_level_raw",
    "background_complexity_raw",
    "modified_background_raw",
    "pattern_evidence_score",
    "side_flank_evidence_score",
    "body_visibility_score",
    "blur_evidence_score",
    "occlusion_evidence_score",
    "background_simplicity_score",
    "visual_component_score",
    "auto_quality_score",
    "auto_evidence_score",
    "image_evidence_utility_score",
    "image_evidence_risk_score",
    "evidence_admissibility_band",
    "recommended_image_role",
    "risk_flags",
    "feature_available_flags",
    "phase14_final_label_version",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def stable_id(*parts: object, prefix: str = "p14img") -> str:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def first_existing_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in frame.columns:
            return column
    return None


def column_or_default(frame: pd.DataFrame, column: str, default: object = pd.NA) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([default] * len(frame), index=frame.index)


def text_series(frame: pd.DataFrame, column: str, default: str = "") -> pd.Series:
    return column_or_default(frame, column, default).fillna(default).astype(str).str.strip()


def numeric_series(frame: pd.DataFrame, column: str, default: float = np.nan) -> pd.Series:
    return pd.to_numeric(column_or_default(frame, column, default), errors="coerce")


def yes_no_series(frame: pd.DataFrame, column: str, default: str = "unknown") -> pd.Series:
    raw = text_series(frame, column, default).str.lower()
    return raw.map(
        {
            "true": "yes",
            "1": "yes",
            "yes": "yes",
            "y": "yes",
            "false": "no",
            "0": "no",
            "no": "no",
            "n": "no",
        }
    ).fillna(default)


def normalize_map(series: pd.Series, mapping: dict[str, float], default: float = np.nan) -> pd.Series:
    raw = series.fillna("").astype(str).str.strip().str.lower()
    return raw.map(mapping).fillna(default).astype(float)


def label_prior(bucket: pd.Series, confidence: pd.Series, evidence_axis: pd.Series) -> pd.Series:
    bucket_score = normalize_map(
        bucket,
        {
            "review_ready": 0.95,
            "review_limited": 0.55,
            "species_level_only": 0.18,
            "uncertain": 0.12,
        },
        default=np.nan,
    )
    confidence_delta = normalize_map(confidence, {"high": 0.04, "medium": 0.0, "low": -0.05}, default=0.0)
    fallback = np.where(evidence_axis.eq("high_confidence"), 0.90, 0.18)
    return pd.Series(bucket_score.fillna(pd.Series(fallback, index=bucket.index)) + confidence_delta, index=bucket.index).clip(0, 1)


def detector_score(frame: pd.DataFrame) -> pd.Series:
    conf = numeric_series(frame, "md_best_confidence", 0.0).fillna(0.0).clip(0, 1)
    area = numeric_series(frame, "md_area_fraction", 0.0).fillna(0.0).clip(0, 1)
    width = numeric_series(frame, "md_width_fraction", 0.0).fillna(0.0).clip(0, 1)
    height = numeric_series(frame, "md_height_fraction", 0.0).fillna(0.0).clip(0, 1)
    edge = yes_no_series(frame, "md_edge_touch", "unknown").eq("yes").astype(float)

    area_score = pd.cut(
        area,
        bins=[-0.001, 0.0, 0.015, 0.035, 0.060, 0.850, 1.000],
        labels=[0.0, 0.15, 0.35, 0.55, 1.0, 0.75],
    ).astype(float)
    shape_score = np.minimum(width / 0.18, 1.0) * 0.5 + np.minimum(height / 0.18, 1.0) * 0.5
    score = 0.45 * conf + 0.40 * area_score + 0.15 * shape_score - 0.18 * edge
    return pd.Series(score, index=frame.index).clip(0, 1)


def infer_environment(quadrant: pd.Series) -> pd.Series:
    q = quadrant.astype(str)
    return np.where(q.str.contains("urban|bobcat", case=False, regex=True), "urban_periurban", "wild")


def infer_species_axis(quadrant: pd.Series) -> pd.Series:
    q = quadrant.astype(str)
    return np.where(q.str.contains("bobcat", case=False, regex=True), "bobcat", "czechlynx")


def infer_evidence_axis(quadrant: pd.Series, tier: pd.Series) -> pd.Series:
    q = quadrant.astype(str)
    t = tier.astype(str)
    high = q.str.contains("high_confidence", case=False, regex=False) | t.str.contains("high_confidence", case=False)
    return np.where(high, "high_confidence", "low_evidence_stress")


def admissibility_band(score: float) -> str:
    if score >= 0.80:
        return "high_admissibility"
    if score >= 0.55:
        return "reviewable_admissibility"
    if score >= 0.30:
        return "low_admissibility"
    return "non_comparable_or_species_level"


def recommended_role(score: float, evidence_axis: str, training_eligible: str, stress_eligible: str) -> str:
    if training_eligible == "yes" and evidence_axis == "high_confidence" and score >= 0.70:
        return "core_training_or_clean_retrieval"
    if stress_eligible == "yes" and evidence_axis == "low_evidence_stress":
        return "low_evidence_stress_test"
    if score >= 0.55:
        return "manual_review_or_boundary_case"
    return "defer_or_species_level_only"


def risk_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if float(row["md_best_confidence"]) <= 0:
        flags.append("no_detector_box")
    if float(row["md_area_fraction"]) < 0.035:
        flags.append("small_animal")
    if row["md_edge_touch"] == "yes":
        flags.append("edge_touch")
    if float(row["side_flank_evidence_score"]) < 0.35:
        flags.append("weak_side_flank")
    if float(row["pattern_evidence_score"]) < 0.35:
        flags.append("weak_pattern")
    if float(row["body_visibility_score"]) < 0.35:
        flags.append("low_body_visibility")
    if float(row["blur_evidence_score"]) < 0.35:
        flags.append("blur_risk")
    if float(row["occlusion_evidence_score"]) < 0.35:
        flags.append("occlusion_risk")
    return ";".join(flags) if flags else "none"


def feature_flags(row: pd.Series) -> str:
    keys = [
        "md_best_confidence",
        "md_area_fraction",
        "pattern_visibility_raw",
        "side_flank_visibility_raw",
        "body_visibility_raw",
        "blur_level_raw",
        "occlusion_level_raw",
        "background_complexity_raw",
        "auto_quality_score",
        "auto_evidence_score",
    ]
    flags = {
        key: "yes" if pd.notna(row[key]) and str(row[key]).strip() not in {"", "nan", "<NA>"} else "no"
        for key in keys
    }
    return json.dumps(flags, sort_keys=True)


def image_path_series(frame: pd.DataFrame) -> pd.Series:
    path_col = first_existing_column(frame, PATH_COLUMNS)
    if path_col is None:
        return pd.Series([""] * len(frame), index=frame.index)
    paths = text_series(frame, path_col, "")
    resolved = []
    for value in paths:
        path = Path(value)
        resolved.append(str(path if path.is_absolute() else PROJECT_ROOT / path))
    return pd.Series(resolved, index=frame.index)


def build_one(quadrant_key: str, path: Path) -> pd.DataFrame:
    source = pd.read_csv(path, low_memory=False)
    source_quadrant = text_series(source, "phase14_2x2_quadrant", quadrant_key).replace("", quadrant_key)
    strict_tier = text_series(source, "strict_evidence_tier", "")
    evidence_axis = pd.Series(infer_evidence_axis(source_quadrant, strict_tier), index=source.index)
    image_path = image_path_series(source)
    image_key_col = first_existing_column(source, ["image_id", "expanded_image_id", "file_name", "phase14_md_candidate_id"])
    image_key = text_series(source, image_key_col, "") if image_key_col else image_path.map(lambda value: stable_id(value, prefix="imgkey"))

    pattern_raw = text_series(source, "human_pattern_visibility", "")
    side_raw = text_series(source, "human_side_flank_visibility", "")
    body_raw = text_series(source, "human_body_visibility", "")
    blur_raw = text_series(source, "human_blur_level", "")
    occlusion_raw = text_series(source, "human_occlusion_level", "")
    background_raw = text_series(source, "human_background_complexity", "")
    modified_raw = text_series(source, "human_modified_background", "")

    pattern_score = normalize_map(pattern_raw, {"high": 1.0, "medium": 0.67, "low": 0.33, "none": 0.0}, np.nan)
    side_score = normalize_map(
        side_raw,
        {"both": 1.0, "left": 1.0, "right": 1.0, "side": 1.0, "unknown": 0.35, "frontal": 0.20, "rear": 0.20, "none": 0.0},
        np.nan,
    )
    body_score = normalize_map(body_raw, {"76_100": 1.0, "51_75": 0.70, "26_50": 0.40, "0_25": 0.10, "unknown": 0.35}, np.nan)
    blur_score = normalize_map(blur_raw, {"none": 1.0, "mild": 0.72, "moderate": 0.35, "severe": 0.05, "unknown": 0.35}, np.nan)
    occlusion_score = normalize_map(occlusion_raw, {"none": 1.0, "partial": 0.55, "mild": 0.70, "moderate": 0.35, "major": 0.10, "severe": 0.05, "unknown": 0.35}, np.nan)
    background_score = normalize_map(background_raw, {"low": 1.0, "medium": 0.65, "high": 0.30, "unknown": 0.50}, np.nan)

    bucket = text_series(source, "human_review_bucket", "")
    confidence = text_series(source, "human_review_confidence", "")
    prior = label_prior(bucket, confidence, evidence_axis)
    detector = detector_score(source)

    # Use the strict evidence-axis only as a transparent fallback where component
    # labels are unavailable, not as hidden ground truth.
    high_fallback = evidence_axis.eq("high_confidence")
    pattern_fallback = pd.Series(np.where(high_fallback, 0.82, 0.18), index=source.index)
    side_fallback = pd.Series(np.where(high_fallback, 0.70, 0.25), index=source.index)
    body_fallback = pd.Series(np.where(high_fallback, 0.78, 0.22), index=source.index)
    blur_fallback = pd.Series(np.where(high_fallback, 0.78, 0.35), index=source.index)
    occlusion_fallback = pd.Series(np.where(high_fallback, 0.78, 0.30), index=source.index)
    pattern_score = pattern_score.fillna(pattern_fallback)
    side_score = side_score.fillna(side_fallback)
    body_score = body_score.fillna(body_fallback)
    blur_score = blur_score.fillna(blur_fallback)
    occlusion_score = occlusion_score.fillna(occlusion_fallback)
    background_score = background_score.fillna(0.50)

    visual = (
        0.25 * pattern_score
        + 0.25 * side_score
        + 0.18 * body_score
        + 0.14 * blur_score
        + 0.12 * occlusion_score
        + 0.06 * background_score
    ).clip(0, 1)
    auto_quality = numeric_series(source, "auto_quality_score", np.nan)
    auto_evidence = numeric_series(source, "auto_evidence_score", np.nan)
    auto_quality_filled = auto_quality.fillna(visual)
    auto_evidence_filled = auto_evidence.fillna(visual)
    utility = (
        0.36 * visual
        + 0.24 * detector
        + 0.22 * prior
        + 0.10 * auto_evidence_filled.clip(0, 1)
        + 0.08 * auto_quality_filled.clip(0, 1)
    ).clip(0, 1)

    md_conf = numeric_series(source, "md_best_confidence", 0.0).fillna(0.0)
    md_area = numeric_series(source, "md_area_fraction", 0.0).fillna(0.0)
    md_width = numeric_series(source, "md_width_fraction", 0.0).fillna(0.0)
    md_height = numeric_series(source, "md_height_fraction", 0.0).fillna(0.0)
    md_aspect = numeric_series(source, "md_aspect_ratio", np.nan)
    md_edge = yes_no_series(source, "md_edge_touch", "unknown")

    out = pd.DataFrame(index=source.index)
    out["phase14_image_evidence_id"] = [
        stable_id(quadrant_key, key, path, prefix="p14img") for key, path in zip(image_key.astype(str), image_path.astype(str))
    ]
    out["source_quadrant"] = source_quadrant
    out["environment_axis"] = infer_environment(source_quadrant)
    out["species_axis"] = infer_species_axis(source_quadrant)
    out["evidence_axis"] = evidence_axis
    out["source_dataset"] = text_series(source, "source_dataset", "")
    out["species_label"] = text_series(source, "species_label", "")
    out["scientific_name"] = text_series(source, "scientific_name", "")
    out["image_key"] = image_key
    out["image_path"] = image_path
    out["image_exists"] = image_path.map(lambda value: "yes" if Path(value).exists() else "no")
    identity = text_series(source, "identity_label", "")
    out["has_identity_label"] = np.where(identity.ne("") & identity.str.lower().ne("nan"), "yes", "no")
    out["identity_label_available_for_validation"] = np.where(out["species_axis"].eq("czechlynx") & out["has_identity_label"].eq("yes"), "yes", "no")
    out["identity_label_internal_present"] = out["has_identity_label"]
    out["source_component"] = text_series(source, "source_component", "")
    out["human_label_status"] = text_series(source, "human_label_status", "")
    out["human_label_provenance"] = text_series(source, "human_label_provenance", "")
    out["human_review_bucket"] = bucket
    out["human_review_confidence"] = confidence
    out["strict_evidence_tier"] = strict_tier
    out["strict_evidence_role"] = text_series(source, "strict_evidence_role", "")
    out["strict_training_eligible"] = yes_no_series(source, "strict_training_eligible", "unknown")
    out["strict_stress_test_eligible"] = yes_no_series(source, "strict_stress_test_eligible", "unknown")
    out["manual_audit_needed"] = yes_no_series(source, "manual_audit_needed", "unknown")
    out["label_prior_score"] = prior.round(6)
    out["md_detected"] = np.where(md_conf.gt(0) & md_area.gt(0), "yes", "no")
    out["md_best_confidence"] = md_conf.round(6)
    out["md_area_fraction"] = md_area.round(6)
    out["md_width_fraction"] = md_width.round(6)
    out["md_height_fraction"] = md_height.round(6)
    out["md_aspect_ratio"] = md_aspect.round(6)
    out["md_edge_touch"] = md_edge
    out["detector_geometry_score"] = detector.round(6)
    out["pattern_visibility_raw"] = pattern_raw
    out["side_flank_visibility_raw"] = side_raw
    out["body_visibility_raw"] = body_raw
    out["blur_level_raw"] = blur_raw
    out["occlusion_level_raw"] = occlusion_raw
    out["background_complexity_raw"] = background_raw
    out["modified_background_raw"] = modified_raw
    out["pattern_evidence_score"] = pattern_score.round(6)
    out["side_flank_evidence_score"] = side_score.round(6)
    out["body_visibility_score"] = body_score.round(6)
    out["blur_evidence_score"] = blur_score.round(6)
    out["occlusion_evidence_score"] = occlusion_score.round(6)
    out["background_simplicity_score"] = background_score.round(6)
    out["visual_component_score"] = visual.round(6)
    out["auto_quality_score"] = auto_quality.round(6)
    out["auto_evidence_score"] = auto_evidence.round(6)
    out["image_evidence_utility_score"] = utility.round(6)
    out["image_evidence_risk_score"] = (1.0 - utility).round(6)
    out["evidence_admissibility_band"] = utility.map(admissibility_band)
    out["recommended_image_role"] = [
        recommended_role(score, axis, train, stress)
        for score, axis, train, stress in zip(
            utility,
            evidence_axis,
            out["strict_training_eligible"],
            out["strict_stress_test_eligible"],
        )
    ]
    out["risk_flags"] = out.apply(risk_flags, axis=1)
    out["feature_available_flags"] = out.apply(feature_flags, axis=1)
    out["phase14_final_label_version"] = text_series(source, "phase14_final_label_version", "")
    return out[OUTPUT_COLUMNS]


def build_table(inputs: dict[str, Path]) -> pd.DataFrame:
    frames = []
    missing = [rel(path) for path in inputs.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing working-final input files: {missing}")
    for quadrant_key, path in inputs.items():
        frames.append(build_one(quadrant_key, path))
    table = pd.concat(frames, ignore_index=True)
    table.insert(0, "phase14_image_evidence_index", range(1, len(table) + 1))
    return table


def summarize(table: pd.DataFrame) -> pd.DataFrame:
    grouped = table.groupby(["environment_axis", "species_axis", "evidence_axis", "source_quadrant"], dropna=False)
    rows = []
    for keys, frame in grouped:
        rows.append(
            {
                "environment_axis": keys[0],
                "species_axis": keys[1],
                "evidence_axis": keys[2],
                "source_quadrant": keys[3],
                "row_count": int(len(frame)),
                "image_exists_yes": int(frame["image_exists"].eq("yes").sum()),
                "identity_validation_available_yes": int(frame["identity_label_available_for_validation"].eq("yes").sum()),
                "utility_mean": float(frame["image_evidence_utility_score"].mean()),
                "utility_median": float(frame["image_evidence_utility_score"].median()),
                "risk_mean": float(frame["image_evidence_risk_score"].mean()),
                "detector_geometry_mean": float(frame["detector_geometry_score"].mean()),
                "visual_component_mean": float(frame["visual_component_score"].mean()),
                "md_detected_yes": int(frame["md_detected"].eq("yes").sum()),
                "edge_touch_yes": int(frame["md_edge_touch"].eq("yes").sum()),
                "recommended_role_counts": json.dumps(
                    {str(k): int(v) for k, v in frame["recommended_image_role"].value_counts().sort_index().items()},
                    sort_keys=True,
                ),
                "admissibility_band_counts": json.dumps(
                    {str(k): int(v) for k, v in frame["evidence_admissibility_band"].value_counts().sort_index().items()},
                    sort_keys=True,
                ),
            }
        )
    return pd.DataFrame(rows)


def audit_payload(table: pd.DataFrame, summary: pd.DataFrame, inputs: dict[str, Path]) -> dict[str, Any]:
    duplicate_ids = int(table["phase14_image_evidence_id"].duplicated().sum())
    missing_images = int(table["image_exists"].ne("yes").sum())
    quadrant_counts = {str(k): int(v) for k, v in table["source_quadrant"].value_counts().sort_index().items()}
    overlap_checks = {}
    for species in ["bobcat", "czechlynx"]:
        high = set(table[(table["species_axis"].eq(species)) & (table["evidence_axis"].eq("high_confidence"))]["image_path"])
        low = set(table[(table["species_axis"].eq(species)) & (table["evidence_axis"].eq("low_evidence_stress"))]["image_path"])
        overlap_checks[f"{species}_high_low_path_overlap"] = len(high & low)
    return {
        "inputs": {key: rel(path) for key, path in inputs.items()},
        "outputs": {
            "table": rel(OUT_TABLE),
            "summary": rel(OUT_SUMMARY),
            "audit": rel(OUT_AUDIT),
        },
        "row_count": int(len(table)),
        "column_count": int(len(table.columns)),
        "quadrant_counts": quadrant_counts,
        "missing_images": missing_images,
        "duplicate_phase14_image_evidence_id": duplicate_ids,
        "overlap_checks": overlap_checks,
        "summary_rows": summary.to_dict(orient="records"),
        "scientific_boundary": {
            "bobcat_identity_validation": "not_available_without_verified_individual_ids",
            "czechlynx_identity_validation": "available_for_known_id_rows",
            "low_evidence_role": "stress_test_not_core_training",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT_TABLE)
    parser.add_argument("--summary", type=Path, default=OUT_SUMMARY)
    parser.add_argument("--audit", type=Path, default=OUT_AUDIT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    table = build_table(WORKING_FINAL_INPUTS)
    summary = summarize(table)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    summary.to_csv(args.summary, index=False)
    payload = audit_payload(table, summary, WORKING_FINAL_INPUTS)
    args.audit.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["row_count"] != 12000:
        raise SystemExit("Expected 12000 image evidence rows")
    if payload["missing_images"] != 0:
        raise SystemExit("Image evidence table contains missing image paths")
    if payload["duplicate_phase14_image_evidence_id"] != 0:
        raise SystemExit("Image evidence table contains duplicate evidence ids")
    if any(value != 0 for value in payload["overlap_checks"].values()):
        raise SystemExit("High/low image overlap detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
