#!/usr/bin/env python3
"""Compute a visual-only PF-ERI pair gate for Phase 7A eligible pairs."""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "outputs/czechlynx/phase7a/pair_tables/phase7a_1000_image_pair_table_v1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a/visual_only_pf_eri"
SCORES_CSV = OUTPUT_DIR / "phase7a_visual_only_pf_eri_pair_scores.csv"
SUMMARY_CSV = OUTPUT_DIR / "phase7a_visual_only_pf_eri_summary.csv"
DRIVER_CSV = OUTPUT_DIR / "phase7a_visual_only_pf_eri_factor_driver_summary.csv"
RISK_BINS_CSV = OUTPUT_DIR / "phase7a_visual_only_pf_eri_risk_bins.csv"
FIGURE_DIR = OUTPUT_DIR / "figures"

REQUIRED_COLUMNS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "source_phase_a",
    "source_phase_b",
    "pair_source_phase_type",
    "same_identity",
    "pair_label_available",
    "pair_modeling_eligible",
    "pair_exclusion_reason",
    "resnet50_similarity",
    "megadescriptor_similarity",
    "descriptor_available",
    "pattern_visibility_a",
    "pattern_visibility_b",
    "side_evidence_quality_a",
    "side_evidence_quality_b",
    "body_fraction_visible_a",
    "body_fraction_visible_b",
    "blur_level_a",
    "blur_level_b",
    "occlusion_level_a",
    "occlusion_level_b",
    "contrast_level_a",
    "contrast_level_b",
    "frontal_or_rear_view_a",
    "frontal_or_rear_view_b",
    "silhouette_only_a",
    "silhouette_only_b",
    "partial_body_a",
    "partial_body_b",
    "uncertainty_flag_a",
    "uncertainty_flag_b",
    "pair_side_compatible",
    "pair_has_frontal_or_rear",
    "pair_has_partial_body",
    "pair_has_night_ir_artifact",
    "pair_primary_limiting_factor_combined",
]

PATTERN = {"none": 0.0, "low": 1.0, "medium": 2.0, "high": 3.0}
SIDE_QUALITY = {"none": 0.0, "low": 1.0, "medium": 2.0, "high": 3.0}
BODY = {"0_25": 0.0, "26_50": 1.0, "51_75": 2.0, "76_100": 3.0}
BLUR = {"severe": 0.0, "moderate": 1.0, "mild": 2.0, "none": 3.0}
OCCLUSION = {"major": 0.0, "partial": 1.5, "none": 3.0}
CONTRAST = {"low": 0.0, "not_available": 1.0, "good": 2.0}
SIDE_COMPATIBILITY = {"no": 0.0, "unknown": 0.35, "yes": 1.0}

SCORE_COLUMNS = [
    "pattern_score_a",
    "pattern_score_b",
    "side_quality_score_a",
    "side_quality_score_b",
    "body_fraction_score_a",
    "body_fraction_score_b",
    "blur_score_a",
    "blur_score_b",
    "occlusion_score_a",
    "occlusion_score_b",
    "contrast_score_a",
    "contrast_score_b",
    "pair_pattern_min_score",
    "pair_side_quality_min_score",
    "pair_body_fraction_min_score",
    "pair_blur_min_score",
    "pair_occlusion_min_score",
    "pair_contrast_min_score",
    "pair_side_compatibility_score",
    "frontal_rear_penalty",
    "silhouette_penalty",
    "partial_body_penalty",
    "uncertainty_penalty",
    "night_ir_penalty",
    "visual_pf_eri_min_rule",
    "visual_pf_eri_weighted",
    "visual_pf_eri_band",
    "primary_limiting_factor_for_score",
]

PAIR_SCORE_FIELDS = [
    "pair_id",
    "image_id_a",
    "image_id_b",
    "same_identity",
    "source_phase_a",
    "source_phase_b",
    "pair_source_phase_type",
    "pair_modeling_eligible",
    "pair_exclusion_reason",
    "pair_side_compatible",
    "pair_primary_limiting_factor_combined",
    *SCORE_COLUMNS,
    "resnet50_similarity_reference_only",
    "megadescriptor_similarity_reference_only",
    "descriptor_reference_note",
]


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clean(value: object) -> str:
    return str(value).strip().lower()


