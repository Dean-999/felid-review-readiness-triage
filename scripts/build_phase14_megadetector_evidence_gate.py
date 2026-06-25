#!/usr/bin/env python3
"""Run MegaDetector on Phase 14 high-evidence candidates and apply a strict size/crop gate."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CANDIDATES = PROJECT_ROOT / "outputs/phase14/phase14_detector_first_admission/phase14_detector_first_candidate_scores.csv"
OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_megadetector_evidence_gate"


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def candidate_sort_key(frame: pd.DataFrame) -> pd.Series:
    parts = []
    for col, weight in [
        ("prob_high_confidence", 1.0),
        ("auto_evidence_score", 0.02),
        ("auto_quality_score", 0.02),
        ("blur_laplacian_var", 0.0001),
        ("contrast_std", 0.001),
    ]:
        if col in frame.columns:
            parts.append(pd.to_numeric(frame[col], errors="coerce").fillna(0) * weight)
    if not parts:
        return pd.Series(0.0, index=frame.index)
    score = parts[0].copy()
    for part in parts[1:]:
        score = score + part
    return score


def prepare_subset(candidates: pd.DataFrame, max_per_env: int | None, include_middle: bool) -> pd.DataFrame:
    tiers = ["high_confidence"]
    if include_middle:
        tiers.append("middle_reviewable")
    if "strict_evidence_tier" not in candidates.columns:
        raise ValueError("strict_evidence_tier column is required")
    subset = candidates[candidates["strict_evidence_tier"].isin(tiers)].copy()
    subset = subset[subset["evidence_image_path"].notna()].copy()
    subset["md_priority_score"] = candidate_sort_key(subset)
    if max_per_env:
        subset = (
            subset.sort_values(["environment_context", "md_priority_score"], ascending=[True, False])
            .groupby("environment_context", group_keys=False)
            .head(max_per_env)
            .copy()
        )
    subset = subset.drop_duplicates("evidence_image_path").reset_index(drop=True)
    subset["md_subset_id"] = [f"md_{i:06d}" for i in range(len(subset))]
    return subset


def extension_for(path: Path) -> str:
    suffix = path.suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png"} else ".jpg"


def build_symlink_folder(subset: pd.DataFrame, out_dir: Path) -> tuple[Path, pd.DataFrame]:
    image_dir = out_dir / "megadetector_input_high_candidates"
    image_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for _, row in subset.iterrows():
        src = resolve(row["evidence_image_path"])
        link_name = f"{row['md_subset_id']}{extension_for(src)}"
        dst = image_dir / link_name
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        os.symlink(src, dst)
        rows.append(
            {
                "md_subset_id": row["md_subset_id"],
                "megadetector_input_path": str(dst),
                "megadetector_input_name": link_name,
                "evidence_image_path": row["evidence_image_path"],
            }
        )
    mapping = pd.DataFrame(rows)
    mapping.to_csv(out_dir / "phase14_megadetector_input_mapping.csv", index=False)
    return image_dir, mapping


def detection_to_row(result: dict[str, Any]) -> dict[str, Any]:
    detections = result.get("detections")
    coords = result.get("normalized_coords") or []
    img_id = result.get("img_id", "")
    if detections is None or len(getattr(detections, "confidence", [])) == 0 or not coords:
        return {
            "megadetector_input_path": img_id,
            "md_detected": False,
            "md_detection_count": 0,
            "md_best_confidence": 0.0,
        }
    confs = list(map(float, detections.confidence))
    class_ids = list(map(int, detections.class_id))
    best_idx = max(range(len(confs)), key=lambda i: confs[i])
    x0, y0, x1, y1 = [float(v) for v in coords[best_idx]]
    width = max(0.0, x1 - x0)
    height = max(0.0, y1 - y0)
    edge_margin = 0.025
    return {
        "megadetector_input_path": img_id,
        "md_detected": True,
        "md_detection_count": len(confs),
        "md_best_confidence": confs[best_idx],
        "md_best_class_id": class_ids[best_idx],
        "md_x0": x0,
        "md_y0": y0,
        "md_x1": x1,
        "md_y1": y1,
        "md_width_fraction": width,
        "md_height_fraction": height,
        "md_area_fraction": width * height,
        "md_aspect_ratio": width / max(height, 1e-9),
        "md_edge_touch": bool(x0 <= edge_margin or y0 <= edge_margin or x1 >= 1 - edge_margin or y1 >= 1 - edge_margin),
    }


def run_megadetector(image_dir: Path, out_dir: Path, batch_size: int, conf_threshold: float, device: str) -> pd.DataFrame:
    from PytorchWildlife.models import detection as pw_detection

    model = pw_detection.MegaDetectorV5(device=device, pretrained=True)
    results = model.batch_image_detection(str(image_dir), batch_size=batch_size, det_conf_thres=conf_threshold)
    rows = [detection_to_row(result) for result in results]
    frame = pd.DataFrame(rows)
    frame.to_csv(out_dir / "phase14_megadetector_raw_detections.csv", index=False)
    return frame


def gate_high_confidence(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in [
        "md_best_confidence",
        "md_area_fraction",
        "md_width_fraction",
        "md_height_fraction",
        "md_aspect_ratio",
    ]:
        out[col] = pd.to_numeric(out.get(col), errors="coerce").fillna(0)
    out["md_edge_touch"] = out.get("md_edge_touch", False).fillna(False).astype(bool)
    out["md_high_evidence_gate"] = (
        out["md_detected"].fillna(False).astype(bool)
        & out["md_best_confidence"].ge(0.55)
        & out["md_area_fraction"].ge(0.035)
        & out["md_width_fraction"].ge(0.18)
        & out["md_height_fraction"].ge(0.10)
        & out["md_aspect_ratio"].between(0.70, 4.80)
        & ~out["md_edge_touch"]
    )
    reasons = []
    for _, row in out.iterrows():
        bad = []
        if not bool(row.get("md_detected", False)):
            bad.append("no_md_detection")
        if float(row.get("md_best_confidence", 0)) < 0.55:
            bad.append("low_md_confidence")
        if float(row.get("md_area_fraction", 0)) < 0.035:
            bad.append("animal_too_small")
        if float(row.get("md_width_fraction", 0)) < 0.18 or float(row.get("md_height_fraction", 0)) < 0.10:
            bad.append("insufficient_bbox_span")
        if bool(row.get("md_edge_touch", False)):
            bad.append("edge_touch")
        if not (0.70 <= float(row.get("md_aspect_ratio", 0)) <= 4.80):
            bad.append("extreme_aspect_ratio")
        reasons.append("|".join(bad) if bad else "pass")
    out["md_gate_reasons"] = reasons
    out["ai_route_md_gate"] = "human_review_required"
    out.loc[out["md_high_evidence_gate"], "ai_route_md_gate"] = "md_auto_high_confidence"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-candidates", default=str(SOURCE_CANDIDATES))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--max-per-env", type=int, default=4000)
    parser.add_argument("--include-middle", action="store_true")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--det-conf-thres", type=float, default=0.2)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates = pd.read_csv(resolve(args.source_candidates), low_memory=False)
    subset = prepare_subset(candidates, args.max_per_env, args.include_middle)
    subset.to_csv(out_dir / "phase14_megadetector_candidate_subset.csv", index=False)
    image_dir, mapping = build_symlink_folder(subset, out_dir)
    detections = run_megadetector(image_dir, out_dir, args.batch_size, args.det_conf_thres, args.device)
    detections["megadetector_input_name"] = detections["megadetector_input_path"].map(lambda p: Path(str(p)).name)
    merged = subset.merge(mapping[["md_subset_id", "megadetector_input_name"]], on="md_subset_id", how="left")
    merged = merged.merge(detections, on="megadetector_input_name", how="left")
    gated = gate_high_confidence(merged)
    gated.to_csv(out_dir / "phase14_megadetector_high_gate_candidates.csv", index=False)
    for env, name in [("urban_periurban", "urban_bobcat"), ("wild", "wild_czechlynx")]:
        env_frame = gated[gated["environment_context"].eq(env)]
        env_frame[env_frame["md_high_evidence_gate"]].to_csv(
            out_dir / f"phase14_megadetector_{name}_auto_high_candidates.csv",
            index=False,
        )
    gated[~gated["md_high_evidence_gate"]].to_csv(
        out_dir / "phase14_megadetector_high_gate_human_review_required.csv",
        index=False,
    )
    summary = {
        "source_candidates": rel(resolve(args.source_candidates)),
        "candidate_subset_rows": int(len(subset)),
        "max_per_env": args.max_per_env,
        "include_middle": bool(args.include_middle),
        "detector": "PytorchWildlife MegaDetectorV5",
        "det_conf_thres": args.det_conf_thres,
        "gate": {
            "md_best_confidence_min": 0.55,
            "md_area_fraction_min": 0.035,
            "md_width_fraction_min": 0.18,
            "md_height_fraction_min": 0.10,
            "md_aspect_ratio_range": [0.70, 4.80],
            "edge_touch_allowed": False,
        },
        "route_counts": {str(k): int(v) for k, v in gated["ai_route_md_gate"].value_counts().sort_index().items()},
        "environment_route_counts": {
            str(env): {str(k): int(v) for k, v in part["ai_route_md_gate"].value_counts().sort_index().items()}
            for env, part in gated.groupby("environment_context")
        },
        "outputs": {
            "candidate_subset": rel(out_dir / "phase14_megadetector_candidate_subset.csv"),
            "raw_detections": rel(out_dir / "phase14_megadetector_raw_detections.csv"),
            "gated_candidates": rel(out_dir / "phase14_megadetector_high_gate_candidates.csv"),
            "urban_auto_high": rel(out_dir / "phase14_megadetector_urban_bobcat_auto_high_candidates.csv"),
            "wild_auto_high": rel(out_dir / "phase14_megadetector_wild_czechlynx_auto_high_candidates.csv"),
            "human_review": rel(out_dir / "phase14_megadetector_high_gate_human_review_required.csv"),
        },
    }
    (out_dir / "phase14_megadetector_high_gate_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS phase14 megadetector evidence gate "
        f"subset_rows={len(subset)} route_counts={summary['route_counts']} out={rel(out_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
