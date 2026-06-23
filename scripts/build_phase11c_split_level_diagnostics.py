#!/usr/bin/env python3
"""Build Phase 11C split-level diagnostics for PF-ERI metric learning.

This script is diagnostic only. It reads existing manifests, visual labels,
pair-level PF-ERI scores, fixed embeddings, and optional retrieval metrics.
It does not train models and does not modify raw data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "outputs/czechlynx/phase10_lite/phase10_lite_plus_matched_training_manifest_k3.csv"
PAIR_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv"
VISUAL_LABELS = PROJECT_ROOT / "data/labels/czechlynx/czechlynx_mechanism_visual_factors_full_annotated.csv"
EMBEDDINGS = PROJECT_ROOT / "outputs/czechlynx/phase4/czechlynx_phase4c_megadescriptor_embeddings.csv"
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase11c/diagnostics"
DOC_PATH = PROJECT_ROOT / "docs/phase11/phase11c_split_level_diagnostic_report.md"

C3 = "C3_quality_proxy_matched_identity"
H3 = "H3_pf_eri_quality_hybrid_matched_identity"
EXPECTED_VISUAL_FIELDS = [
    "pattern_visibility",
    "side_evidence_quality",
    "blur_level",
    "occlusion_level",
    "body_fraction_visible",
    "frontal_or_rear_view",
    "side_visibility",
]

OUT_FILES = {
    "image_set_overlap": OUT_DIR / "phase11c_image_set_overlap_c3_vs_h3.csv",
    "image_quality": OUT_DIR / "phase11c_image_quality_distribution_by_split_group.csv",
    "positive_pairs": OUT_DIR / "phase11c_positive_pair_reliability_by_split_group.csv",
    "negative_pairs": OUT_DIR / "phase11c_negative_pair_hard_negative_by_split_group.csv",
    "split3": OUT_DIR / "phase11c_split3_special_diagnostic.csv",
    "correlations": OUT_DIR / "phase11c_metric_correlation_diagnostic.csv",
    "field_audit": OUT_DIR / "phase11c_split_level_diagnostic_field_audit.json",
}


def pct(condition: pd.Series) -> float:
    if len(condition) == 0:
        return float("nan")
    return float(condition.mean())


def safe_numeric(frame: pd.DataFrame, column: str, default: float = np.nan) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([default] * len(frame), index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce")


def flatten_distribution(frame: pd.DataFrame, column: str, prefix: str) -> dict[str, float | int | str]:
    if column not in frame.columns:
        return {f"{prefix}_missing": 1}
    counts = frame[column].fillna("missing").astype(str).value_counts(dropna=False)
    total = max(int(counts.sum()), 1)
    out: dict[str, float | int | str] = {}
    for value, count in counts.sort_index().items():
        safe_value = value.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
        out[f"{prefix}_{safe_value}_count"] = int(count)
        out[f"{prefix}_{safe_value}_pct"] = float(count / total)
    return out


def read_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    manifest = pd.read_csv(MANIFEST)
    pair_table = pd.read_csv(PAIR_TABLE)
    visual = pd.read_csv(VISUAL_LABELS)
    embeddings = pd.read_csv(EMBEDDINGS, usecols=["expanded_image_id", "embedding_dim"])
    audit = {
        "manifest_path": str(MANIFEST.relative_to(PROJECT_ROOT)),
        "pair_table_path": str(PAIR_TABLE.relative_to(PROJECT_ROOT)),
        "visual_labels_path": str(VISUAL_LABELS.relative_to(PROJECT_ROOT)),
        "embeddings_path": str(EMBEDDINGS.relative_to(PROJECT_ROOT)),
        "missing_visual_fields": sorted(set(EXPECTED_VISUAL_FIELDS) - set(visual.columns)),
        "embedding_image_count": int(embeddings["expanded_image_id"].astype(str).nunique()),
    }
    if audit["missing_visual_fields"]:
        raise ValueError(f"visual labels missing required fields: {audit['missing_visual_fields']}")
    return manifest, pair_table, visual, embeddings, audit


def enrich_manifest(manifest: pd.DataFrame, visual: pd.DataFrame) -> pd.DataFrame:
    visual_subset = visual[["expanded_image_id", *EXPECTED_VISUAL_FIELDS]].drop_duplicates("expanded_image_id")
    enriched = manifest.merge(visual_subset, how="left", left_on="image_id", right_on="expanded_image_id")
    if "quality_bucket_rank_normalized" not in enriched.columns:
        bucket_map = {"high": 1.0, "medium_high": 0.75, "medium_low": 0.5, "low": 0.25}
        enriched["quality_bucket_rank_normalized"] = enriched["quality_bucket"].astype(str).str.lower().map(bucket_map)
    return enriched


def build_image_set_overlap(enriched: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for split_id in sorted(enriched["split_id"].astype(int).unique()):
        c3 = enriched[(enriched["split_id"].astype(int) == split_id) & (enriched["phase10_lite_plus_group"].astype(str) == C3)]
        h3 = enriched[(enriched["split_id"].astype(int) == split_id) & (enriched["phase10_lite_plus_group"].astype(str) == H3)]
        c3_images = set(c3["image_id"].astype(str))
        h3_images = set(h3["image_id"].astype(str))
        c3_ids = set(c3["identity_label_internal"].astype(str))
        h3_ids = set(h3["identity_label_internal"].astype(str))
        rows.append(
            {
                "split_id": split_id,
                "c3_image_count": len(c3_images),
                "h3_image_count": len(h3_images),
                "shared_image_count": len(c3_images & h3_images),
                "c3_only_image_count": len(c3_images - h3_images),
                "h3_only_image_count": len(h3_images - c3_images),
                "shared_image_pct_of_c3": len(c3_images & h3_images) / max(len(c3_images), 1),
                "shared_image_pct_of_h3": len(c3_images & h3_images) / max(len(h3_images), 1),
                "c3_identity_count": len(c3_ids),
                "h3_identity_count": len(h3_ids),
                "shared_identity_count": len(c3_ids & h3_ids),
                "identity_sets_match": c3_ids == h3_ids,
                "c3_mean_pf_eri_image_score": float(safe_numeric(c3, "pf_eri_image_score").mean()),
                "h3_mean_pf_eri_image_score": float(safe_numeric(h3, "pf_eri_image_score").mean()),
                "c3_mean_quality_proxy_score": float(safe_numeric(c3, "quality_bucket_rank_normalized").mean()),
                "h3_mean_quality_proxy_score": float(safe_numeric(h3, "quality_bucket_rank_normalized").mean()),
                "c3_mean_hybrid_score": float(safe_numeric(c3, "hybrid_score").mean()),
                "h3_mean_hybrid_score": float(safe_numeric(h3, "hybrid_score").mean()),
            }
        )
    return pd.DataFrame(rows)


def build_image_quality_distribution(enriched: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    target = enriched[enriched["phase10_lite_plus_group"].astype(str).isin([C3, H3])].copy()
    for (split_id, group), frame in target.groupby(["split_id", "phase10_lite_plus_group"], sort=True):
        row: dict[str, object] = {
            "split_id": int(split_id),
            "group_name": str(group),
            "image_count": int(frame["image_id"].nunique()),
            "identity_count": int(frame["identity_label_internal"].nunique()),
            "mean_pf_eri_image_score": float(safe_numeric(frame, "pf_eri_image_score").mean()),
            "median_pf_eri_image_score": float(safe_numeric(frame, "pf_eri_image_score").median()),
            "mean_quality_proxy_score": float(safe_numeric(frame, "quality_bucket_rank_normalized").mean()),
            "mean_hybrid_score": float(safe_numeric(frame, "hybrid_score").mean()),
        }
        for column in EXPECTED_VISUAL_FIELDS:
            row.update(flatten_distribution(frame, column, column))
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_positive_pairs(pair_table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    positive = pair_table[pair_table["same_identity"].astype(bool)].copy()
    for (split_id, group), frame in positive.groupby(["split_id", "group_name"], sort=True):
        r = safe_numeric(frame, "pair_reliability_score")
        rows.append(
            {
                "split_id": int(split_id),
                "group_name": str(group),
                "positive_pair_count": int(len(frame)),
                "mean_pair_reliability_score": float(r.mean()),
                "median_pair_reliability_score": float(r.median()),
                "std_pair_reliability_score": float(r.std(ddof=0)),
                "min_pair_reliability_score": float(r.min()),
                "max_pair_reliability_score": float(r.max()),
                "pct_positive_pairs_r_lt_025": pct(r < 0.25),
                "pct_positive_pairs_r_lt_040": pct(r < 0.40),
                "pct_positive_pairs_r_gt_070": pct(r > 0.70),
                "mean_side_comparability_score": float(safe_numeric(frame, "side_comparability_score").mean()),
                "mean_pattern_pair_score": float(safe_numeric(frame, "pattern_pair_score").mean()),
                "mean_blur_pair_score": float(safe_numeric(frame, "blur_pair_score").mean()),
                "mean_occlusion_pair_score": float(safe_numeric(frame, "occlusion_pair_score").mean()),
                "mean_body_visibility_pair_score": float(safe_numeric(frame, "body_visibility_pair_score").mean()),
                "mean_viewpoint_compatibility_score": float(safe_numeric(frame, "viewpoint_compatibility_score").mean()),
            }
        )
    return pd.DataFrame(rows)


def summarize_negative_pairs(pair_table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    negative = pair_table[~pair_table["same_identity"].astype(bool)].copy()
    for (split_id, group), frame in negative.groupby(["split_id", "group_name"], sort=True):
        sim = safe_numeric(frame, "descriptor_similarity")
        r = safe_numeric(frame, "pair_reliability_score")
        hard = frame["hard_negative_flag"].astype(str).str.lower().isin(["true", "1", "yes"])
        hard_frame = frame[hard]
        hard_r = safe_numeric(hard_frame, "pair_reliability_score") if len(hard_frame) else pd.Series(dtype="float64")
        rows.append(
            {
                "split_id": int(split_id),
                "group_name": str(group),
                "negative_pair_count": int(len(frame)),
                "mean_negative_descriptor_similarity": float(sim.mean()),
                "top_decile_negative_similarity_threshold": float(sim.quantile(0.90)),
                "hard_negative_count": int(hard.sum()),
                "pct_hard_negative": float(hard.mean()),
                "mean_r_among_hard_negatives": float(hard_r.mean()) if len(hard_r) else float("nan"),
                "pct_hard_negatives_r_lte_040": pct(hard_r <= 0.40) if len(hard_r) else float("nan"),
                "mean_pair_reliability_score_negatives": float(r.mean()),
            }
        )
    return pd.DataFrame(rows)


def compare_split3(metric_frame: pd.DataFrame, metric_columns: Iterable[str], label: str) -> pd.DataFrame:
    rows = []
    for group, frame in metric_frame.groupby("group_name", sort=True):
        split3 = frame[frame["split_id"].astype(int) == 3]
        others = frame[frame["split_id"].astype(int).isin([1, 2, 4, 5])]
        if split3.empty or others.empty:
            continue
        for column in metric_columns:
            split3_value = pd.to_numeric(split3[column], errors="coerce").mean()
            other_value = pd.to_numeric(others[column], errors="coerce").mean()
            rows.append(
                {
                    "diagnostic_family": label,
                    "group_name": group,
                    "metric": column,
                    "split3_value": float(split3_value),
                    "other_splits_mean": float(other_value),
                    "split3_minus_other_splits_mean": float(split3_value - other_value),
                    "split3_ratio_to_other_splits_mean": float(split3_value / other_value) if other_value not in [0, np.nan] else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def build_split3_diagnostic(image_quality: pd.DataFrame, positive_pairs: pd.DataFrame, negative_pairs: pd.DataFrame) -> pd.DataFrame:
    pieces = [
        compare_split3(
            image_quality,
            [
                "mean_pf_eri_image_score",
                "mean_quality_proxy_score",
                "mean_hybrid_score",
            ],
            "image_quality",
        ),
        compare_split3(
            positive_pairs,
            [
                "mean_pair_reliability_score",
                "pct_positive_pairs_r_lt_025",
                "pct_positive_pairs_r_lt_040",
                "pct_positive_pairs_r_gt_070",
                "mean_side_comparability_score",
                "mean_pattern_pair_score",
            ],
            "positive_pair_reliability",
        ),
        compare_split3(
            negative_pairs,
            [
                "mean_negative_descriptor_similarity",
                "top_decile_negative_similarity_threshold",
                "hard_negative_count",
                "pct_hard_negative",
                "mean_r_among_hard_negatives",
            ],
            "negative_hard_structure",
        ),
    ]
    out = pd.concat([p for p in pieces if not p.empty], ignore_index=True)
    if not out.empty:
        out["interpretation_hint"] = out.apply(interpret_split3_row, axis=1)
    return out


def interpret_split3_row(row: pd.Series) -> str:
    metric = str(row["metric"])
    delta = float(row["split3_minus_other_splits_mean"])
    if "score" in metric or "reliability" in metric or "similarity" in metric:
        if delta < -0.02:
            return "split3_lower_than_other_splits"
        if delta > 0.02:
            return "split3_higher_than_other_splits"
    if "pct_positive_pairs_r_lt" in metric or "hard_negative" in metric:
        if delta > 0.02:
            return "split3_harder_than_other_splits"
        if delta < -0.02:
            return "split3_easier_than_other_splits"
    return "similar_to_other_splits"


def find_metric_files() -> list[Path]:
    roots = [PROJECT_ROOT / "outputs/czechlynx"]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        found.extend(root.rglob("*retrieval_metrics*.csv"))
    return sorted(found)


def load_optional_metrics() -> pd.DataFrame:
    frames = []
    for path in find_metric_files():
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        frame["metric_source_path"] = str(path.relative_to(PROJECT_ROOT))
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def build_correlation_diagnostic(positive_pairs: pd.DataFrame, negative_pairs: pd.DataFrame) -> pd.DataFrame:
    metrics = load_optional_metrics()
    structural = positive_pairs.merge(
        negative_pairs,
        on=["split_id", "group_name"],
        how="outer",
        suffixes=("_positive", "_negative"),
    )
    if metrics.empty:
        return pd.DataFrame(
            [
                {
                    "status": "not_computed",
                    "reason": "no_phase11_or_phase11b_retrieval_metrics_found_locally",
                    "n_rows": 0,
                    "method": "pearson_spearman_if_metrics_available",
                    "metric_name": "",
                    "structural_feature": "",
                    "pearson_r": np.nan,
                    "spearman_r": np.nan,
                }
            ]
        )

    group_col = "experiment_group" if "experiment_group" in metrics.columns else "group_name"
    if "split_id" not in metrics.columns or group_col not in metrics.columns:
        return pd.DataFrame(
            [
                {
                    "status": "not_computed",
                    "reason": "retrieval_metrics_missing_split_id_or_group_column",
                    "n_rows": int(len(metrics)),
                    "method": "pearson_spearman_if_metrics_available",
                    "metric_name": "",
                    "structural_feature": "",
                    "pearson_r": np.nan,
                    "spearman_r": np.nan,
                }
            ]
        )
    joined = metrics.merge(
        structural,
        left_on=["split_id", group_col],
        right_on=["split_id", "group_name"],
        how="inner",
    )
    performance_cols = [c for c in ["mAP", "MRR", "top1_accuracy", "top5_accuracy", "false_candidate_burden"] if c in joined.columns]
    feature_cols = [
        "mean_pair_reliability_score",
        "pct_positive_pairs_r_lt_040",
        "hard_negative_count",
        "mean_pattern_pair_score",
        "mean_side_comparability_score",
    ]
    rows = []
    for metric_name in performance_cols:
        for feature in feature_cols:
            sub = joined[[metric_name, feature]].apply(pd.to_numeric, errors="coerce").dropna()
            if len(sub) < 6:
                rows.append(
                    {
                        "status": "not_computed",
                        "reason": "too_few_joined_rows",
                        "n_rows": int(len(sub)),
                        "method": "pearson_spearman_if_metrics_available",
                        "metric_name": metric_name,
                        "structural_feature": feature,
                        "pearson_r": np.nan,
                        "spearman_r": np.nan,
                    }
                )
            else:
                rows.append(
                    {
                        "status": "computed_exploratory",
                        "reason": "small_group_split_level_sample",
                        "n_rows": int(len(sub)),
                        "method": "pearson_spearman",
                        "metric_name": metric_name,
                        "structural_feature": feature,
                        "pearson_r": float(sub[metric_name].corr(sub[feature], method="pearson")),
                        "spearman_r": float(sub[metric_name].corr(sub[feature], method="spearman")),
                    }
                )
    return pd.DataFrame(rows)


def write_report(
    overlap: pd.DataFrame,
    image_quality: pd.DataFrame,
    positive_pairs: pd.DataFrame,
    negative_pairs: pd.DataFrame,
    split3: pd.DataFrame,
    correlations: pd.DataFrame,
) -> None:
    c3_h3_overlap = float(overlap["shared_image_pct_of_c3"].mean())
    c3_pf = float(overlap["c3_mean_pf_eri_image_score"].mean())
    h3_pf = float(overlap["h3_mean_pf_eri_image_score"].mean())
    c3_quality = float(overlap["c3_mean_quality_proxy_score"].mean())
    h3_quality = float(overlap["h3_mean_quality_proxy_score"].mean())
    split3_h3_positive = positive_pairs[
        (positive_pairs["split_id"].astype(int) == 3) & (positive_pairs["group_name"].astype(str) == H3)
    ]
    split3_c3_positive = positive_pairs[
        (positive_pairs["split_id"].astype(int) == 3) & (positive_pairs["group_name"].astype(str) == C3)
    ]
    h3_split3_r = float(split3_h3_positive["mean_pair_reliability_score"].iloc[0]) if not split3_h3_positive.empty else float("nan")
    c3_split3_r = float(split3_c3_positive["mean_pair_reliability_score"].iloc[0]) if not split3_c3_positive.empty else float("nan")

    lines = [
        "# Phase 11C Split-Level Diagnostic Report",
        "",
        "## Scope",
        "",
        "This report diagnoses split-level evidence structure for Phase 11C PF-ERI metric-learning experiments. It does not train a model and does not make a scientific-success claim.",
        "",
        "## Main Diagnostic Findings",
        "",
        f"- Mean C3/H3 image overlap as a fraction of C3: `{c3_h3_overlap:.3f}`.",
        f"- Mean PF-ERI image score: C3 `{c3_pf:.3f}`, H3 `{h3_pf:.3f}`.",
        f"- Mean quality-proxy score: C3 `{c3_quality:.3f}`, H3 `{h3_quality:.3f}`.",
        f"- Split 3 mean positive-pair R: C3 `{c3_split3_r:.3f}`, H3 `{h3_split3_r:.3f}`.",
        "",
        "## Likely Bottlenecks",
        "",
    ]
    if c3_quality > h3_quality + 0.01:
        lines.append("- C3 appears stronger on the quality-proxy axis, so H3-base weighting may face an image-set ceiling.")
    elif h3_quality > c3_quality + 0.01:
        lines.append("- H3 appears stronger on the quality-proxy axis; C3 superiority is not explained by simple image quality.")
    else:
        lines.append("- C3 and H3 have similar mean quality-proxy scores; differences may be pair-level rather than image-level.")
    if h3_split3_r < float(positive_pairs[positive_pairs["group_name"].astype(str) == H3]["mean_pair_reliability_score"].mean()) - 0.02:
        lines.append("- H3 split 3 has lower positive-pair reliability than the H3 average, consistent with split-specific instability.")
    else:
        lines.append("- H3 split 3 does not show a large positive-pair reliability drop by mean R alone.")
    hard_rows = split3[
        (split3["diagnostic_family"] == "negative_hard_structure")
        & (split3["metric"].isin(["hard_negative_count", "pct_hard_negative"]))
        & (split3["interpretation_hint"] == "split3_harder_than_other_splits")
    ]
    if not hard_rows.empty:
        lines.append("- Split 3 shows harder negative-pair structure for at least one group.")
    else:
        lines.append("- Split 3 is not consistently harder by hard-negative count/proportion alone.")
    lines.extend(
        [
            "",
            "## R Calibration Check",
            "",
            "The diagnostics do not prove that R is calibrated. They check whether R distribution and component structure differ by split/group. If training results remain unstable when structural diagnostics look similar, R formula recalibration should be prioritized.",
            "",
            "## Metric Correlation Diagnostic",
            "",
        ]
    )
    if correlations["status"].astype(str).eq("not_computed").all():
        reason = str(correlations["reason"].iloc[0])
        lines.append(f"- Correlations were not computed: `{reason}`.")
    else:
        lines.append("- Correlations were computed as exploratory group/split-level associations only.")
    lines.extend(
        [
            "",
            "## Recommendations For Phase 11C",
            "",
            "1. Prioritize C3-base weighting if C3 image-quality and overlap diagnostics confirm a stronger base image set.",
            "2. Continue parameterized positive-pair transforms if split 3 has low positive-pair reliability or excessive low-R positives.",
            "3. Recalibrate the R formula if split-level failures persist despite similar C3/H3 image quality and pair-reliability structure.",
            "4. Do not redesign negative controls unless hard-negative diagnostics show split-specific high-similarity negative burden.",
            "",
            "## Claim Boundary",
            "",
            "These diagnostics identify possible bottlenecks. They do not show that PF-ERI improves metric learning, do not identify animals, and do not validate field deployment.",
        ]
    )
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest, pair_table, visual, _embeddings, audit = read_inputs()
    enriched = enrich_manifest(manifest, visual)

    overlap = build_image_set_overlap(enriched)
    image_quality = build_image_quality_distribution(enriched)
    positive_pairs = summarize_positive_pairs(pair_table)
    negative_pairs = summarize_negative_pairs(pair_table)
    split3 = build_split3_diagnostic(image_quality, positive_pairs, negative_pairs)
    correlations = build_correlation_diagnostic(positive_pairs, negative_pairs)

    overlap.to_csv(OUT_FILES["image_set_overlap"], index=False)
    image_quality.to_csv(OUT_FILES["image_quality"], index=False)
    positive_pairs.to_csv(OUT_FILES["positive_pairs"], index=False)
    negative_pairs.to_csv(OUT_FILES["negative_pairs"], index=False)
    split3.to_csv(OUT_FILES["split3"], index=False)
    correlations.to_csv(OUT_FILES["correlations"], index=False)
    OUT_FILES["field_audit"].write_text(json.dumps(audit, indent=2), encoding="utf-8")
    write_report(overlap, image_quality, positive_pairs, negative_pairs, split3, correlations)

    for key, path in OUT_FILES.items():
        if key == "field_audit":
            continue
        frame = pd.read_csv(path)
        print(f"wrote {path.relative_to(PROJECT_ROOT)} rows={len(frame)} cols={len(frame.columns)}")
    print(f"wrote {DOC_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