def score_value(row: dict[str, str], field: str, suffix: str, mapping: dict[str, float]) -> float:
    value = clean(row[f"{field}_{suffix}"])
    if value not in mapping:
        raise ValueError(f"{field}_{suffix} has unsupported value: {value}")
    return mapping[value]


def pair_min(row: dict[str, str], field: str, mapping: dict[str, float]) -> tuple[float, float, float]:
    a = score_value(row, field, "a", mapping)
    b = score_value(row, field, "b", mapping)
    return a, b, min(a, b)


def yes_no(value: str) -> str:
    value = clean(value)
    if value in {"yes", "no", "unknown"}:
        return value
    raise ValueError(f"unsupported yes/no value: {value}")


def band(score: float) -> str:
    if score >= 75.0:
        return "high"
    if score >= 50.0:
        return "medium"
    if score >= 25.0:
        return "low"
    return "unusable"


def interpretation_for_band(score_band: str) -> str:
    return {
        "high": "high visual reviewability; descriptor support can be considered in a later staged slice",
        "medium": "usable but limited visual reviewability; should remain cautious",
        "low": "weak visual reviewability; likely defer unless evidence is otherwise important",
        "unusable": "insufficient visual evidence for individual-level review",
    }[score_band]


def limiting_factor(components: dict[str, float]) -> str:
    normalized = {
        "pattern_visibility": components["pair_pattern_min_score"] / 3.0,
        "side_evidence_quality": components["pair_side_quality_min_score"] / 3.0,
        "body_fraction_visible": components["pair_body_fraction_min_score"] / 3.0,
        "blur_level": components["pair_blur_min_score"] / 3.0,
        "occlusion_level": components["pair_occlusion_min_score"] / 3.0,
        "contrast_level": components["pair_contrast_min_score"] / 2.0,
        "side_compatibility": components["pair_side_compatibility_score"],
    }
    penalty_values = {
        "frontal_or_rear_view": components["frontal_rear_penalty"] / 8.0,
        "silhouette_only": components["silhouette_penalty"] / 12.0,
        "partial_body": components["partial_body_penalty"] / 6.0,
        "uncertainty_flag": components["uncertainty_penalty"] / 5.0,
        "night_ir_artifact": components["night_ir_penalty"] / 4.0,
    }
    largest_penalty = max(penalty_values.items(), key=lambda item: item[1])
    lowest_component = min(normalized.items(), key=lambda item: item[1])
    if largest_penalty[1] >= 0.9 and lowest_component[1] > 0.35:
        return largest_penalty[0]
    return lowest_component[0]


