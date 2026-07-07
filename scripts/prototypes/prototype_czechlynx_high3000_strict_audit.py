#!/usr/bin/env python3
"""PROTOTYPE: strict CzechLynx high-confidence 3000 audit.

Question:
Do the CzechLynx high-confidence 3000 sets still pass the same clarity-first
standard we used for Bobcat final entry?

This is throwaway audit code. It does not change the CzechLynx selection; it
emits pass/fail diagnostics and review queues for human follow-up.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase17_strict_high3000_audit"

PRIMARY_HIGH_3000 = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_high_confidence_3000_working_final_labels.csv"
)
STRICT_2X2_HIGH_3000 = (
    PROJECT_ROOT
    / "outputs/phase14/phase14_strict_2x2_evidence_sets/phase14_strict_2x2_czechlynx_high_confidence_3000.csv"
)
PHASE16F_SELECTED_3000 = (
    PROJECT_ROOT
    / "outputs/phase16/phase16f_czechlynx_constrained_selection/phase16f_czechlynx_selected_3000_manifest.csv"
)
PHASE16E_SCORES = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_candidate_model_filter/phase16e_czechlynx_scores_00000_39759_merged.csv"
)


def safe_float(value: Any) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def safe_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def normalize_key(value: Any) -> str:
    key = str(value or "").strip().replace("\\", "/")
    marker = "CzechLynx/"
    if marker in key:
        return key.split(marker, 1)[1].join(["CzechLynx/", ""])
    return key


def coalesce_columns(df: pd.DataFrame, preferred: str, fallback: str) -> None:
    if preferred not in df.columns and fallback in df.columns:
        df[preferred] = df[fallback]
    elif preferred in df.columns and fallback in df.columns:
        df[preferred] = df[preferred].where(df[preferred].notna(), df[fallback])


def primary_lookup() -> pd.DataFrame:
    primary = read_csv(PRIMARY_HIGH_3000)
    key_columns = ["path", "local_image_path", "review_image_path_local", "candidate_source_path"]
    rows = []
    keep_columns = [
        "image_width",
        "image_height",
        "original_image_width",
        "original_image_height",
        "contrast_std",
        "blur_laplacian_var",
        "edge_density",
        "auto_blur_band",
        "auto_night_ir",
        "auto_exposure_band",
        "human_blur_level",
        "human_occlusion_level",
        "human_body_visibility",
        "md_best_confidence",
        "md_area_fraction",
        "md_width_fraction",
        "md_height_fraction",
        "md_edge_touch",
    ]
    keep_columns = [column for column in keep_columns if column in primary.columns]
    for column in key_columns:
        if column not in primary.columns:
            continue
        part = primary[[column, *keep_columns]].copy()
        part["audit_lookup_key"] = part[column].map(normalize_key)
        part = part[part["audit_lookup_key"].ne("")]
        rows.append(part.drop(columns=[column]))
    if not rows:
        return pd.DataFrame(columns=["audit_lookup_key"])
    lookup = pd.concat(rows, ignore_index=True)
    return lookup.drop_duplicates("audit_lookup_key", keep="first")


def enrich_from_primary_lookup(df: pd.DataFrame) -> pd.DataFrame:
    lookup = primary_lookup()
    if lookup.empty:
        return df
    out = df.copy()
    candidate_keys = []
    for _, row in out.iterrows():
        key = ""
        for column in ["image_key", "path", "local_image_path", "review_image_path_local", "candidate_source_path"]:
            if column in out.columns and str(row.get(column, "")).strip():
                key = normalize_key(row.get(column, ""))
                break
        candidate_keys.append(key)
    out["audit_lookup_key"] = candidate_keys
    out = out.merge(lookup, on="audit_lookup_key", how="left", suffixes=("", "_from_primary"))
    for column in lookup.columns:
        if column == "audit_lookup_key":
            continue
        fallback = f"{column}_from_primary"
        if fallback in out.columns:
            coalesce_columns(out, column, fallback)
    return out


def prepare_phase16f() -> pd.DataFrame:
    selected = read_csv(PHASE16F_SELECTED_3000)
    scores = read_csv(PHASE16E_SCORES)
    geometry_cols = [
        "candidate_id",
        "image_key",
        "local_path_original",
        "md_best_confidence",
        "md_area_fraction",
        "md_width_fraction",
        "md_height_fraction",
        "md_edge_touch",
        "iqa_quality_proxy_score",
        "clip_viewpoint_prob_partial_or_occluded",
        "clip_viewpoint_prob_unclear",
    ]
    available = [col for col in geometry_cols if col in scores.columns]
    merged = selected.merge(scores[available], on="candidate_id", how="left", suffixes=("", "_phase16e"))
    coalesce_columns(merged, "image_key", "image_key_phase16e")
    return enrich_from_primary_lookup(merged)


def add_common_identity(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    out = df.copy()
    out["audit_dataset"] = dataset_name
    if "candidate_id" not in out.columns:
        if "expanded_image_id" in out.columns:
            out["candidate_id"] = out["expanded_image_id"]
        elif "image_id" in out.columns:
            out["candidate_id"] = out["image_id"]
        else:
            out["candidate_id"] = [f"{dataset_name}_{idx:06d}" for idx in range(len(out))]
    if "image_key" not in out.columns:
        for col in ["path", "local_image_path", "review_image_path_local", "candidate_source_path"]:
            if col in out.columns:
                out["image_key"] = out[col]
                break
    out["audit_image_key"] = out.get("image_key", pd.Series("", index=out.index)).map(normalize_key)
    if "identity_label" in out.columns:
        out["audit_identity_label"] = out["identity_label"]
    elif "phase16f_balance_group" in out.columns:
        out["audit_identity_label"] = out["phase16f_balance_group"]
    else:
        out["audit_identity_label"] = ""
    return out


def numeric(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(0.0, index=df.index)
    return pd.to_numeric(df[column], errors="coerce").fillna(0.0)


def text(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series("", index=df.index)
    return df[column].fillna("").astype(str).str.strip().str.lower()


def audit_frame(df: pd.DataFrame, dataset_name: str, args: argparse.Namespace) -> pd.DataFrame:
    out = add_common_identity(df, dataset_name)
    width = numeric(out, "image_width").where(numeric(out, "image_width").gt(0), numeric(out, "original_image_width"))
    height = numeric(out, "image_height").where(numeric(out, "image_height").gt(0), numeric(out, "original_image_height"))
    md_width_px = numeric(out, "md_width_fraction") * width
    md_height_px = numeric(out, "md_height_fraction") * height
    out["audit_md_bbox_short_side_px"] = pd.concat([md_width_px, md_height_px], axis=1).min(axis=1)
    out["audit_md_bbox_area_fraction"] = numeric(out, "md_area_fraction")
    out["audit_md_confidence"] = numeric(out, "md_best_confidence")
    out["audit_has_detector_geometry"] = out["audit_md_bbox_short_side_px"].gt(0) & out["audit_md_bbox_area_fraction"].gt(0)

    contrast = numeric(out, "contrast_std")
    laplacian = numeric(out, "blur_laplacian_var")
    edge_density = numeric(out, "edge_density")
    iqa_quality = numeric(out, "iqa_quality_proxy_score")
    partial_prob = numeric(out, "clip_viewpoint_prob_partial_or_occluded")
    unclear_prob = numeric(out, "clip_viewpoint_prob_unclear")

    reasons: list[list[str]] = [[] for _ in range(len(out))]

    def add_reason(mask: pd.Series, reason: str) -> None:
        for idx in out.index[mask.fillna(False)]:
            reasons[out.index.get_loc(idx)].append(reason)

    add_reason(~out["audit_has_detector_geometry"], "missing_detector_geometry")
    add_reason(out["audit_md_confidence"].lt(args.min_detector_conf), "low_detector_confidence")
    add_reason(out["audit_md_bbox_short_side_px"].lt(args.min_bbox_short_side), "bbox_short_side_lt_224px")
    add_reason(out["audit_md_bbox_area_fraction"].lt(args.min_bbox_area), "bbox_area_lt_10pct")
    if "md_edge_touch" in out.columns:
        add_reason(out["md_edge_touch"].map(safe_bool), "detector_edge_touch_partial_body_risk")
    add_reason(contrast.lt(args.min_contrast), "low_contrast")
    add_reason(laplacian.lt(args.min_laplacian), "low_sharpness")
    add_reason(edge_density.lt(args.min_edge_density), "weak_edges_or_mosaic")

    if "auto_blur_band" in out.columns:
        add_reason(~text(out, "auto_blur_band").isin({"none", ""}), "auto_blur_not_none")
    if "auto_night_ir" in out.columns:
        add_reason(text(out, "auto_night_ir").eq("yes"), "night_ir")
    if "auto_exposure_band" in out.columns:
        add_reason(text(out, "auto_exposure_band").eq("poor"), "poor_exposure")
    if "human_blur_level" in out.columns:
        add_reason(~text(out, "human_blur_level").isin({"none", "low", ""}), "human_blur_not_none_or_low")
    if "human_occlusion_level" in out.columns:
        add_reason(~text(out, "human_occlusion_level").isin({"none", "low", ""}), "human_occlusion_not_none_or_low")
    if "human_body_visibility" in out.columns:
        body = text(out, "human_body_visibility")
        add_reason(body.isin({"0_25", "26_50"}), "human_body_visibility_lt_50")
    if "clip_viewpoint_prob_partial_or_occluded" in out.columns:
        add_reason(partial_prob.ge(args.max_partial_prob), "clip_partial_or_occluded_high")
    if "clip_viewpoint_prob_unclear" in out.columns:
        add_reason(unclear_prob.ge(args.max_unclear_prob), "clip_unclear_high")
    if "iqa_quality_proxy_score" in out.columns:
        add_reason(iqa_quality.lt(args.min_iqa_quality_proxy), "low_iqa_quality_proxy")

    out["strict_high3000_audit_reasons"] = ["pass" if not row else "|".join(row) for row in reasons]
    out["strict_high3000_audit_pass"] = [not row for row in reasons]
    out["strict_high3000_gate_rule"] = (
        "detector bbox short side >= 224px, bbox area >= 10%, confidence >= 0.25, "
        "no edge-touch high partial-body risk, contrast/laplacian/edge pass, no blur/night/poor exposure flags"
    )
    return out


def summary_for(df: pd.DataFrame) -> dict[str, Any]:
    reasons = Counter()
    for value in df["strict_high3000_audit_reasons"]:
        if value == "pass":
            continue
        reasons.update(str(value).split("|"))
    return {
        "rows": int(len(df)),
        "pass_rows": int(df["strict_high3000_audit_pass"].sum()),
        "fail_rows": int((~df["strict_high3000_audit_pass"]).sum()),
        "pass_rate": float(df["strict_high3000_audit_pass"].mean()) if len(df) else 0.0,
        "identity_count": int(df["audit_identity_label"].nunique()) if "audit_identity_label" in df.columns else 0,
        "reason_counts": dict(reasons.most_common()),
        "bbox_short_side_quantiles": {
            key: float(value)
            for key, value in df["audit_md_bbox_short_side_px"].quantile([0.01, 0.05, 0.10, 0.50]).to_dict().items()
        },
        "area_fraction_quantiles": {
            key: float(value)
            for key, value in df["audit_md_bbox_area_fraction"].quantile([0.01, 0.05, 0.10, 0.50]).to_dict().items()
        },
    }


def write_outputs(audited: dict[str, pd.DataFrame], args: argparse.Namespace) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summaries: dict[str, Any] = {}
    output_files: dict[str, str] = {}
    for name, frame in audited.items():
        out_csv = OUTPUT_DIR / f"{name}_strict_audit.csv"
        pass_csv = OUTPUT_DIR / f"{name}_strict_pass_manifest.csv"
        fail_csv = OUTPUT_DIR / f"{name}_strict_fail_review_queue.csv"
        frame.to_csv(out_csv, index=False)
        frame[frame["strict_high3000_audit_pass"]].to_csv(pass_csv, index=False)
        frame[~frame["strict_high3000_audit_pass"]].to_csv(fail_csv, index=False)
        summaries[name] = summary_for(frame)
        output_files[f"{name}_audit_csv"] = str(out_csv)
        output_files[f"{name}_strict_pass_manifest_csv"] = str(pass_csv)
        output_files[f"{name}_fail_review_queue_csv"] = str(fail_csv)

    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prototype_question": "Do CzechLynx high-confidence 3000 sets pass the same strict clarity-first standard used for Bobcat final entry?",
        "gate": {
            "min_detector_confidence": args.min_detector_conf,
            "min_bbox_short_side_px": args.min_bbox_short_side,
            "min_bbox_area_fraction": args.min_bbox_area,
            "min_contrast_std": args.min_contrast,
            "min_laplacian_var": args.min_laplacian,
            "min_edge_density": args.min_edge_density,
            "max_clip_partial_or_occluded_prob": args.max_partial_prob,
            "max_clip_unclear_prob": args.max_unclear_prob,
            "min_iqa_quality_proxy_when_available": args.min_iqa_quality_proxy,
        },
        "input_files": {
            "primary_phase14_working_final": str(PRIMARY_HIGH_3000),
            "phase14_strict_2x2": str(STRICT_2X2_HIGH_3000),
            "phase16f_selected_3000": str(PHASE16F_SELECTED_3000),
            "phase16e_scores_for_phase16f_geometry_join": str(PHASE16E_SCORES),
        },
        "summaries": summaries,
        "output_files": output_files,
        "claim_boundary": "Prototype audit only. Failing rows require human inspection or replacement before any final high-confidence freeze.",
    }
    audit_path = OUTPUT_DIR / "phase17_strict_czechlynx_high3000_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = OUTPUT_DIR / "phase17_strict_czechlynx_high3000_audit_report.md"
    lines = [
        "# Phase17 Strict CzechLynx High-3000 Audit",
        "",
        "This prototype applies the Bobcat final-entry clarity principle to CzechLynx high-confidence 3000 sets.",
        "",
        "## Boundary",
        "",
        "This audit does not change the selection. It identifies rows that should be reviewed or replaced before final freeze.",
        "",
        "## Summary",
        "",
    ]
    for name, summary in summaries.items():
        lines += [
            f"### {name}",
            "",
            f"- Rows: {summary['rows']}",
            f"- Strict pass: {summary['pass_rows']}",
            f"- Strict fail/review: {summary['fail_rows']}",
            f"- Pass rate: {summary['pass_rate']:.4f}",
            f"- Identity labels/groups: {summary['identity_count']}",
            f"- Top failure reasons: {summary['reason_counts']}",
            "",
        ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    audit["audit_json"] = str(audit_path)
    audit["report_md"] = str(report_path)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-detector-conf", type=float, default=0.25)
    parser.add_argument("--min-bbox-short-side", type=float, default=224)
    parser.add_argument("--min-bbox-area", type=float, default=0.10)
    parser.add_argument("--min-contrast", type=float, default=42)
    parser.add_argument("--min-laplacian", type=float, default=80)
    parser.add_argument("--min-edge-density", type=float, default=0.05)
    parser.add_argument("--max-partial-prob", type=float, default=0.30)
    parser.add_argument("--max-unclear-prob", type=float, default=0.20)
    parser.add_argument("--min-iqa-quality-proxy", type=float, default=0.45)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audited = {
        "phase14_working_final_high3000": audit_frame(read_csv(PRIMARY_HIGH_3000), "phase14_working_final_high3000", args),
        "phase14_strict_2x2_high3000": audit_frame(
            enrich_from_primary_lookup(read_csv(STRICT_2X2_HIGH_3000)),
            "phase14_strict_2x2_high3000",
            args,
        ),
        "phase16f_selected_high3000": audit_frame(prepare_phase16f(), "phase16f_selected_high3000", args),
    }
    audit = write_outputs(audited, args)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
