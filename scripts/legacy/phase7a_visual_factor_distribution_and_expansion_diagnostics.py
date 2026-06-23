#!/usr/bin/env python3
"""Summarize Phase 7A 1000-image visual factors and expansion diagnostics."""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_phase7a_1000_image_annotations_v1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase7a/visual_factor_diagnostics"
FIGURE_DIR = OUTPUT_DIR / "figures"

FACTOR_COLUMNS = [
    "pattern_visibility",
    "side_visibility",
    "side_evidence_quality",
    "body_fraction_visible",
    "partial_body",
    "frontal_or_rear_view",
    "silhouette_only",
    "blur_level",
    "occlusion_level",
    "lighting_condition",
    "night_ir_artifact",
    "contrast_level",
    "primary_limiting_factor",
    "uncertainty_flag",
    "annotation_status",
    "source_phase",
    "quality_bucket",
    "selection_stratum",
]

SOURCE_PHASES = ["phase4_original_500", "phase6_v2_balanced_500"]

COOCCURRENCE_PAIRS = [
    ("pattern_visibility", "side_visibility"),
    ("pattern_visibility", "blur_level"),
    ("pattern_visibility", "occlusion_level"),
    ("side_visibility", "frontal_or_rear_view"),
    ("body_fraction_visible", "partial_body"),
    ("lighting_condition", "night_ir_artifact"),
    ("contrast_level", "pattern_visibility"),
    ("primary_limiting_factor", "annotation_status"),
]

SPARSE_THRESHOLD = 30
CONDITIONAL_THRESHOLD = 50
COOCCURRENCE_THRESHOLD = 20


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def proportion(count: int, denominator: int) -> float:
    return round(count / denominator, 6) if denominator else 0.0


def source_count(rows: list[dict[str, str]], source_phase: str) -> int:
    return sum(row["source_phase"] == source_phase for row in rows)


def subgroup_status(count: int) -> str:
    if count < SPARSE_THRESHOLD:
        return "sparse"
    if count <= CONDITIONAL_THRESHOLD:
        return "conditionally_sparse"
    return "adequate_for_first_pass"


def sparse_reason(count: int) -> str:
    if count < SPARSE_THRESHOLD:
        return f"count below {SPARSE_THRESHOLD}; not stable for subgroup claims"
    if count <= CONDITIONAL_THRESHOLD:
        return f"count between {SPARSE_THRESHOLD} and {CONDITIONAL_THRESHOLD}; use conditional caveat"
    return "not sparse by simple count threshold"


def ensure_input(rows: list[dict[str, str]]) -> None:
    if len(rows) != 1000:
        raise ValueError(f"expected 1000 rows, found {len(rows)}")
    missing = [column for column in FACTOR_COLUMNS if column not in rows[0]]
    if missing:
        raise ValueError(f"input missing required factor columns: {missing}")
    counts = Counter(row["source_phase"] for row in rows)
    for source_phase in SOURCE_PHASES:
        if counts[source_phase] != 500:
            raise ValueError(f"expected 500 rows for {source_phase}, found {counts[source_phase]}")


def factor_count_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    total = len(rows)
    source_totals = {source: source_count(rows, source) for source in SOURCE_PHASES}
    for factor in FACTOR_COLUMNS:
        levels = sorted({row[factor] for row in rows})
        for level in levels:
            level_rows = [row for row in rows if row[factor] == level]
            record: dict[str, object] = {
                "factor": factor,
                "level": level,
                "count": len(level_rows),
                "proportion": proportion(len(level_rows), total),
            }
            for source in SOURCE_PHASES:
                count = sum(row["source_phase"] == source for row in level_rows)
                short = "phase4" if source == "phase4_original_500" else "phase6_v2"
                record[f"{short}_count"] = count
                record[f"{short}_proportion_within_source"] = proportion(count, source_totals[source])
            out.append(record)
    return out