def compute_scores(row: dict[str, str]) -> dict[str, object]:
    pattern_a, pattern_b, pair_pattern = pair_min(row, "pattern_visibility", PATTERN)
    side_a, side_b, pair_side = pair_min(row, "side_evidence_quality", SIDE_QUALITY)
    body_a, body_b, pair_body = pair_min(row, "body_fraction_visible", BODY)
    blur_a, blur_b, pair_blur = pair_min(row, "blur_level", BLUR)
    occ_a, occ_b, pair_occ = pair_min(row, "occlusion_level", OCCLUSION)
    contrast_a, contrast_b, pair_contrast = pair_min(row, "contrast_level", CONTRAST)

    side_compatible = clean(row["pair_side_compatible"])
    if side_compatible not in SIDE_COMPATIBILITY:
        raise ValueError(f"pair_side_compatible has unsupported value: {side_compatible}")
    side_compatibility_score = SIDE_COMPATIBILITY[side_compatible]

    frontal_values = {yes_no(row["frontal_or_rear_view_a"]), yes_no(row["frontal_or_rear_view_b"])}
    silhouette_values = {yes_no(row["silhouette_only_a"]), yes_no(row["silhouette_only_b"])}
    partial_values = {yes_no(row["partial_body_a"]), yes_no(row["partial_body_b"])}
    uncertainty_values = {yes_no(row["uncertainty_flag_a"]), yes_no(row["uncertainty_flag_b"])}

    frontal_penalty = 8.0 if "yes" in frontal_values else 3.0 if "unknown" in frontal_values else 0.0
    silhouette_penalty = 12.0 if "yes" in silhouette_values else 0.0
    partial_penalty = 6.0 if "yes" in partial_values else 0.0
    uncertainty_penalty = 5.0 if "yes" in uncertainty_values else 0.0
    night_ir_penalty = 4.0 if clean(row["pair_has_night_ir_artifact"]) == "yes" else 0.0

    base_weighted = 100.0 * (
        0.22 * (pair_pattern / 3.0)
        + 0.20 * (pair_side / 3.0)
        + 0.16 * side_compatibility_score
        + 0.14 * (pair_body / 3.0)
        + 0.10 * (pair_blur / 3.0)
        + 0.08 * (pair_occ / 3.0)
        + 0.04 * (pair_contrast / 2.0)
    )
    weighted = max(
        0.0,
        min(
            100.0,
            base_weighted
            - frontal_penalty
            - silhouette_penalty
            - partial_penalty
            - uncertainty_penalty
            - night_ir_penalty,
        ),
    )

    min_components = [
        100.0 * pair_pattern / 3.0,
        100.0 * pair_side / 3.0,
        100.0 * pair_body / 3.0,
        100.0 * pair_blur / 3.0,
        100.0 * pair_occ / 3.0,
        100.0 * pair_contrast / 2.0,
    ]
    min_rule = min(min_components)
    if side_compatible == "no":
        min_rule = min(min_rule, 35.0)
    elif side_compatible == "unknown":
        min_rule = min(min_rule, 55.0)
    if frontal_penalty >= 8.0:
        min_rule = min(min_rule, 70.0)
    if silhouette_penalty > 0:
        min_rule = min(min_rule, 30.0)
    if partial_penalty > 0:
        min_rule = min(min_rule, 75.0)
    if uncertainty_penalty > 0:
        min_rule = min(min_rule, 80.0)

    components = {
        "pattern_score_a": pattern_a,
        "pattern_score_b": pattern_b,
        "side_quality_score_a": side_a,
        "side_quality_score_b": side_b,
        "body_fraction_score_a": body_a,
        "body_fraction_score_b": body_b,
        "blur_score_a": blur_a,
        "blur_score_b": blur_b,
        "occlusion_score_a": occ_a,
        "occlusion_score_b": occ_b,
        "contrast_score_a": contrast_a,
        "contrast_score_b": contrast_b,
        "pair_pattern_min_score": pair_pattern,
        "pair_side_quality_min_score": pair_side,
        "pair_body_fraction_min_score": pair_body,
        "pair_blur_min_score": pair_blur,
        "pair_occlusion_min_score": pair_occ,
        "pair_contrast_min_score": pair_contrast,
        "pair_side_compatibility_score": side_compatibility_score,
        "frontal_rear_penalty": frontal_penalty,
        "silhouette_penalty": silhouette_penalty,
        "partial_body_penalty": partial_penalty,
        "uncertainty_penalty": uncertainty_penalty,
        "night_ir_penalty": night_ir_penalty,
        "visual_pf_eri_min_rule": round(min_rule, 4),
        "visual_pf_eri_weighted": round(weighted, 4),
    }
    components["visual_pf_eri_band"] = band(weighted)
    components["primary_limiting_factor_for_score"] = limiting_factor(components)
    return components


def numeric(values: list[object]) -> list[float]:
    return [float(value) for value in values]


def quantile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[int(pos)]
    return ordered[low] * (high - pos) + ordered[high] * (pos - low)


