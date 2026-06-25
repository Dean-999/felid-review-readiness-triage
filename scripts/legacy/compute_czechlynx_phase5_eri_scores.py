#!/usr/bin/env python3
"""Compute Phase 5 ERI-ReID scores for CzechLynx pair evidence."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANNOTATION_CSV = (
    PROJECT_ROOT
    / "data"
    / "labels"
    / "czechlynx"
    / "czechlynx_mechanism_visual_factors_full_annotated_v1.csv"
)
PAIR_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "czechlynx"
    / "phase4"
    / "czechlynx_phase4c_pair_level_mechanism_similarity_table.csv"
)
OUTPUT_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "czechlynx"
    / "phase5"
    / "czechlynx_phase5_pair_eri_scores_internal.csv"
)

EXPECTED_ROWS = 3000
EXPECTED_SAME = 750
EXPECTED_DIFFERENT = 2250

REQUIRED_ANNOTATION_COLUMNS = {
    "expanded_image_id",
    "blur_level",
    "occlusion_level",
    "side_evidence_quality",
    "pattern_visibility",
    "body_fraction_visible",
    "uncertainty_flag",
    "annotation_status",
}

REQUIRED_PAIR_COLUMNS = [
    "pair_id",
    "pair_type",
    "image_a_expanded_id",
    "image_b_expanded_id",
    "pair_blur_max",
    "pair_occlusion_max",
    "pair_pattern_min",
    "pair_side_evidence_min",
    "pair_side_comparable",
    "pair_ir_artifact_max",
    "pair_body_fraction_min",
    "pair_any_frontal_rear",
    "pair_any_silhouette",
    "pair_any_uncertain",
    "pair_any_needs_review",
    "resnet50_similarity",
    "megadescriptor_similarity",
]

POSITIVE_EVIDENCE = {"high": 100.0, "medium": 65.0, "low": 30.0, "none": 0.0}
IMPAIRMENT = {
    "none": 100.0,
    "mild": 70.0,
    "moderate": 35.0,
    "severe": 0.0,
    "unknown": 50.0,
    "not_applicable": 100.0,
}
BODY_FRACTION = {
    "76_100": 100.0,
    "51_75": 70.0,
    "26_50": 35.0,
    "0_25": 0.0,
    "unknown": 50.0,
}
SIDE_COMPARABLE = {"yes": 100.0, "limited": 55.0, "unknown": 25.0, "no": 0.0}
BINARY_IMPAIRMENT = {"no": 100.0, "unknown": 50.0, "yes": 0.0}

HYBRID_WEIGHTS = {
    "primary": (0.55, 0.30, 0.15),
    "visual_heavy": (0.70, 0.20, 0.10),
    "balanced": (0.40, 0.40, 0.20),
    "model_heavy": (0.30, 0.55, 0.15),
    "agreement_heavy": (0.40, 0.25, 0.35),
}

SENSITIVE_COLUMN_PARTS = [
    "unique_name",
    "latitude",
    "longitude",
    "cell_code",
    "trap_id",
    "review_image_path",
]


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_csv_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in df.columns:
        df[column] = df[column].map(clean_cell)
    return df


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def require_columns(df: pd.DataFrame, required: set[str] | list[str], label: str) -> None:
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"{label} missing required column(s): {', '.join(missing)}")


def score_map(series: pd.Series, mapping: dict[str, float], column: str) -> pd.Series:
    values = series.str.lower()
    unexpected = sorted(set(values) - set(mapping))
    if unexpected:
        raise ValueError(f"{column} has unexpected value(s): {', '.join(unexpected)}")
    return values.map(mapping).astype(float)


def score_band(score: float) -> str:
    if score >= 75.0:
        return "high"
    if score >= 50.0:
        return "medium"
    if score >= 25.0:
        return "low"
    return "unusable"


def review_tier(band: str) -> str:
    return {
        "high": "high_confidence_candidate_review",
        "medium": "cautious_secondary_review",
        "low": "defer_unless_evidence_recovery_needed",
        "unusable": "exclude_from_individual_reid_review",
    }[band]


def percentile_rank(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="raise")
    return numeric.rank(method="average", pct=True) * 100.0


def main() -> int:
    try:
        if not ANNOTATION_CSV.exists():
            return fail(f"frozen annotation file not found: {ANNOTATION_CSV}")
        if not PAIR_CSV.exists():
            return fail(f"Phase 4C pair similarity file not found: {PAIR_CSV}")

        annotations = read_csv_clean(ANNOTATION_CSV)
        pairs = read_csv_clean(PAIR_CSV)

        require_columns(annotations, REQUIRED_ANNOTATION_COLUMNS, "annotation file")
        require_columns(pairs, REQUIRED_PAIR_COLUMNS, "Phase 4C pair table")

        sensitive_cols = [
            col
            for col in pairs.columns
            if any(part in col.lower() for part in SENSITIVE_COLUMN_PARTS)
        ]
        if sensitive_cols:
            return fail("Phase 4C pair table contains sensitive column(s): " + ", ".join(sensitive_cols))

        if len(annotations) != 500:
            return fail(f"annotation file has {len(annotations)} rows; expected 500")
        if len(pairs) != EXPECTED_ROWS:
            return fail(f"pair table has {len(pairs)} rows; expected {EXPECTED_ROWS}")
        same_count = int((pairs["pair_type"] == "same").sum())
        different_count = int((pairs["pair_type"] == "different").sum())
        if same_count != EXPECTED_SAME or different_count != EXPECTED_DIFFERENT:
            return fail(
                "unexpected pair_type counts: "
                f"same={same_count}, different={different_count}; "
                f"expected same={EXPECTED_SAME}, different={EXPECTED_DIFFERENT}"
            )

        output = pairs[REQUIRED_PAIR_COLUMNS].copy()
        output["resnet50_similarity"] = pd.to_numeric(output["resnet50_similarity"], errors="raise")
        output["megadescriptor_similarity"] = pd.to_numeric(
            output["megadescriptor_similarity"], errors="raise"
        )

        pattern_score = score_map(output["pair_pattern_min"], POSITIVE_EVIDENCE, "pair_pattern_min")
        side_quality_score = score_map(
            output["pair_side_evidence_min"], POSITIVE_EVIDENCE, "pair_side_evidence_min"
        )
        side_comparable_score = score_map(
            output["pair_side_comparable"], SIDE_COMPARABLE, "pair_side_comparable"
        )
        body_fraction_score = score_map(
            output["pair_body_fraction_min"], BODY_FRACTION, "pair_body_fraction_min"
        )
        blur_score = score_map(output["pair_blur_max"], IMPAIRMENT, "pair_blur_max")
        occlusion_score = score_map(
            output["pair_occlusion_max"], IMPAIRMENT, "pair_occlusion_max"
        )
        ir_score = score_map(output["pair_ir_artifact_max"], IMPAIRMENT, "pair_ir_artifact_max")
        frontal_score = score_map(
            output["pair_any_frontal_rear"], BINARY_IMPAIRMENT, "pair_any_frontal_rear"
        )
        silhouette_score = score_map(
            output["pair_any_silhouette"], BINARY_IMPAIRMENT, "pair_any_silhouette"
        )

        visual_only = (
            0.22 * pattern_score
            + 0.22 * side_quality_score
            + 0.16 * side_comparable_score
            + 0.12 * body_fraction_score
            + 0.10 * blur_score
            + 0.08 * occlusion_score
            + 0.05 * ir_score
            + 0.03 * frontal_score
            + 0.02 * silhouette_score
        )
        visual_only -= (output["pair_any_uncertain"].str.lower() == "yes").astype(float) * 10.0
        visual_only -= (output["pair_any_needs_review"].str.lower() == "yes").astype(float) * 10.0
        output["visual_only_eri"] = visual_only.clip(0.0, 100.0)

        output["megadescriptor_percentile"] = percentile_rank(output["megadescriptor_similarity"])
        output["resnet50_percentile"] = percentile_rank(output["resnet50_similarity"])
        output["model_support_score"] = (
            0.65 * output["megadescriptor_percentile"]
            + 0.35 * output["resnet50_percentile"]
        )
        output["cross_model_agreement"] = 100.0 - (
            output["megadescriptor_percentile"] - output["resnet50_percentile"]
        ).abs()

        for name, (visual_w, model_w, agreement_w) in HYBRID_WEIGHTS.items():
            col = "hybrid_eri" if name == "primary" else f"hybrid_eri_{name}"
            output[col] = (
                visual_w * output["visual_only_eri"]
                + model_w * output["model_support_score"]
                + agreement_w * output["cross_model_agreement"]
            ).clip(0.0, 100.0)

        output["visual_only_eri_band"] = output["visual_only_eri"].map(score_band)
        output["hybrid_eri_band"] = output["hybrid_eri"].map(score_band)
        output["visual_only_review_tier"] = output["visual_only_eri_band"].map(review_tier)
        output["hybrid_review_tier"] = output["hybrid_eri_band"].map(review_tier)

        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        output.to_csv(OUTPUT_CSV, index=False)

        print("CzechLynx Phase 5 ERI-ReID scoring")
        print(f"Input pair rows: {len(output)}")
        print(f"Same pairs: {same_count}")
        print(f"Different pairs: {different_count}")
        print(f"Output CSV: {OUTPUT_CSV}")
        print("Visual-only ERI bands:")
        for band, count in output["visual_only_eri_band"].value_counts().sort_index().items():
            print(f"  {band}: {count}")
        print("Hybrid ERI bands:")
        for band, count in output["hybrid_eri_band"].value_counts().sort_index().items():
            print(f"  {band}: {count}")
        print("RESULT: PASS")
        return 0
    except Exception as exc:  # noqa: BLE001 - emit concise audit-style failure.
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
