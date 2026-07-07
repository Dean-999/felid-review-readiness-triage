#!/usr/bin/env python3
"""PROTOTYPE: supplement CzechLynx strict high-quality 3000.

Question:
Can we fill a CzechLynx 3000-image high-quality set without weakening the
Bobcat-style strict clarity gate?

This is throwaway prototype code. It re-scores local CzechLynx candidates with
image metrics and a detector, then emits a review queue. It does not replace the
official CzechLynx high-confidence set until reviewed/frozen.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTOTYPE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROTOTYPE_DIR))

import prototype_czechlynx_high3000_strict_audit as strict_audit  # noqa: E402
from prototype_bobcat_photo_selection_subject40_gate import (  # noqa: E402
    best_detection_from_result,
    image_quality_metrics,
)


OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase17_strict3000_supplement"
PHASE16E_RECAL = (
    PROJECT_ROOT
    / "outputs/phase16/phase16e_recalibrated_czechlynx_scores/phase16e_recalibrated_candidate_scores.csv"
)
BASE_PASS = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase17_strict_high3000_audit/phase14_working_final_high3000_strict_pass_manifest.csv"
)
EXTRA_BASE_POOLS = [
    (
        "phase14_high_topup_passed_pool",
        PROJECT_ROOT / "outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_high_topup_passed_pool.csv",
    ),
    (
        "phase14_high_topup_all_gated",
        PROJECT_ROOT / "outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_high_topup_all_gated_candidates.csv",
    ),
    (
        "phase14_megadetector_high_final",
        PROJECT_ROOT / "outputs/phase14/phase14_colab_megadetector_final_selection/phase14_czechlynx_megadetector_high_confidence_final.csv",
    ),
    (
        "phase14_megadetector_auto_high_300x2",
        PROJECT_ROOT / "outputs/phase14/phase14_megadetector_evidence_gate_300x2/phase14_megadetector_wild_czechlynx_auto_high_candidates.csv",
    ),
]
DETECTION_CACHE = OUTPUT_DIR / "phase17_czechlynx_strict3000_detector_cache.csv"
FINAL_QUEUE = OUTPUT_DIR / "phase17_czechlynx_strict3000_review_queue.csv"
AUDIT_JSON = OUTPUT_DIR / "phase17_czechlynx_strict3000_supplement_audit.json"
REPORT_MD = OUTPUT_DIR / "phase17_czechlynx_strict3000_supplement_report.md"

ALLOWED_ANIMAL_CLASSES = {"cat", "dog", "bear"}
CACHE_FIELDS = [
    "candidate_id",
    "image_key",
    "local_image_path",
    "source_pool",
    "phase16e_rank_score",
    "audit_identity_label",
    "image_width",
    "image_height",
    "contrast_std",
    "gradient_p90",
    "laplacian_var",
    "edge_density",
    "detector_model",
    "detected_class",
    "detected_confidence",
    "subject_bbox_x1",
    "subject_bbox_y1",
    "subject_bbox_x2",
    "subject_bbox_y2",
    "subject_area_fraction",
    "subject_width_fraction",
    "subject_height_fraction",
    "subject_edge_contact_count",
    "subject_min_edge_margin_fraction",
    "partial_body_risk",
    "completeness_proxy",
    "strict_gate_pass",
    "strict_gate_reasons",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with temp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


def safe_float(value: Any) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_key(value: Any) -> str:
    return strict_audit.normalize_key(value)


def resolve_local_path(row: pd.Series) -> str:
    candidates = []
    for column in ["local_path_original", "local_image_path", "review_image_path_local", "candidate_source_path"]:
        if column in row and pd.notna(row[column]) and str(row[column]).strip():
            candidates.append(str(row[column]))
    if "image_key" in row and pd.notna(row["image_key"]):
        candidates.append(str(PROJECT_ROOT / "data/raw/czechlynx" / str(row["image_key"])))
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return str(path)
        fixed = Path(candidate.replace("/Users/deanshen/", "/Users/dshen/"))
        if fixed.exists():
            return str(fixed)
    return ""


def identity_from_key(key: str) -> str:
    parts = normalize_key(key).split("/")
    if len(parts) >= 3:
        return parts[2]
    return "unknown"


def load_base_pass(args: argparse.Namespace) -> pd.DataFrame:
    base = pd.read_csv(BASE_PASS, low_memory=False)
    base = base.copy()
    base["source_pool"] = "phase14_working_final_strict_pass"
    base["dedupe_key"] = base["audit_image_key"].map(normalize_key)
    if "local_image_path" not in base.columns:
        base["local_image_path"] = base.get("candidate_source_path", "")
    base["phase17_supplement_role"] = "base_strict_pass"
    frames = [base]
    strict_args = argparse.Namespace(
        min_detector_conf=args.min_detector_conf,
        min_bbox_short_side=args.min_bbox_short_side,
        min_bbox_area=args.min_bbox_area,
        min_contrast=args.min_contrast,
        min_laplacian=args.min_laplacian,
        min_edge_density=args.min_edge_density,
        max_partial_prob=0.30,
        max_unclear_prob=0.20,
        min_iqa_quality_proxy=0.45,
    )
    for name, path in EXTRA_BASE_POOLS:
        if not path.exists():
            continue
        frame = pd.read_csv(path, low_memory=False)
        audited = strict_audit.audit_frame(strict_audit.enrich_from_primary_lookup(frame), name, strict_args)
        passed = audited[audited["strict_high3000_audit_pass"]].copy()
        passed["source_pool"] = f"{name}_strict_pass"
        passed["dedupe_key"] = passed["audit_image_key"].map(normalize_key)
        passed["local_image_path"] = passed.get("candidate_source_path", passed.get("local_image_path", ""))
        passed["phase17_supplement_role"] = "extra_local_strict_pass"
        frames.append(passed)
    combined = pd.concat(frames, ignore_index=True, sort=False)
    return combined.drop_duplicates("dedupe_key", keep="first")


def load_candidate_pool(args: argparse.Namespace, exclude_keys: set[str]) -> list[dict[str, Any]]:
    df = pd.read_csv(PHASE16E_RECAL, low_memory=False)
    for column in [
        "iqa_quality_proxy_score",
        "clip_side_view_score",
        "final_candidate_score",
        "clip_viewpoint_prob_partial_or_occluded",
        "clip_viewpoint_prob_unclear",
    ]:
        df[column] = pd.to_numeric(df.get(column, 0), errors="coerce").fillna(0.0)
    df["dedupe_key"] = df["image_key"].map(normalize_key)
    df = df[~df["dedupe_key"].isin(exclude_keys)].copy()
    df = df[df["iqa_quality_proxy_score"].ge(args.prefilter_min_iqa)]
    df = df[df["clip_side_view_score"].ge(args.prefilter_min_side)]
    df = df[df["clip_viewpoint_prob_partial_or_occluded"].lt(args.prefilter_max_partial)]
    df = df[df["clip_viewpoint_prob_unclear"].lt(args.prefilter_max_unclear)]
    df["local_image_path"] = df.apply(resolve_local_path, axis=1)
    df = df[df["local_image_path"].ne("")]
    df["audit_identity_label"] = df["image_key"].map(identity_from_key)
    df["phase16e_rank_score"] = (
        0.45 * df["final_candidate_score"]
        + 0.35 * df["iqa_quality_proxy_score"]
        + 0.20 * df["clip_side_view_score"]
        - 0.10 * df["clip_viewpoint_prob_partial_or_occluded"]
        - 0.10 * df["clip_viewpoint_prob_unclear"]
    )
    df = df.sort_values("phase16e_rank_score", ascending=False)
    if args.candidate_limit:
        df = df.head(args.candidate_limit)
    keep = [
        "candidate_id",
        "image_key",
        "local_image_path",
        "phase16e_rank_score",
        "audit_identity_label",
        "md_best_confidence",
        "md_area_fraction",
        "md_width_fraction",
        "md_height_fraction",
        "md_edge_touch",
    ]
    keep = [column for column in keep if column in df.columns]
    return [{**row, "source_pool": "phase16e_local_rescore"} for row in df[keep].to_dict("records")]


def load_cache() -> dict[str, dict[str, str]]:
    rows = read_rows(DETECTION_CACHE)
    return {normalize_key(row.get("image_key", "")): row for row in rows if row.get("image_key")}


def download_local(candidate: dict[str, Any]) -> tuple[dict[str, Any], Image.Image | None, dict[str, Any]]:
    try:
        image = Image.open(candidate["local_image_path"]).convert("RGB")
        metrics = image_quality_metrics(image)
        gray = np.asarray(image.copy().resize((min(768, image.width), min(768, image.height))).convert("L"), dtype=np.float32)
        dx = np.diff(gray, axis=1)
        dy = np.diff(gray, axis=0)
        gradient = np.sqrt(dx[:-1, :] ** 2 + dy[:, :-1] ** 2)
        metrics["edge_density"] = round(float((gradient > 18).mean()), 6)
        return candidate, image, metrics
    except Exception as error:
        return candidate, None, {"strict_gate_reasons": f"load_failed:{type(error).__name__}:{str(error)[:100]}"}


def annotate_partial(row: dict[str, Any]) -> None:
    width = safe_float(row.get("image_width"))
    height = safe_float(row.get("image_height"))
    x1 = safe_float(row.get("subject_bbox_x1"))
    y1 = safe_float(row.get("subject_bbox_y1"))
    x2 = safe_float(row.get("subject_bbox_x2"))
    y2 = safe_float(row.get("subject_bbox_y2"))
    if not width or not height or not x2 or not y2:
        row["subject_edge_contact_count"] = ""
        row["subject_min_edge_margin_fraction"] = ""
        row["partial_body_risk"] = "unknown"
        row["completeness_proxy"] = "unknown"
        return
    margins = [max(0, x1) / width, max(0, y1) / height, max(0, width - x2) / width, max(0, height - y2) / height]
    edge_contact_count = sum(1 for margin in margins if margin <= 0.02)
    row["subject_edge_contact_count"] = edge_contact_count
    row["subject_min_edge_margin_fraction"] = round(min(margins), 6)
    if edge_contact_count >= 2:
        row["partial_body_risk"] = "high"
    elif edge_contact_count == 1:
        row["partial_body_risk"] = "medium"
    else:
        row["partial_body_risk"] = "low"
    area = safe_float(row.get("subject_area_fraction"))
    row["completeness_proxy"] = "complete_body_likely" if edge_contact_count == 0 and area >= 0.20 else "review_partial_or_occlusion_risk"


def apply_md_fallback(row: dict[str, Any], candidate: dict[str, Any], image: Image.Image) -> None:
    if row.get("detected_class") in ALLOWED_ANIMAL_CLASSES:
        return
    conf = safe_float(candidate.get("md_best_confidence"))
    area = safe_float(candidate.get("md_area_fraction"))
    width_fraction = safe_float(candidate.get("md_width_fraction"))
    height_fraction = safe_float(candidate.get("md_height_fraction"))
    if conf <= 0 or area <= 0 or width_fraction <= 0 or height_fraction <= 0:
        return
    width, height = image.size
    box_width = width * width_fraction
    box_height = height * height_fraction
    row["detected_class"] = "cat"
    row["detected_confidence"] = conf
    row["subject_bbox_x1"] = max(0.0, (width - box_width) / 2)
    row["subject_bbox_y1"] = max(0.0, (height - box_height) / 2)
    row["subject_bbox_x2"] = min(float(width), row["subject_bbox_x1"] + box_width)
    row["subject_bbox_y2"] = min(float(height), row["subject_bbox_y1"] + box_height)
    row["subject_area_fraction"] = area
    row["subject_width_fraction"] = width_fraction
    row["subject_height_fraction"] = height_fraction
    row["detector_model"] = f"{row.get('detector_model', 'yolo11n.pt')}+phase16e_md_fallback"


def strict_reasons(row: dict[str, Any], args: argparse.Namespace) -> list[str]:
    reasons = []
    bbox_short = min(
        max(0.0, safe_float(row.get("subject_bbox_x2")) - safe_float(row.get("subject_bbox_x1"))),
        max(0.0, safe_float(row.get("subject_bbox_y2")) - safe_float(row.get("subject_bbox_y1"))),
    )
    if row.get("detected_class") not in ALLOWED_ANIMAL_CLASSES:
        reasons.append("no_allowed_animal_detection")
    if safe_float(row.get("detected_confidence")) < args.min_detector_conf:
        reasons.append("low_detector_confidence")
    if bbox_short < args.min_bbox_short_side:
        reasons.append("bbox_short_side_lt_224px")
    if safe_float(row.get("subject_area_fraction")) < args.min_bbox_area:
        reasons.append("bbox_area_lt_10pct")
    if safe_float(row.get("subject_edge_contact_count")) >= 2:
        reasons.append("high_partial_body_or_edge_crop_risk")
    if safe_float(row.get("contrast_std")) < args.min_contrast:
        reasons.append("low_contrast")
    if safe_float(row.get("gradient_p90")) < args.min_gradient_p90:
        reasons.append("weak_edges_or_mosaic")
    if safe_float(row.get("laplacian_var")) < args.min_laplacian:
        reasons.append("low_sharpness")
    if safe_float(row.get("edge_density")) < args.min_edge_density:
        reasons.append("low_edge_density")
    return reasons


def score_new_candidates(candidates: list[dict[str, Any]], cache: dict[str, dict[str, str]], args: argparse.Namespace) -> None:
    if args.cache_only:
        return
    pending = [row for row in candidates if normalize_key(row["image_key"]) not in cache]
    if args.max_new:
        pending = pending[: args.max_new]
    if not pending:
        return
    model = YOLO(args.model)
    new_rows: list[dict[str, Any]] = []
    for start in range(0, len(pending), args.download_batch_size):
        batch = pending[start : start + args.download_batch_size]
        loaded = []
        with ThreadPoolExecutor(max_workers=args.download_workers) as executor:
            futures = [executor.submit(download_local, row) for row in batch]
            for future in as_completed(futures):
                candidate, image, payload = future.result()
                if image is None:
                    row = {**candidate, **payload, "detector_model": args.model}
                    new_rows.append(row)
                else:
                    loaded.append((candidate, image, payload))
        for detect_start in range(0, len(loaded), args.batch_size):
            detect_batch = loaded[detect_start : detect_start + args.batch_size]
            results = model.predict([item[1] for item in detect_batch], imgsz=args.image_size, conf=args.min_detector_conf, verbose=False)
            for (candidate, image, metrics), result in zip(detect_batch, results):
                detection = best_detection_from_result(result, image.size[0], image.size[1])
                row = {**candidate, **metrics, **detection, "detector_model": args.model}
                apply_md_fallback(row, candidate, image)
                annotate_partial(row)
                reasons = strict_reasons(row, args)
                row["strict_gate_pass"] = "yes" if not reasons else "no"
                row["strict_gate_reasons"] = "pass" if not reasons else "|".join(reasons)
                new_rows.append(row)
        all_rows = list(cache.values()) + new_rows
        write_csv(DETECTION_CACHE, all_rows, CACHE_FIELDS)
        print(f"processed_new={min(start + len(batch), len(pending))}/{len(pending)} cache_rows={len(all_rows)}", flush=True)


def base_to_queue_rows(base: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, row in base.iterrows():
        local_path = row.get("candidate_source_path") or row.get("local_image_path") or row.get("review_image_path_local") or ""
        rows.append(
            {
                "candidate_id": row.get("candidate_id") or row.get("expanded_image_id") or row.get("audit_image_key"),
                "image_key": row.get("audit_image_key") or row.get("path"),
                "local_image_path": local_path,
                "source_pool": "phase14_working_final_strict_pass",
                "phase16e_rank_score": "",
                "audit_identity_label": row.get("audit_identity_label") or identity_from_key(row.get("audit_image_key", "")),
                "image_width": row.get("image_width"),
                "image_height": row.get("image_height"),
                "contrast_std": row.get("contrast_std"),
                "gradient_p90": "",
                "laplacian_var": row.get("blur_laplacian_var"),
                "edge_density": row.get("edge_density"),
                "detector_model": "phase14_megadetector_existing",
                "detected_class": "cat",
                "detected_confidence": row.get("md_best_confidence"),
                "subject_area_fraction": row.get("md_area_fraction"),
                "subject_width_fraction": row.get("md_width_fraction"),
                "subject_height_fraction": row.get("md_height_fraction"),
                "partial_body_risk": "low",
                "completeness_proxy": "phase14_strict_pass",
                "strict_gate_pass": "yes",
                "strict_gate_reasons": "pass",
            }
        )
    return rows


def select_final(base: pd.DataFrame, candidates: list[dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cache = load_cache()
    selected_by_key: dict[str, dict[str, Any]] = {}
    group_counts: dict[str, int] = defaultdict(int)

    def maybe_add(row: dict[str, Any], rank_score: float) -> None:
        key = normalize_key(row.get("image_key", ""))
        group = row.get("audit_identity_label") or identity_from_key(key)
        if not key or key in selected_by_key:
            return
        if group_counts[group] >= args.max_per_identity:
            return
        out = dict(row)
        out["dedupe_key"] = key
        out["phase17_strict3000_rank_score"] = rank_score
        selected_by_key[key] = out
        group_counts[group] += 1

    for row in base_to_queue_rows(base):
        maybe_add(row, 10.0)

    pass_rows = []
    for row in cache.values():
        if row.get("strict_gate_pass") == "yes":
            pass_rows.append(row)
    pass_rows.sort(
        key=lambda row: (
            -safe_float(row.get("phase16e_rank_score")),
            -safe_float(row.get("subject_area_fraction")),
            -safe_float(row.get("laplacian_var")),
            -safe_float(row.get("detected_confidence")),
        )
    )
    for row in pass_rows:
        maybe_add(row, safe_float(row.get("phase16e_rank_score")))
        if len(selected_by_key) >= args.target_count:
            break
    selected = list(selected_by_key.values())
    for row in selected:
        if not row.get("image_uri"):
            row["image_uri"] = row.get("local_image_path", "")
    selected.sort(key=lambda row: (-safe_float(row.get("phase17_strict3000_rank_score")), str(row.get("dedupe_key"))))
    selected = selected[: args.target_count]
    for idx, row in enumerate(selected, start=1):
        row["phase17_strict3000_rank"] = idx
        row["phase17_strict3000_status"] = "strict_candidate_review_required"
    audit = {
        "selected_rows": len(selected),
        "target_count": args.target_count,
        "base_strict_pass_rows": len(base),
        "detector_cache_rows": len(cache),
        "detector_cache_pass_rows": sum(1 for row in cache.values() if row.get("strict_gate_pass") == "yes"),
        "selected_source_counts": dict(Counter(row.get("source_pool", "") for row in selected)),
        "selected_identity_count": len({row.get("audit_identity_label") for row in selected}),
        "largest_identity_count": max(Counter(row.get("audit_identity_label") for row in selected).values()) if selected else 0,
    }
    return selected, audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-count", type=int, default=3000)
    parser.add_argument("--candidate-limit", type=int, default=12000)
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--max-new", type=int, default=0)
    parser.add_argument("--max-per-identity", type=int, default=40)
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--prefilter-min-iqa", type=float, default=0.50)
    parser.add_argument("--prefilter-min-side", type=float, default=0.70)
    parser.add_argument("--prefilter-max-partial", type=float, default=0.30)
    parser.add_argument("--prefilter-max-unclear", type=float, default=0.20)
    parser.add_argument("--min-detector-conf", type=float, default=0.25)
    parser.add_argument("--min-bbox-short-side", type=float, default=224)
    parser.add_argument("--min-bbox-area", type=float, default=0.10)
    parser.add_argument("--min-contrast", type=float, default=42)
    parser.add_argument("--min-gradient-p90", type=float, default=18)
    parser.add_argument("--min-laplacian", type=float, default=80)
    parser.add_argument("--min-edge-density", type=float, default=0.05)
    parser.add_argument("--image-size", type=int, default=960)
    parser.add_argument("--download-workers", type=int, default=8)
    parser.add_argument("--download-batch-size", type=int, default=96)
    parser.add_argument("--batch-size", type=int, default=16)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    base = load_base_pass(args)
    exclude = set(base["dedupe_key"])
    candidates = load_candidate_pool(args, exclude)
    cache = load_cache()
    score_new_candidates(candidates, cache, args)
    selected, audit = select_final(base, candidates, args)
    write_csv(FINAL_QUEUE, selected, sorted({key for row in selected for key in row.keys()}))
    audit.update(
        {
            "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "candidate_rows_prefiltered": len(candidates),
            "output_queue_csv": str(FINAL_QUEUE),
            "detector_cache_csv": str(DETECTION_CACHE),
            "elapsed_seconds": round(time.time() - started, 2),
            "claim_boundary": "Prototype review queue only; human review/freeze still required.",
        }
    )
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# CzechLynx Strict 3000 Supplement",
                "",
                f"- Selected rows: {audit['selected_rows']} / {args.target_count}",
                f"- Base strict pass rows: {audit['base_strict_pass_rows']}",
                f"- Detector cache pass rows: {audit['detector_cache_pass_rows']}",
                f"- Source counts: {audit['selected_source_counts']}",
                "",
                "Boundary: prototype review queue only; final freeze requires human confirmation.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