def summarize_group(rows: list[dict[str, object]], label: str) -> list[dict[str, object]]:
    scores = numeric([row["visual_pf_eri_weighted"] for row in rows])
    min_scores = numeric([row["visual_pf_eri_min_rule"] for row in rows])
    same = [row for row in rows if row["same_identity"] == "yes"]
    different = [row for row in rows if row["same_identity"] == "no"]
    output = [
        {"metric": f"{label}_pair_count", "value": len(rows)},
        {"metric": f"{label}_same_count", "value": len(same)},
        {"metric": f"{label}_different_count", "value": len(different)},
    ]
    if scores:
        output.extend(
            [
                {"metric": f"{label}_weighted_mean", "value": round(mean(scores), 4)},
                {"metric": f"{label}_weighted_median", "value": round(median(scores), 4)},
                {"metric": f"{label}_weighted_q10", "value": round(quantile(scores, 0.10), 4)},
                {"metric": f"{label}_weighted_q25", "value": round(quantile(scores, 0.25), 4)},
                {"metric": f"{label}_weighted_q75", "value": round(quantile(scores, 0.75), 4)},
                {"metric": f"{label}_weighted_q90", "value": round(quantile(scores, 0.90), 4)},
                {"metric": f"{label}_min_rule_mean", "value": round(mean(min_scores), 4)},
                {"metric": f"{label}_min_rule_median", "value": round(median(min_scores), 4)},
            ]
        )
    return output


def descriptor_mean(rows: list[dict[str, object]], field: str) -> str:
    values = [float(row[field]) for row in rows if row.get(field, "") != ""]
    return "" if not values else f"{mean(values):.6f}"


