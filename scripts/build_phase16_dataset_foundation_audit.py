#!/usr/bin/env python3
"""Audit whether the Phase 14 2x2 image foundation is ready for modeling.

This script does not relabel the dataset. It provides a conservative
dataset-readiness diagnostic so that later PF-ERI, strong-model, and
wild-vs-urban analyses do not rest on unchecked image-set assumptions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_INPUT = PROJECT_ROOT / "outputs/phase14/phase14_algorithm_inputs/phase14_2x2_image_evidence_table.csv"
DESCRIPTOR_INPUT = PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embedding_package/phase14_2x2_descriptor_embedding_manifest.csv"
EMBEDDING_INPUT = PROJECT_ROOT / "outputs/phase14/phase14_descriptor_embeddings/phase14_2x2_megadescriptor_embeddings.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/dataset_foundation_audit"
SUMMARY_CSV = OUTPUT_DIR / "phase16_dataset_foundation_quadrant_summary.csv"
ISSUE_CSV = OUTPUT_DIR / "phase16_dataset_foundation_issue_detail.csv"
AUDIT_CANDIDATES_CSV = OUTPUT_DIR / "phase16_dataset_foundation_manual_audit_candidates.csv"
REPORT_MD = OUTPUT_DIR / "phase16_dataset_foundation_audit_report_cn.md"
AUDIT_JSON = OUTPUT_DIR / "phase16_dataset_foundation_audit.json"

EXPECTED_ROWS_PER_QUADRANT = 3000
AUDIT_SAMPLE_PER_QUADRANT = 150
RANDOM_SEED = 1602


def _as_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _as_lower(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower()


def high_evidence_proxy_pass(row: pd.Series) -> bool:
    """Conservative automatic proxy for high-confidence Re-ID evidence."""
    return (
        str(row.get("image_exists", "")).lower() == "yes"
        and str(row.get("md_detected", "")).lower() == "yes"
        and float(row.get("md_best_confidence") or 0) >= 0.80
        and float(row.get("md_area_fraction") or 0) >= 0.08
        and float(row.get("md_width_fraction") or 0) >= 0.18
        and float(row.get("md_height_fraction") or 0) >= 0.18
        and str(row.get("md_edge_touch", "")).lower() != "yes"
        and float(row.get("image_evidence_utility_score") or 0) >= 0.70
        and str(row.get("human_review_bucket", "")).lower() == "review_ready"
        and str(row.get("human_review_confidence", "")).lower() == "high"
    )


def low_evidence_proxy_pass(row: pd.Series) -> bool:
    """Conservative automatic proxy for true low-evidence stress samples."""
    high_like = (
        str(row.get("image_exists", "")).lower() == "yes"
        and str(row.get("md_detected", "")).lower() == "yes"
        and float(row.get("md_best_confidence") or 0) >= 0.80
        and float(row.get("md_area_fraction") or 0) >= 0.08
        and str(row.get("md_edge_touch", "")).lower() != "yes"
        and float(row.get("image_evidence_utility_score") or 0) >= 0.70
        and str(row.get("human_review_bucket", "")).lower() == "review_ready"
    )
    stress_signal = (
        float(row.get("image_evidence_utility_score") or 0) <= 0.50
        or float(row.get("md_area_fraction") or 0) < 0.06
        or str(row.get("md_edge_touch", "")).lower() == "yes"
        or str(row.get("human_review_bucket", "")).lower()
        in {"species_level_only", "uncertain"}
    )
    return str(row.get("image_exists", "")).lower() == "yes" and stress_signal and not high_like


def issue_flags(row: pd.Series) -> list[str]:
    flags: list[str] = []
    evidence_axis = str(row.get("evidence_axis", "")).lower()
    image_exists = str(row.get("image_exists", "")).lower() == "yes"
    md_detected = str(row.get("md_detected", "")).lower() == "yes"
    md_conf = float(row.get("md_best_confidence") or 0)
    md_area = float(row.get("md_area_fraction") or 0)
    md_width = float(row.get("md_width_fraction") or 0)
    md_height = float(row.get("md_height_fraction") or 0)
    utility = float(row.get("image_evidence_utility_score") or 0)
    review_bucket = str(row.get("human_review_bucket", "")).lower()
    review_confidence = str(row.get("human_review_confidence", "")).lower()
    edge_touch = str(row.get("md_edge_touch", "")).lower() == "yes"

    if not image_exists:
        flags.append("missing_image")
    if not md_detected:
        flags.append("no_detector_confirmation")
    if md_detected and md_conf < 0.80:
        flags.append("low_detector_confidence")
    if md_detected and md_area < 0.03:
        flags.append("animal_tiny")
    elif md_detected and md_area < 0.08:
        flags.append("animal_small_for_high_evidence")
    if md_detected and (md_width < 0.18 or md_height < 0.18):
        flags.append("insufficient_bbox_span")
    if edge_touch:
        flags.append("edge_touch_or_crop_risk")
    if evidence_axis == "high_confidence":
        if not high_evidence_proxy_pass(row):
            flags.append("high_confidence_proxy_fail")
        if review_bucket != "review_ready":
            flags.append("high_confidence_not_review_ready")
        if review_confidence != "high":
            flags.append("high_confidence_not_high_label_confidence")
        if utility < 0.70:
            flags.append("high_confidence_low_utility")
    elif evidence_axis == "low_evidence_stress":
        if not low_evidence_proxy_pass(row):
            flags.append("low_evidence_proxy_fail")
        if high_evidence_proxy_pass(row) or (
            review_bucket == "review_ready" and utility >= 0.70 and md_area >= 0.08
        ):
            flags.append("stress_set_contains_high_like_evidence")
    else:
        flags.append("unknown_evidence_axis")
    return flags


def readiness_status(row: pd.Series) -> str:
    evidence_axis = str(row.get("evidence_axis", "")).lower()
    if row["image_missing_rate"] > 0:
        return "fail_missing_images"
    if row["duplicate_path_rate"] > 0:
        return "fail_duplicate_paths"
    if row["row_count"] != EXPECTED_ROWS_PER_QUADRANT:
        return "review_count_mismatch"
    if evidence_axis == "high_confidence":
        if row["proxy_pass_rate"] >= 0.90 and row["manual_audit_needed_rate"] <= 0.10:
            return "pass_for_core_modeling_with_spot_audit"
        if row["proxy_pass_rate"] >= 0.75:
            return "conditional_targeted_manual_audit"
        return "not_ready_rebuild_or_topup_required"
    if evidence_axis == "low_evidence_stress":
        if row["proxy_pass_rate"] >= 0.90 and row["high_like_contamination_rate"] <= 0.05:
            return "pass_for_stress_testing_with_spot_audit"
        if row["proxy_pass_rate"] >= 0.75 and row["high_like_contamination_rate"] <= 0.15:
            return "conditional_targeted_manual_audit"
        return "not_ready_rebuild_or_topup_required"
    return "review_unknown_axis"


def build_audit_table(
    images: pd.DataFrame,
    descriptors: pd.DataFrame,
    embeddings: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "phase14_image_evidence_id",
        "source_quadrant",
        "environment_axis",
        "species_axis",
        "evidence_axis",
        "image_key",
        "image_path",
        "image_exists",
        "manual_audit_needed",
        "human_review_bucket",
        "human_review_confidence",
        "md_detected",
        "md_best_confidence",
        "md_area_fraction",
        "md_width_fraction",
        "md_height_fraction",
        "md_edge_touch",
        "image_evidence_utility_score",
    }
    missing = sorted(required - set(images.columns))
    if missing:
        raise ValueError(f"Missing required image evidence columns: {missing}")

    df = images.copy()
    numeric_columns = [
        "md_best_confidence",
        "md_area_fraction",
        "md_width_fraction",
        "md_height_fraction",
        "image_evidence_utility_score",
        "image_evidence_risk_score",
        "label_prior_score",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = _as_number(df[column])

    descriptor_cols = ["phase14_image_evidence_id", "descriptor_extraction_status"]
    if set(descriptor_cols).issubset(descriptors.columns):
        df = df.merge(
            descriptors[descriptor_cols].drop_duplicates("phase14_image_evidence_id"),
            on="phase14_image_evidence_id",
            how="left",
        )
    else:
        df["descriptor_extraction_status"] = ""
    if "phase14_image_evidence_id" in embeddings.columns:
        embedded_ids = set(embeddings["phase14_image_evidence_id"].dropna().astype(str))
        df["phase16_embedding_available"] = (
            df["phase14_image_evidence_id"].astype(str).isin(embedded_ids)
        )
    else:
        df["phase16_embedding_available"] = False

    df["phase16_high_evidence_proxy_pass"] = df.apply(high_evidence_proxy_pass, axis=1)
    df["phase16_low_evidence_proxy_pass"] = df.apply(low_evidence_proxy_pass, axis=1)
    df["phase16_foundation_issue_flags"] = df.apply(
        lambda row: "|".join(issue_flags(row)) or "none",
        axis=1,
    )
    df["phase16_foundation_issue_count"] = df["phase16_foundation_issue_flags"].map(
        lambda value: 0 if value == "none" else len(str(value).split("|"))
    )
    df["phase16_proxy_pass"] = [
        high if axis == "high_confidence" else low
        for axis, high, low in zip(
            _as_lower(df["evidence_axis"]),
            df["phase16_high_evidence_proxy_pass"],
            df["phase16_low_evidence_proxy_pass"],
        )
    ]
    df["phase16_high_like_in_stress"] = (
        _as_lower(df["evidence_axis"]).eq("low_evidence_stress")
        & (
            df["phase16_high_evidence_proxy_pass"]
            | (
                _as_lower(df["human_review_bucket"]).eq("review_ready")
                & (df["image_evidence_utility_score"] >= 0.70)
                & (df["md_area_fraction"] >= 0.08)
            )
        )
    )
    return df


def summarize(audit: pd.DataFrame) -> pd.DataFrame:
    audit = audit.copy()
    audit["image_missing"] = ~_as_lower(audit["image_exists"]).eq("yes")
    audit["manual_audit_needed_bool"] = _as_lower(audit["manual_audit_needed"]).isin(
        {"yes", "true", "audit_sample_required_before_final_claim", "unknown"}
    )
    audit["descriptor_available"] = audit["phase16_embedding_available"].astype(bool)
    audit["duplicate_path"] = audit.duplicated("image_path", keep=False)
    group_cols = ["source_quadrant", "environment_axis", "species_axis", "evidence_axis"]
    summary = (
        audit.groupby(group_cols, dropna=False)
        .agg(
            row_count=("phase14_image_evidence_id", "count"),
            unique_image_paths=("image_path", "nunique"),
            duplicate_path_count=("duplicate_path", "sum"),
            image_missing_rate=("image_missing", "mean"),
            descriptor_available_rate=("descriptor_available", "mean"),
            manual_audit_needed_rate=("manual_audit_needed_bool", "mean"),
            proxy_pass_rate=("phase16_proxy_pass", "mean"),
            high_proxy_pass_rate=("phase16_high_evidence_proxy_pass", "mean"),
            low_proxy_pass_rate=("phase16_low_evidence_proxy_pass", "mean"),
            high_like_contamination_rate=("phase16_high_like_in_stress", "mean"),
            median_md_confidence=("md_best_confidence", "median"),
            median_md_area_fraction=("md_area_fraction", "median"),
            median_utility=("image_evidence_utility_score", "median"),
            p10_utility=("image_evidence_utility_score", lambda s: s.quantile(0.10)),
            p90_utility=("image_evidence_utility_score", lambda s: s.quantile(0.90)),
            issue_row_rate=("phase16_foundation_issue_count", lambda s: (s > 0).mean()),
            mean_issue_count=("phase16_foundation_issue_count", "mean"),
        )
        .reset_index()
    )
    summary["duplicate_path_rate"] = summary["duplicate_path_count"] / summary["row_count"]
    summary["phase16_dataset_foundation_status"] = summary.apply(readiness_status, axis=1)
    ordered = [
        "source_quadrant",
        "environment_axis",
        "species_axis",
        "evidence_axis",
        "phase16_dataset_foundation_status",
        "row_count",
        "unique_image_paths",
        "duplicate_path_count",
        "duplicate_path_rate",
        "image_missing_rate",
        "descriptor_available_rate",
        "manual_audit_needed_rate",
        "proxy_pass_rate",
        "high_proxy_pass_rate",
        "low_proxy_pass_rate",
        "high_like_contamination_rate",
        "median_md_confidence",
        "median_md_area_fraction",
        "median_utility",
        "p10_utility",
        "p90_utility",
        "issue_row_rate",
        "mean_issue_count",
    ]
    return summary[ordered]


def select_manual_audit_candidates(audit: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [
        "phase14_image_evidence_id",
        "source_quadrant",
        "environment_axis",
        "species_axis",
        "evidence_axis",
        "image_key",
        "image_path",
        "human_review_bucket",
        "human_review_confidence",
        "md_best_confidence",
        "md_area_fraction",
        "md_width_fraction",
        "md_height_fraction",
        "md_edge_touch",
        "image_evidence_utility_score",
        "descriptor_extraction_status",
        "phase16_embedding_available",
        "phase16_foundation_issue_flags",
        "phase16_foundation_issue_count",
    ]
    groups = []
    for quadrant, group in audit.groupby("source_quadrant", sort=True):
        prioritized = group.sort_values(
            [
                "phase16_foundation_issue_count",
                "image_evidence_utility_score",
                "md_area_fraction",
            ],
            ascending=[False, True, True],
        )
        issue_rows = prioritized[prioritized["phase16_foundation_issue_count"] > 0]
        n_issue = min(len(issue_rows), int(AUDIT_SAMPLE_PER_QUADRANT * 0.8))
        selected = issue_rows.head(n_issue)
        remaining_n = AUDIT_SAMPLE_PER_QUADRANT - len(selected)
        if remaining_n > 0:
            remaining = group.drop(index=selected.index, errors="ignore")
            selected = pd.concat(
                [
                    selected,
                    remaining.sample(
                        n=min(remaining_n, len(remaining)),
                        random_state=RANDOM_SEED,
                    ),
                ],
                ignore_index=False,
            )
        groups.append(selected)
    out = pd.concat(groups, ignore_index=True)
    out = out.sort_values(["source_quadrant", "phase16_foundation_issue_count"], ascending=[True, False])
    out.insert(0, "phase16_foundation_audit_index", range(1, len(out) + 1))
    out["manual_foundation_bucket"] = ""
    out["manual_laterality"] = ""
    out["manual_pattern_visibility"] = ""
    out["manual_reid_usable"] = ""
    out["manual_review_confidence"] = ""
    out["manual_notes"] = ""
    return out[["phase16_foundation_audit_index", *keep_cols,
                "manual_foundation_bucket", "manual_laterality",
                "manual_pattern_visibility", "manual_reid_usable",
                "manual_review_confidence", "manual_notes"]]


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Render a small dataframe as GitHub-flavored Markdown without tabulate."""
    if df.empty:
        return "_No rows._"
    display = df.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(
                lambda value: "" if pd.isna(value) else f"{value:.4f}"
            )
        else:
            display[column] = display[column].fillna("").astype(str)
    headers = list(display.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in display.iterrows():
        values = [str(row[column]).replace("\n", " ") for column in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(summary: pd.DataFrame, audit: pd.DataFrame) -> None:
    not_ready = summary[
        summary["phase16_dataset_foundation_status"].str.startswith("not_ready")
    ]
    conditional = summary[
        summary["phase16_dataset_foundation_status"].str.startswith("conditional")
    ]
    report = [
        "# Phase 16 Dataset Foundation Audit Report",
        "",
        "## 结论",
        "",
        "这份报告检查当前 3000 x 4 影像基础是否足以支撑后续 PF-ERI、strong-model benchmark 和 wild-vs-urban 对比。它不是最终人工标签，也不会修改原始标签；它是一个保守的数据根基风险审计。",
        "",
        "关键原则：如果 high-confidence precision 或 low-evidence stress purity 不够，应该 targeted top-up 或人工复核，而不是放松规则或直接进入模型主结果。",
        "",
        "## Quadrant Readiness",
        "",
        dataframe_to_markdown(summary),
        "",
        "## 自动审计解释",
        "",
        "- high-confidence proxy pass 要求：图像存在、MegaDetector 确认、检测置信度和框大小足够、非明显边缘裁切、utility 足够高、当前标签为 review_ready/high。",
        "- low-evidence stress proxy pass 要求：图像存在，并且具有小目标、边缘裁切、低 utility、species-level/uncertain 等低证据压力信号，同时不能像 clear review-ready high-evidence 图。",
        "- 这些 proxy 是风险筛查，不是人工真值；失败样本进入人工审计候选，不自动删除。",
        "",
        "## 当前行动建议",
        "",
    ]
    if len(not_ready):
        report.append("至少一个 quadrant 被标记为 `not_ready_rebuild_or_topup_required`。下一步应优先人工复核候选表，并针对失败原因补图或重筛。")
    elif len(conditional):
        report.append("至少一个 quadrant 处于 conditional 状态。下一步应先复核候选表，再决定是否 targeted top-up。")
    else:
        report.append("四个 quadrant 均达到自动审计通过或接近通过状态。下一步可以进入 strong-model benchmark，同时保留 spot audit。")
    report.extend(
        [
            "",
            "## 输出文件",
            "",
            f"- quadrant summary: `{SUMMARY_CSV}`",
            f"- issue detail: `{ISSUE_CSV}`",
            f"- manual audit candidates: `{AUDIT_CANDIDATES_CSV}`",
            "",
            "## Claim Boundary",
            "",
            "这份审计只能说明数据基础风险和人工复核优先级，不能替代专家人工标签，不能直接证明模型性能，也不能证明 urbanization 因果影响。",
            "",
        ]
    )
    REPORT_MD.write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    images = pd.read_csv(IMAGE_INPUT, low_memory=False)
    descriptors = pd.read_csv(DESCRIPTOR_INPUT, low_memory=False)
    embeddings = pd.read_csv(EMBEDDING_INPUT, usecols=["phase14_image_evidence_id"])
    audit = build_audit_table(images, descriptors, embeddings)
    summary = summarize(audit)
    issues = audit[audit["phase16_foundation_issue_count"] > 0].copy()
    candidates = select_manual_audit_candidates(audit)

    summary.to_csv(SUMMARY_CSV, index=False)
    issues.to_csv(ISSUE_CSV, index=False)
    candidates.to_csv(AUDIT_CANDIDATES_CSV, index=False)
    write_report(summary, audit)

    audit_payload = {
        "image_input": str(IMAGE_INPUT),
        "descriptor_input": str(DESCRIPTOR_INPUT),
        "embedding_input": str(EMBEDDING_INPUT),
        "summary_csv": str(SUMMARY_CSV),
        "issue_csv": str(ISSUE_CSV),
        "manual_audit_candidates_csv": str(AUDIT_CANDIDATES_CSV),
        "report_md": str(REPORT_MD),
        "rows": int(len(audit)),
        "expected_rows_per_quadrant": EXPECTED_ROWS_PER_QUADRANT,
        "audit_sample_per_quadrant": AUDIT_SAMPLE_PER_QUADRANT,
        "quadrants": summary.to_dict(orient="records"),
        "claim_boundary": (
            "dataset foundation diagnostic only; does not replace manual labels "
            "or final model validation"
        ),
    }
    AUDIT_JSON.write_text(json.dumps(audit_payload, indent=2), encoding="utf-8")
    print(f"PASS phase16 dataset foundation audit rows={len(audit)}")
    print(f"WROTE {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