def factor_count_by_source_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for factor in FACTOR_COLUMNS:
        for source in SOURCE_PHASES:
            source_rows = [row for row in rows if row["source_phase"] == source]
            counts = Counter(row[factor] for row in source_rows)
            for level in sorted(counts):
                out.append(
                    {
                        "factor": factor,
                        "level": level,
                        "source_phase": source,
                        "count": counts[level],
                        "proportion_within_source": proportion(counts[level], len(source_rows)),
                    }
                )
    return out


def sparse_level_rows(factor_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for row in factor_rows:
        count = int(row["count"])
        if count <= CONDITIONAL_THRESHOLD:
            out.append(
                {
                    "factor": row["factor"],
                    "level": row["level"],
                    "count": count,
                    "proportion": row["proportion"],
                    "sparse_flag": subgroup_status(count),
                    "reason": sparse_reason(count),
                }
            )
    return out


def cooccurrence_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    total = len(rows)
    for factor_a, factor_b in COOCCURRENCE_PAIRS:
        pairs = Counter((row[factor_a], row[factor_b]) for row in rows)
        for (level_a, level_b), count in sorted(pairs.items()):
            phase4_count = sum(
                row["source_phase"] == "phase4_original_500"
                and row[factor_a] == level_a
                and row[factor_b] == level_b
                for row in rows
            )
            phase6_count = count - phase4_count
            out.append(
                {
                    "factor_a": factor_a,
                    "level_a": level_a,
                    "factor_b": factor_b,
                    "level_b": level_b,
                    "count": count,
                    "proportion": proportion(count, total),
                    "phase4_count": phase4_count,
                    "phase6_v2_count": phase6_count,
                    "sparse_flag": "sparse" if count < COOCCURRENCE_THRESHOLD else "not_sparse",
                    "reason": (
                        f"co-occurrence count below {COOCCURRENCE_THRESHOLD}"
                        if count < COOCCURRENCE_THRESHOLD
                        else "co-occurrence count meets simple threshold"
                    ),
                }
            )
    return out


def mask_rows(rows: list[dict[str, str]], name: str) -> list[dict[str, str]]:
    if name == "complete_only":
        return [row for row in rows if row["annotation_status"] == "complete"]
    if name == "high_pattern_side_visible":
        return [
            row
            for row in rows
            if row["pattern_visibility"] == "high" and row["side_visibility"] in {"left", "right", "both"}
        ]
    if name == "low_none_pattern":
        return [row for row in rows if row["pattern_visibility"] in {"low", "none"}]
    if name == "side_unknown":
        return [row for row in rows if row["side_visibility"] == "unknown"]
    if name == "frontal_rear_view":
        return [
            row
            for row in rows
            if row["frontal_or_rear_view"] == "yes" or row["side_visibility"] in {"frontal", "rear"}
        ]
    if name == "severe_blur":
        return [row for row in rows if row["blur_level"] == "severe"]
    if name == "major_occlusion":
        return [row for row in rows if row["occlusion_level"] == "major"]
    if name == "low_contrast":
        return [row for row in rows if row["contrast_level"] == "low"]
    if name == "night_ir_artifact":
        return [row for row in rows if row["night_ir_artifact"] == "yes" or row["lighting_condition"] == "night_ir"]
    if name == "partial_body":
        return [row for row in rows if row["partial_body"] == "yes"]
    if name == "extreme_hard_proxy":
        return [row for row in rows if row["quality_bucket"] == "extreme_hard_proxy"]
    if name == "needs_review":
        return [row for row in rows if row["annotation_status"] == "needs_review"]
    raise ValueError(f"unknown subgroup: {name}")


def ess_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    subgroups = [
        ("complete_only", "complete-only sample"),
        ("high_pattern_side_visible", "high pattern + side visible"),
        ("low_none_pattern", "low/none pattern"),
        ("side_unknown", "side unknown"),
        ("frontal_rear_view", "frontal/rear view"),
        ("severe_blur", "severe blur"),
        ("major_occlusion", "major occlusion"),
        ("low_contrast", "low contrast"),
        ("night_ir_artifact", "night IR artifact or night IR lighting"),
        ("partial_body", "partial body"),
        ("extreme_hard_proxy", "extreme_hard_proxy"),
        ("needs_review", "needs_review"),
    ]
    out: list[dict[str, object]] = []
    for key, label in subgroups:
        subset = mask_rows(rows, key)
        count = len(subset)
        phase4_count = source_count(subset, "phase4_original_500")
        phase6_count = source_count(subset, "phase6_v2_balanced_500")
        status = subgroup_status(count)
        if key == "complete_only":
            status = "adequate_for_first_pass" if count >= 950 else status
        out.append(
            {
                "diagnostic": key,
                "description": label,
                "count": count,
                "proportion": proportion(count, len(rows)),
                "phase4_count": phase4_count,
                "phase6_v2_count": phase6_count,
                "complete_count": sum(row["annotation_status"] == "complete" for row in subset),
                "needs_review_count": sum(row["annotation_status"] == "needs_review" for row in subset),
                "uncertainty_yes_count": sum(row["uncertainty_flag"] == "yes" for row in subset),
                "effective_sample_size": count,
                "adequacy_status": status,
                "interpretation": sparse_reason(count) if key != "complete_only" else "complete-only sample is large enough for global first-pass diagnostics",
            }
        )
    return out


def expansion_trigger_rows(
    rows: list[dict[str, str]],
    sparse_rows: list[dict[str, object]],
    co_rows: list[dict[str, object]],
    ess: list[dict[str, object]],
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []

    def add(diagnostic: str, observed: object, threshold: str, status: str, interpretation: str, action: str) -> None:
        out.append(
            {
                "diagnostic": diagnostic,
                "observed_value": observed,
                "threshold": threshold,
                "trigger_status": status,
                "interpretation": interpretation,
                "recommended_action": action,
            }
        )

    add(
        "total_image_count",
        len(rows),
        ">=1000 for first-pass global image-level diagnostics",
        "no_trigger" if len(rows) >= 1000 else "triggered",
        "1000-image resource is available",
        "proceed to first-pass image-level PF-ERI readiness work; do not infer pair-level risk from this alone",
    )

    complete_count = sum(row["annotation_status"] == "complete" for row in rows)
    add(
        "complete_only_count",
        complete_count,
        ">=950 complete rows",
        "no_trigger" if complete_count >= 950 else "triggered",
        f"{complete_count} rows are complete",
        "retain needs_review caveat; no broad expansion needed for completion rate",
    )

    sparse_factor_count = len(sparse_rows)
    hard_sparse_count = sum(row["sparse_flag"] == "sparse" for row in sparse_rows)
    add(
        "sparse_factor_level_count",
        f"{hard_sparse_count} hard sparse levels; {sparse_factor_count} total sparse or conditional levels",
        "0 hard sparse levels for strong subgroup claims",
        "triggered" if hard_sparse_count else "no_trigger",
        "Some rare image-level states are underpowered for strong subgroup claims",
        "do not claim rare-subgroup stability; use targeted expansion if those subgroups become central",
    )

    sparse_co = [row for row in co_rows if row["sparse_flag"] == "sparse"]
    sparse_ratio = len(sparse_co) / len(co_rows) if co_rows else 0.0
    add(
        "sparse_key_cooccurrence_cells",
        f"{len(sparse_co)} of {len(co_rows)} ({sparse_ratio:.3f})",
        f"no key co-occurrence cell below {COOCCURRENCE_THRESHOLD} for strong interaction claims",
        "triggered" if sparse_co else "no_trigger",
        "Several two-factor cells are sparse, so high-order interaction claims would be weak",
        "limit Phase 7A to main effects and coarse staged policies unless targeted pair/image expansion is added",
    )

    contrast_na = sum(row["contrast_level"] == "not_available" for row in rows)
    add(
        "phase4_contrast_unavailable",
        contrast_na,
        "0 unavailable rows for full 1000-image contrast analysis",
        "conditional_trigger" if contrast_na else "no_trigger",
        "Contrast is available only for Phase 6 v2; Phase 4 contrast cannot be analyzed as a full 1000-image factor",
        "treat contrast as Phase 6-only or collect comparable contrast labels in any future expansion",
    )

    mapping_warning = sum(row["source_phase"] == "phase4_original_500" and "mapped_to" in row["mapping_notes"] for row in rows)
    add(
        "phase4_conservative_mapping_rows",
        mapping_warning,
        "0 conservative mapping rows for fully direct harmonization",
        "conditional_trigger" if mapping_warning else "no_trigger",
        "Phase 4 contains conservative harmonization for some ordinal/state fields",
        "preserve mapping caveats in later PF-ERI scoring; avoid overinterpreting mapped factor levels",
    )

    for row in ess:
        status = row["adequacy_status"]
        if status in {"sparse", "conditionally_sparse"}:
            add(
                f"effective_sample_size_{row['diagnostic']}",
                row["count"],
                f"> {CONDITIONAL_THRESHOLD} for first-pass subgroup stability; >=30 minimum descriptive threshold",
                "triggered" if status == "sparse" else "conditional_trigger",
                str(row["interpretation"]),
                "target this subgroup only if it is needed for claims or future risk modeling",
            )

    if any(row["trigger_status"] == "triggered" for row in out):
        overall = "targeted_expansion_recommended_for_subgroup_claims"
    elif any(row["trigger_status"] == "conditional_trigger" for row in out):
        overall = "conditional_expansion_later"
    else:
        overall = "no_expansion_needed_now"
    add(
        "overall_expansion_decision",
        overall,
        "no hard sparse triggers for no expansion",
        overall,
        "1000 images support first-pass global diagnostics, but sparse subgroup and co-occurrence triggers limit strong subgroup claims",
        "proceed with first-pass PF-ERI modeling; plan targeted expansion only if later pair/risk modeling depends on sparse groups",
    )
    return out


def recommendation_rows(
    rows: list[dict[str, str]],
    ess: list[dict[str, object]],
    sparse: list[dict[str, object]],
) -> list[dict[str, object]]:
    recommendations: list[dict[str, object]] = []
    priority_order = {"sparse": "high", "conditionally_sparse": "medium"}

    for row in ess:
        status = row["adequacy_status"]
        if status not in priority_order:
            continue
        count = int(row["count"])
        target = 50 if status == "sparse" else 75
        recommendations.append(
            {
                "target_subgroup": row["diagnostic"],
                "reason": row["interpretation"],
                "current_count": count,
                "recommended_additional_count": max(target - count, 0),
                "priority": priority_order[status],
                "sampling_logic": "targeted sampling from candidate images; do not use random expansion for this subgroup",
            }
        )

    contrast_na = sum(row["contrast_level"] == "not_available" for row in rows)
    if contrast_na:
        recommendations.append(
            {
                "target_subgroup": "contrast_level_comparable_labels",
                "reason": "contrast_level is not available for Phase 4, limiting full 1000-image contrast analysis",
                "current_count": len(rows) - contrast_na,
                "recommended_additional_count": 250,
                "priority": "medium",
                "sampling_logic": "if contrast becomes central, annotate comparable contrast labels for Phase 4 or collect new balanced contrast examples",
            }
        )

    recommendation_keys = {(row["target_subgroup"], row["current_count"]) for row in recommendations}
    key_sparse_factors = {
        "side_visibility",
        "body_fraction_visible",
        "occlusion_level",
        "lighting_condition",
        "primary_limiting_factor",
        "uncertainty_flag",
        "annotation_status",
    }
    for row in sparse:
        factor = str(row["factor"])
        level = str(row["level"])
        if factor not in key_sparse_factors:
            continue
        if factor == "annotation_status" and level == "needs_review":
            continue
        if factor == "uncertainty_flag" and level != "yes":
            continue
        count = int(row["count"])
        status = str(row["sparse_flag"])
        target = 50 if status == "sparse" else 75
        subgroup = f"{factor}={level}"
        key = (subgroup, count)
        if key in recommendation_keys:
            continue
        recommendations.append(
            {
                "target_subgroup": subgroup,
                "reason": row["reason"],
                "current_count": count,
                "recommended_additional_count": max(target - count, 0),
                "priority": "high" if status == "sparse" else "medium",
                "sampling_logic": "targeted sampling only if this factor level becomes central to PF-ERI claims or pair-risk modeling",
            }
        )
        recommendation_keys.add(key)

    recommendations.append(
        {
            "target_subgroup": "global_1000_image_resource",
            "reason": "global image-level count is sufficient for first-pass PF-ERI readiness diagnostics",
            "current_count": len(rows),
            "recommended_additional_count": 0,
            "priority": "none_now",
            "sampling_logic": "do not expand randomly before pair-level and risk-model diagnostics identify specific data gaps",
        }
    )
    return recommendations


def plot_factor_counts(rows: list[dict[str, str]], factor: str, path: Path) -> None:
    counts = Counter(row[factor] for row in rows)
    labels = list(sorted(counts))
    values = [counts[label] for label in labels]
    fig, ax = plt.subplots(figsize=(max(7, len(labels) * 0.7), 4.5))
    ax.bar(labels, values, color="#4C78A8")
    ax.set_title(f"{factor} distribution")
    ax.set_ylabel("Image count")
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_source_comparison(rows: list[dict[str, str]], factor: str, path: Path) -> None:
    levels = sorted({row[factor] for row in rows})
    width = 0.38
    x = list(range(len(levels)))
    fig, ax = plt.subplots(figsize=(max(8, len(levels) * 0.8), 4.5))
    for idx, source in enumerate(SOURCE_PHASES):
        source_rows = [row for row in rows if row["source_phase"] == source]
        counts = Counter(row[factor] for row in source_rows)
        values = [counts[level] for level in levels]
        offset = -width / 2 if idx == 0 else width / 2
        label = "Phase 4" if source == "phase4_original_500" else "Phase 6 v2"
        ax.bar([i + offset for i in x], values, width=width, label=label)
    ax.set_title(f"{factor}: Phase 4 vs Phase 6 v2")
    ax.set_ylabel("Image count")
    ax.set_xticks(x)
    ax.set_xticklabels(levels, rotation=35, ha="right", fontsize=8)
    ax.legend()
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_cooccurrence_heatmap(rows: list[dict[str, str]], factor_a: str, factor_b: str, path: Path) -> None:
    levels_a = sorted({row[factor_a] for row in rows})
    levels_b = sorted({row[factor_b] for row in rows})
    matrix = []
    for level_a in levels_a:
        matrix.append([sum(row[factor_a] == level_a and row[factor_b] == level_b for row in rows) for level_b in levels_b])
    fig, ax = plt.subplots(figsize=(max(7, len(levels_b) * 0.8), max(4.5, len(levels_a) * 0.45)))
    image = ax.imshow(matrix, cmap="Blues")
    ax.set_title(f"{factor_a} x {factor_b}")
    ax.set_xticks(range(len(levels_b)))
    ax.set_xticklabels(levels_b, rotation=35, ha="right", fontsize=8)
    ax.set_yticks(range(len(levels_a)))
    ax.set_yticklabels(levels_a, fontsize=8)
    for i, level_a in enumerate(levels_a):
        for j, level_b in enumerate(levels_b):
            value = matrix[i][j]
            ax.text(j, i, str(value), ha="center", va="center", fontsize=7, color="black")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run(input_csv: Path, output_dir: Path) -> dict[str, object]:
    rows = read_csv(input_csv)
    ensure_input(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    factor_rows = factor_count_rows(rows)
    by_source = factor_count_by_source_rows(rows)
    sparse = sparse_level_rows(factor_rows)
    co = cooccurrence_rows(rows)
    ess = ess_rows(rows)
    triggers = expansion_trigger_rows(rows, sparse, co, ess)
    recommendations = recommendation_rows(rows, ess, sparse)

    write_csv(
        output_dir / "phase7a_1000_image_factor_counts.csv",
        factor_rows,
        [
            "factor",
            "level",
            "count",
            "proportion",
            "phase4_count",
            "phase4_proportion_within_source",
            "phase6_v2_count",
            "phase6_v2_proportion_within_source",
        ],
    )
    write_csv(
        output_dir / "phase7a_1000_image_factor_counts_by_source_phase.csv",
        by_source,
        ["factor", "level", "source_phase", "count", "proportion_within_source"],
    )
    write_csv(
        output_dir / "phase7a_1000_image_sparse_factor_levels.csv",
        sparse,
        ["factor", "level", "count", "proportion", "sparse_flag", "reason"],
    )
    write_csv(
        output_dir / "phase7a_1000_image_factor_cooccurrence_key_pairs.csv",
        co,
        [
            "factor_a",
            "level_a",
            "factor_b",
            "level_b",
            "count",
            "proportion",
            "phase4_count",
            "phase6_v2_count",
            "sparse_flag",
            "reason",
        ],
    )
    write_csv(
        output_dir / "phase7a_1000_image_effective_sample_size_diagnostics.csv",
        ess,
        [
            "diagnostic",
            "description",
            "count",
            "proportion",
            "phase4_count",
            "phase6_v2_count",
            "complete_count",
            "needs_review_count",
            "uncertainty_yes_count",
            "effective_sample_size",
            "adequacy_status",
            "interpretation",
        ],
    )
    write_csv(
        output_dir / "phase7a_1000_image_expansion_trigger_diagnostics.csv",
        triggers,
        ["diagnostic", "observed_value", "threshold", "trigger_status", "interpretation", "recommended_action"],
    )
    write_csv(
        output_dir / "phase7a_1000_image_expansion_recommendations.csv",
        recommendations,
        ["target_subgroup", "reason", "current_count", "recommended_additional_count", "priority", "sampling_logic"],
    )

    for factor in [
        "pattern_visibility",
        "side_visibility",
        "blur_level",
        "occlusion_level",
        "lighting_condition",
        "quality_bucket",
    ]:
        plot_factor_counts(rows, factor, FIGURE_DIR / f"{factor}_distribution.png")
        plot_source_comparison(rows, factor, FIGURE_DIR / f"{factor}_phase_comparison.png")
    for factor_a, factor_b in COOCCURRENCE_PAIRS[:4]:
        plot_cooccurrence_heatmap(rows, factor_a, factor_b, FIGURE_DIR / f"{factor_a}_x_{factor_b}_heatmap.png")

    summary = {
        "row_count": len(rows),
        "phase4_count": source_count(rows, "phase4_original_500"),
        "phase6_v2_count": source_count(rows, "phase6_v2_balanced_500"),
        "sparse_factor_level_count": len(sparse),
        "hard_sparse_factor_level_count": sum(row["sparse_flag"] == "sparse" for row in sparse),
        "sparse_cooccurrence_count": sum(row["sparse_flag"] == "sparse" for row in co),
        "overall_expansion_decision": [row for row in triggers if row["diagnostic"] == "overall_expansion_decision"][0][
            "observed_value"
        ],
    }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run(args.input_csv.resolve(), args.output_dir.resolve())
    print("Phase 7A visual-factor distribution and expansion diagnostics complete")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"output_dir: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