def build_summary(input_rows: list[dict[str, str]], score_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [
        {"metric": "input_pair_count", "value": len(input_rows)},
        {
            "metric": "eligible_labeled_pair_count",
            "value": len(score_rows),
        },
    ]
    rows.extend(summarize_group(score_rows, "all_eligible"))
    rows.extend(summarize_group([row for row in score_rows if row["same_identity"] == "yes"], "same_identity"))
    rows.extend(summarize_group([row for row in score_rows if row["same_identity"] == "no"], "different_identity"))
    for score_band in ["high", "medium", "low", "unusable"]:
        band_rows = [row for row in score_rows if row["visual_pf_eri_band"] == score_band]
        rows.extend(summarize_group(band_rows, f"band_{score_band}"))
    for side_class in ["yes", "no", "unknown"]:
        side_rows = [row for row in score_rows if row["pair_side_compatible"] == side_class]
        rows.extend(summarize_group(side_rows, f"side_compatible_{side_class}"))
    for factor, count in Counter(row["primary_limiting_factor_for_score"] for row in score_rows).most_common():
        factor_rows = [row for row in score_rows if row["primary_limiting_factor_for_score"] == factor]
        rows.append({"metric": f"limiting_factor_{factor}_count", "value": count})
        rows.append(
            {
                "metric": f"limiting_factor_{factor}_weighted_median",
                "value": round(median(numeric([row["visual_pf_eri_weighted"] for row in factor_rows])), 4),
            }
        )
    rows.append(
        {
            "metric": "descriptor_reference_note",
            "value": "descriptor similarities are copied as held-out reference context and are not score inputs",
        }
    )
    return rows


def build_driver_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    factor_columns = [
        "pair_pattern_min_score",
        "pair_side_quality_min_score",
        "pair_body_fraction_min_score",
        "pair_blur_min_score",
        "pair_occlusion_min_score",
        "pair_contrast_min_score",
        "pair_side_compatibility_score",
        "primary_limiting_factor_for_score",
        "pair_side_compatible",
        "pair_primary_limiting_factor_combined",
        "visual_pf_eri_band",
    ]
    output: list[dict[str, object]] = []
    for factor in factor_columns:
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            grouped[str(row[factor])].append(row)
        for level, level_rows in sorted(grouped.items(), key=lambda item: item[0]):
            same_count = sum(1 for row in level_rows if row["same_identity"] == "yes")
            different_count = sum(1 for row in level_rows if row["same_identity"] == "no")
            scores = numeric([row["visual_pf_eri_weighted"] for row in level_rows])
            output.append(
                {
                    "factor": factor,
                    "level": level,
                    "pair_count": len(level_rows),
                    "same_count": same_count,
                    "different_count": different_count,
                    "same_proportion": round(same_count / len(level_rows), 6) if level_rows else "",
                    "mean_visual_pf_eri_weighted": round(mean(scores), 4) if scores else "",
                    "median_visual_pf_eri_weighted": round(median(scores), 4) if scores else "",
                    "mean_resnet50_similarity_reference_only": descriptor_mean(
                        level_rows, "resnet50_similarity_reference_only"
                    ),
                    "mean_megadescriptor_similarity_reference_only": descriptor_mean(
                        level_rows, "megadescriptor_similarity_reference_only"
                    ),
                    "eligibility_context": "eligible_labeled_pairs_only",
                }
            )
    return output


def build_risk_bins(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for score_band in ["high", "medium", "low", "unusable"]:
        band_rows = [row for row in rows if row["visual_pf_eri_band"] == score_band]
        same_count = sum(1 for row in band_rows if row["same_identity"] == "yes")
        different_count = sum(1 for row in band_rows if row["same_identity"] == "no")
        output.append(
            {
                "bin": score_band,
                "score_rule": "visual_pf_eri_weighted fixed bands: high>=75, medium>=50, low>=25, unusable<25",
                "pair_count": len(band_rows),
                "same_count": same_count,
                "different_count": different_count,
                "same_proportion": round(same_count / len(band_rows), 6) if band_rows else "",
                "mean_resnet50_similarity_reference_only": descriptor_mean(
                    band_rows, "resnet50_similarity_reference_only"
                ),
                "mean_megadescriptor_similarity_reference_only": descriptor_mean(
                    band_rows, "megadescriptor_similarity_reference_only"
                ),
                "minimum_sample_caveat": "ok" if len(band_rows) >= 30 else "sparse_bin",
                "interpretation": interpretation_for_band(score_band),
            }
        )
    return output


def save_figures(rows: list[dict[str, object]]) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    scores = numeric([row["visual_pf_eri_weighted"] for row in rows])

    plt.figure(figsize=(8, 5))
    plt.hist(scores, bins=20, color="#4C78A8", edgecolor="black", alpha=0.85)
    plt.xlabel("Visual-only PF-ERI weighted score")
    plt.ylabel("Pair count")
    plt.title("Visual-only PF-ERI score distribution")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "visual_pf_eri_weighted_histogram.png", dpi=160)
    plt.close()

    plt.figure(figsize=(7, 5))
    data = [
        numeric([row["visual_pf_eri_weighted"] for row in rows if row["same_identity"] == "yes"]),
        numeric([row["visual_pf_eri_weighted"] for row in rows if row["same_identity"] == "no"]),
    ]
    plt.boxplot(data, tick_labels=["same", "different"], showmeans=True)
    plt.ylabel("Visual-only PF-ERI weighted score")
    plt.title("Visual-only score by pair label (reference only)")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "visual_pf_eri_same_vs_different_boxplot.png", dpi=160)
    plt.close()

    plt.figure(figsize=(7, 5))
    labels = ["yes", "no", "unknown"]
    data = [numeric([row["visual_pf_eri_weighted"] for row in rows if row["pair_side_compatible"] == label]) for label in labels]
    plt.boxplot(data, tick_labels=labels, showmeans=True)
    plt.xlabel("Pair side compatible")
    plt.ylabel("Visual-only PF-ERI weighted score")
    plt.title("Visual-only score by side compatibility")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "visual_pf_eri_by_side_compatibility.png", dpi=160)
    plt.close()

    limiting_counts = Counter(row["primary_limiting_factor_for_score"] for row in rows)
    factors = [item[0] for item in limiting_counts.most_common()]
    medians = [
        median(numeric([row["visual_pf_eri_weighted"] for row in rows if row["primary_limiting_factor_for_score"] == factor]))
        for factor in factors
    ]
    plt.figure(figsize=(10, 5))
    plt.bar(factors, medians, color="#59A14F")
    plt.xticks(rotation=35, ha="right")
    plt.ylabel("Median visual-only PF-ERI weighted score")
    plt.title("Visual-only score by primary limiting factor")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "visual_pf_eri_by_primary_limiting_factor.png", dpi=160)
    plt.close()

    risk_bins = build_risk_bins(rows)
    labels = [row["bin"] for row in risk_bins]
    same_counts = [int(row["same_count"]) for row in risk_bins]
    different_counts = [int(row["different_count"]) for row in risk_bins]
    plt.figure(figsize=(8, 5))
    plt.bar(labels, different_counts, label="different", color="#E15759")
    plt.bar(labels, same_counts, bottom=different_counts, label="same", color="#4C78A8")
    plt.xlabel("Visual-only PF-ERI weighted band")
    plt.ylabel("Pair count")
    plt.title("Same/different composition by visual-only score band")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "visual_pf_eri_score_bin_composition.png", dpi=160)
    plt.close()

    plt.figure(figsize=(7, 5))
    plt.scatter(
        numeric([row["visual_pf_eri_weighted"] for row in rows]),
        numeric([row["megadescriptor_similarity_reference_only"] for row in rows]),
        s=12,
        alpha=0.45,
        label="MegaDescriptor reference only",
    )
    plt.scatter(
        numeric([row["visual_pf_eri_weighted"] for row in rows]),
        numeric([row["resnet50_similarity_reference_only"] for row in rows]),
        s=12,
        alpha=0.35,
        label="ResNet50 reference only",
    )
    plt.xlabel("Visual-only PF-ERI weighted score")
    plt.ylabel("Descriptor similarity (not used in score)")
    plt.title("Visual score vs descriptor similarity reference signals")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "visual_pf_eri_vs_descriptor_similarity_reference_only.png", dpi=160)
    plt.close()


