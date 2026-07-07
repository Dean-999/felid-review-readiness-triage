#!/usr/bin/env python3
"""PROTOTYPE: find strict Bobcat candidates for the final 902 gap.

Question:
Can we fill the remaining final-3000 gap without weakening the accepted clarity
standard?

This is throwaway prototype code. It builds a review queue only; it does not
promote rows into the final seed. Human CLEAR remains the only final-entry gate.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from PIL import Image
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTOTYPE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROTOTYPE_DIR))

from prototype_bobcat_photo_selection_subject40_gate import (  # noqa: E402
    ALLOWED_ANIMAL_CLASSES,
    OUTPUT_FIELDS,
    annotate_completeness_proxy,
    best_detection_from_result,
    image_quality_metrics,
    normalize_image_url,
    read_csv,
    seed_image_keys,
    write_csv,
)


OUTPUT_DIR = PROJECT_ROOT / "outputs/bobcat_photo_selection"
PHASE17O_LABEL = "phase17o_strict_final902_rescue"
DETECTIONS_CSV = OUTPUT_DIR / "bobcat_photo_selection_detector_scores.csv"
SEED_CSV = (
    PROJECT_ROOT
    / "outputs/phase17/phase17n_bobcat_final3000_seed/phase17n_bobcat_final3000_human_clear_seed_manifest.csv"
)
QUEUE_CSV = OUTPUT_DIR / f"bobcat_photo_selection_{PHASE17O_LABEL}_review_queue.csv"
AUDIT_JSON = OUTPUT_DIR / f"bobcat_photo_selection_{PHASE17O_LABEL}_audit.json"
COMBINED_CANDIDATES_CSV = OUTPUT_DIR / f"bobcat_photo_selection_{PHASE17O_LABEL}_combined_candidates.csv"

SOURCE_PATHS = [
    PROJECT_ROOT / "outputs/phase17/phase17m_inat_annotation_aware_strict_clarity_queue/phase17m_inat_annotation_aware_scored_all.csv",
    PROJECT_ROOT / "outputs/phase17/phase17l_multisource_strict_clarity_queue/phase17l_multisource_bobcat_scored_all.csv",
    PROJECT_ROOT / "outputs/phase17/phase17m_inat_annotation_aware_strict_clarity_queue/phase17m_inat_annotation_aware_strict_clarity_review_queue_5000.csv",
    PROJECT_ROOT / "outputs/phase17/phase17l_multisource_strict_clarity_queue/phase17l_bobcat_strict_clarity_review_queue_5000.csv",
    PROJECT_ROOT / "outputs/phase14/phase14_bobcat_high_confidence_inventory/phase14_bobcat_all_strict_high_candidates.csv",
    PROJECT_ROOT / "outputs/phase14/phase14_lila_md_prefilter/fcf_bobcat_md_high_prefilter_not_local_candidates.csv",
    PROJECT_ROOT / "outputs/phase14/phase14_lila_md_prefilter/fcf_bobcat_md_high_prefilter_not_in_local_roots_candidates.csv",
    PROJECT_ROOT / "outputs/phase14/phase14_megadetector_evidence_gate/phase14_megadetector_urban_bobcat_auto_high_candidates.csv",
    PROJECT_ROOT / "outputs/phase14/phase14_megadetector_evidence_gate_300x2/phase14_megadetector_urban_bobcat_auto_high_candidates.csv",
]

REVIEW_PATHS = [
    PROJECT_ROOT / "outputs/bobcat_photo_selection/reviews/combined_rescue_to_3000/bobcat_photo_selection_review_working.csv",
    PROJECT_ROOT / "outputs/bobcat_photo_selection/reviews/phase14_day_ultra_bbox224_crop_rescue/bobcat_photo_selection_review_working.csv",
    PROJECT_ROOT / "outputs/bobcat_photo_selection/reviews/phase14_day_ultra_no_poor_exposure_rescue/bobcat_photo_selection_review_working.csv",
    PROJECT_ROOT / "outputs/bobcat_photo_selection/reviews/subject20_multisource_full_complete_priority/bobcat_photo_selection_review_working.csv",
    PROJECT_ROOT / "outputs/bobcat_photo_selection/reviews/subject20_multisource_interim_4k/bobcat_photo_selection_review_working.csv",
]


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_candidate(row: dict[str, Any], source_name: str, index: int) -> dict[str, str] | None:
    image_uri = (
        row.get("image_uri")
        or row.get("download_url")
        or row.get("azure_url")
        or row.get("review_image_path_local")
        or row.get("local_image_path")
        or row.get("image_path")
        or ""
    )
    image_uri = str(image_uri)
    if not image_uri or image_uri.lower() == "nan":
        return None
    if not image_uri.startswith(("http://", "https://")):
        local = PROJECT_ROOT / image_uri
        if local.exists():
            image_uri = str(local)
        else:
            return None
    photo_id = str(row.get("photo_id") or row.get("image_id") or row.get("annotation_id") or "")
    candidate_id = str(row.get("candidate_id") or f"{source_name}_{index:06d}_{photo_id}")
    return {
        "candidate_id": candidate_id,
        "image_uri": normalize_image_url(image_uri) if image_uri.startswith(("http://", "https://")) else image_uri,
        "source_uri": str(row.get("source_uri") or row.get("observation_uri") or row.get("dataset_page") or ""),
        "photo_id": photo_id,
        "observation_id": str(row.get("observation_id") or row.get("source_record_id") or ""),
        "place_guess": str(row.get("place_guess") or row.get("location_id") or ""),
        "phase17l_strict_proxy_tier": str(row.get("phase17l_strict_proxy_tier") or row.get("evidence_tier") or ""),
        "phase17l_strict_clarity_proxy_score": str(row.get("phase17l_strict_clarity_proxy_score") or row.get("auto_quality_score") or ""),
    }


def build_combined_candidates() -> list[dict[str, str]]:
    rows_by_key: dict[str, dict[str, str]] = {}
    for path in SOURCE_PATHS:
        if not path.exists():
            continue
        source_name = path.parent.name
        with path.open(newline="", encoding="utf-8") as handle:
            for index, row in enumerate(csv.DictReader(handle), start=1):
                candidate = normalize_candidate(row, source_name, index)
                if not candidate:
                    continue
                key = normalize_image_url(candidate["image_uri"])
                if key and key not in rows_by_key:
                    rows_by_key[key] = candidate
    rows = list(rows_by_key.values())
    write_csv(COMBINED_CANDIDATES_CSV, rows, OUTPUT_FIELDS)
    return rows


def reviewed_reject_keys() -> set[str]:
    reject_keys: set[str] = set()
    for path in REVIEW_PATHS:
        for row in read_csv(path):
            key = normalize_image_url(row.get("image_uri", ""))
            if not key:
                continue
            decision = (
                row.get("human_subject40_clear_decision")
                or row.get("phase17l_clarity_gate_decision")
                or row.get("phase17k_clarity_gate_decision")
                or row.get("human_quality_yes_no")
                or ""
            ).strip().lower()
            if decision in {"reject", "not_clear", "not clear", "no"}:
                reject_keys.add(key)
    return reject_keys


def download_image(uri: str, timeout: int) -> Image.Image:
    if uri.startswith(("http://", "https://")):
        response = requests.get(
            uri,
            headers={"User-Agent": "phase17o-bobcat-strict-final902-prototype/0.1"},
            timeout=(timeout, timeout),
        )
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGB")
    return Image.open(uri).convert("RGB")


def download_candidate(candidate: dict[str, str], timeout: int) -> tuple[dict[str, str], Image.Image | None, dict[str, Any]]:
    try:
        image = download_image(candidate["image_uri"], timeout)
        return candidate, image, image_quality_metrics(image)
    except Exception as error:
        return candidate, None, {"subject_gate_reasons": f"download_failed:{type(error).__name__}:{str(error)[:120]}"}


def bbox_short_side(row: dict[str, Any]) -> float:
    width = safe_float(row.get("subject_bbox_x2")) - safe_float(row.get("subject_bbox_x1"))
    height = safe_float(row.get("subject_bbox_y2")) - safe_float(row.get("subject_bbox_y1"))
    return max(0.0, min(width, height))


def strict_reasons(row: dict[str, Any], args: argparse.Namespace) -> list[str]:
    reasons: list[str] = []
    if str(row.get("detected_class", "")) not in ALLOWED_ANIMAL_CLASSES:
        reasons.append("no_allowed_animal_detection")
    if safe_float(row.get("detected_confidence")) < args.detector_conf:
        reasons.append("low_detector_confidence")
    if bbox_short_side(row) < args.min_bbox_short_side:
        reasons.append(f"bbox_short_side_lt_{int(args.min_bbox_short_side)}px")
    if safe_float(row.get("contrast_std")) < args.min_contrast:
        reasons.append("low_contrast")
    if safe_float(row.get("gradient_p90")) < args.min_gradient_p90:
        reasons.append("weak_edges_or_mosaic")
    if safe_float(row.get("laplacian_var")) < args.min_laplacian:
        reasons.append("low_animal_or_image_sharpness")
    if safe_float(row.get("subject_edge_contact_count")) >= 2:
        reasons.append("high_partial_body_or_edge_crop_risk")
    return reasons


def load_detection_cache() -> dict[str, dict[str, str]]:
    return {
        normalize_image_url(row.get("image_uri", "")): row
        for row in read_csv(DETECTIONS_CSV)
        if normalize_image_url(row.get("image_uri", ""))
    }


def score_new_candidates(candidates: list[dict[str, str]], existing: dict[str, dict[str, str]], args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.cache_only:
        return []
    pending = [row for row in candidates if normalize_image_url(row["image_uri"]) not in existing]
    pending = pending[: args.max_new] if args.max_new > 0 else pending
    if not pending:
        return []
    model = YOLO(args.model)
    new_rows: list[dict[str, Any]] = []
    for batch_start in range(0, len(pending), args.download_batch_size):
        batch = pending[batch_start : batch_start + args.download_batch_size]
        downloaded: list[tuple[dict[str, str], Image.Image, dict[str, Any]]] = []
        with ThreadPoolExecutor(max_workers=args.download_workers) as executor:
            futures = [executor.submit(download_candidate, row, args.timeout) for row in batch]
            for future in as_completed(futures):
                candidate, image, payload = future.result()
                if image is None:
                    new_rows.append({**candidate, **payload, "detector_model": args.model})
                else:
                    downloaded.append((candidate, image, payload))
        for detect_start in range(0, len(downloaded), args.batch_size):
            detect_batch = downloaded[detect_start : detect_start + args.batch_size]
            results = model.predict([item[1] for item in detect_batch], imgsz=args.image_size, conf=args.detector_conf, verbose=False)
            for (candidate, image, metrics), result in zip(detect_batch, results):
                detection = best_detection_from_result(result, image.size[0], image.size[1])
                new_rows.append({**candidate, **metrics, **detection, "detector_model": args.model})
        cache_rows = list(existing.values()) + new_rows
        write_csv(DETECTIONS_CSV, cache_rows, OUTPUT_FIELDS)
        print(f"phase17o processed_new={min(batch_start + len(batch), len(pending))}/{len(pending)}", flush=True)
    return new_rows


def select_rows(args: argparse.Namespace) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = build_combined_candidates()
    seed_keys = seed_image_keys(SEED_CSV)
    reject_keys = reviewed_reject_keys()
    existing = load_detection_cache()
    new_rows = score_new_candidates(candidates, existing, args)
    if new_rows:
        all_detection_rows = list(existing.values()) + new_rows
        write_csv(DETECTIONS_CSV, all_detection_rows, OUTPUT_FIELDS)
        existing = load_detection_cache()

    candidate_keys = {normalize_image_url(row["image_uri"]) for row in candidates}
    selected_pool: list[dict[str, Any]] = []
    rejection_reasons: Counter[str] = Counter()
    for key, row in existing.items():
        if key not in candidate_keys or key in seed_keys or key in reject_keys:
            continue
        row = dict(row)
        annotate_completeness_proxy(row)
        reasons = strict_reasons(row, args)
        row["subject_gate_pass"] = "yes" if not reasons else "no"
        row["subject_gate_reasons"] = "|".join(reasons) if reasons else "pass"
        row["final_gate_rule"] = (
            "phase17o strict final-gap candidate: bbox short side >= "
            f"{args.min_bbox_short_side}px, contrast >= {args.min_contrast}, "
            f"gradient_p90 >= {args.min_gradient_p90}, laplacian >= {args.min_laplacian}; "
            "human CLEAR required before final seed entry"
        )
        if reasons:
            rejection_reasons.update(reasons)
            continue
        selected_pool.append(row)

    selected_pool.sort(
        key=lambda row: (
            safe_float(row.get("subject_edge_contact_count")),
            {"low": 0, "medium": 1, "high": 2, "unknown": 3}.get(str(row.get("partial_body_risk", "unknown")), 3),
            -bbox_short_side(row),
            -safe_float(row.get("subject_area_fraction")),
            -safe_float(row.get("laplacian_var")),
            -safe_float(row.get("detected_confidence")),
        )
    )
    selected = selected_pool[: args.target_count]
    for rank, row in enumerate(selected, start=1):
        row["selection_rank"] = rank
        row["selection_status"] = "phase17o_strict_final902_review_candidate"
    write_csv(QUEUE_CSV, selected, OUTPUT_FIELDS)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prototype_question": "Can the final 902 gap be filled without weakening the accepted clarity/crop standard?",
        "combined_candidate_rows": len(candidates),
        "existing_detection_rows": len(existing),
        "new_detection_rows_scored": len(new_rows),
        "seed_rows_excluded": len(seed_keys),
        "review_reject_keys_excluded": len(reject_keys),
        "strict_pass_rows_available": len(selected_pool),
        "selected_review_queue_rows": len(selected),
        "target_count": args.target_count,
        "output_queue_csv": str(QUEUE_CSV),
        "combined_candidates_csv": str(COMBINED_CANDIDATES_CSV),
        "detector_scores_csv": str(DETECTIONS_CSV),
        "gate": {
            "allowed_detector_classes": sorted(ALLOWED_ANIMAL_CLASSES),
            "min_bbox_short_side_px": args.min_bbox_short_side,
            "detector_confidence_min": args.detector_conf,
            "contrast_std_min": args.min_contrast,
            "gradient_p90_min": args.min_gradient_p90,
            "laplacian_var_min": args.min_laplacian,
            "edge_contact_count_max": 1,
        },
        "class_counts": dict(Counter(row.get("detected_class", "") for row in selected)),
        "partial_body_risk_counts": dict(Counter(row.get("partial_body_risk", "") for row in selected)),
        "rejection_reason_counts": dict(rejection_reasons.most_common(25)),
        "claim_boundary": "This is a strict review queue only. It does not fill the final 3000 until the user/human reviewer marks rows CLEAR.",
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-count", type=int, default=902)
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--max-new", type=int, default=0)
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--detector-conf", type=float, default=0.25)
    parser.add_argument("--min-bbox-short-side", type=float, default=224)
    parser.add_argument("--min-contrast", type=float, default=42)
    parser.add_argument("--min-gradient-p90", type=float, default=18)
    parser.add_argument("--min-laplacian", type=float, default=80)
    parser.add_argument("--image-size", type=int, default=960)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--download-workers", type=int, default=12)
    parser.add_argument("--download-batch-size", type=int, default=96)
    parser.add_argument("--batch-size", type=int, default=16)
    return parser.parse_args()


def main() -> int:
    start = time.time()
    audit = select_rows(parse_args())
    audit["elapsed_seconds"] = round(time.time() - start, 2)
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