def build(input_csv: Path, output_dir: Path) -> dict[str, object]:
    rows, headers = read_csv(input_csv)
    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        raise ValueError("input table missing required column(s): " + ", ".join(missing))

    score_rows: list[dict[str, object]] = []
    for row in rows:
        if clean(row["pair_modeling_eligible"]) != "yes":
            continue
        if clean(row["pair_label_available"]) != "yes":
            continue
        components = compute_scores(row)
        out_row: dict[str, object] = {
            "pair_id": row["pair_id"],
            "image_id_a": row["image_id_a"],
            "image_id_b": row["image_id_b"],
            "same_identity": clean(row["same_identity"]),
            "source_phase_a": row["source_phase_a"],
            "source_phase_b": row["source_phase_b"],
            "pair_source_phase_type": row["pair_source_phase_type"],
            "pair_modeling_eligible": row["pair_modeling_eligible"],
            "pair_exclusion_reason": row["pair_exclusion_reason"],
            "pair_side_compatible": clean(row["pair_side_compatible"]),
            "pair_primary_limiting_factor_combined": row["pair_primary_limiting_factor_combined"],
            **components,
            "resnet50_similarity_reference_only": float(row["resnet50_similarity"]),
            "megadescriptor_similarity_reference_only": float(row["megadescriptor_similarity"]),
            "descriptor_reference_note": "copied reference only; not used in visual PF-ERI scores",
        }
        score_rows.append(out_row)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(SCORES_CSV, score_rows, PAIR_SCORE_FIELDS)
    write_csv(SUMMARY_CSV, build_summary(rows, score_rows), ["metric", "value"])
    write_csv(
        DRIVER_CSV,
        build_driver_summary(score_rows),
        [
            "factor",
            "level",
            "pair_count",
            "same_count",
            "different_count",
            "same_proportion",
            "mean_visual_pf_eri_weighted",
            "median_visual_pf_eri_weighted",
            "mean_resnet50_similarity_reference_only",
            "mean_megadescriptor_similarity_reference_only",
            "eligibility_context",
        ],
    )
    write_csv(
        RISK_BINS_CSV,
        build_risk_bins(score_rows),
        [
            "bin",
            "score_rule",
            "pair_count",
            "same_count",
            "different_count",
            "same_proportion",
            "mean_resnet50_similarity_reference_only",
            "mean_megadescriptor_similarity_reference_only",
            "minimum_sample_caveat",
            "interpretation",
        ],
    )
    save_figures(score_rows)
    return {
        "input_pair_count": len(rows),
        "eligible_labeled_pair_count": len(score_rows),
        "same_count": sum(1 for row in score_rows if row["same_identity"] == "yes"),
        "different_count": sum(1 for row in score_rows if row["same_identity"] == "no"),
        "mean_visual_pf_eri_weighted": round(mean(numeric([row["visual_pf_eri_weighted"] for row in score_rows])), 4),
        "median_visual_pf_eri_weighted": round(median(numeric([row["visual_pf_eri_weighted"] for row in score_rows])), 4),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build(args.input_csv.resolve(), args.output_dir.resolve())
    print("Phase 7A visual-only PF-ERI gate complete")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"output_dir: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
