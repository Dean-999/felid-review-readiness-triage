#!/usr/bin/env python3
"""PROTOTYPE: Bobcat photo selection with an animal subject >=40% gate.

Question:
Can a real detector gate remove the unstable "sharp image but tiny/non-
comparable animal" failure mode?

This is throwaway prototype code. It uses a general YOLO detector as a fast
subject-area proxy, not a final species classifier. Final inclusion still
requires human CLEAR confirmation.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import requests
from PIL import Image
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs/bobcat_photo_selection"
DEFAULT_CANDIDATES = (
    PROJECT_ROOT
    / "outputs/phase17/phase17m_inat_annotation_aware_strict_clarity_queue/"
    / "phase17m_inat_annotation_aware_strict_clarity_review_queue_5000.csv"
)
DEFAULT_SEED = (
    PROJECT_ROOT
    / "outputs/phase17/phase17n_bobcat_final3000_seed/phase17n_bobcat_final3000_human_clear_seed_manifest.csv"
)
DETECTIONS_CSV = OUTPUT_DIR / "bobcat_photo_selection_detector_scores.csv"

ALLOWED_ANIMAL_CLASSES = {"cat", "dog", "bear"}
OUTPUT_FIELDS = [
    "selection_rank",
    "selection_status",
    "candidate_id",
    "image_uri",
    "source_uri",
    "photo_id",
    "observation_id",
    "place_guess",
    "phase17l_strict_proxy_tier",
    "phase17l_strict_clarity_proxy_score",
    "image_width",
    "image_height",
    "contrast_std",
    "gradient_p90",
    "laplacian_var",
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
    "subject_gate_pass",
    "subject_gate_reasons",
    "final_gate_rule",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def normalize_image_url(url: str) -> str:
    return (
        str(url or "")
        .replace("/original.", "/large.")
        .replace("/medium.", "/large.")
        .replace("/small.", "/large.")
        .replace("/square.", "/large.")
        .split("?", 1)[0]
    )


def download_image(url: str, timeout: int) -> Image.Image:
    response = requests.get(
        url,
        headers={"User-Agent": "bobcat-photo-selection-prototype/0.1"},
        timeout=(timeout, timeout),
    )
    response.raise_for_status()
    data = response.content
    return Image.open(io.BytesIO(data)).convert("RGB")


def image_quality_metrics(image: Image.Image) -> dict[str, float | int]:
    width, height = image.size
    resized = image.copy()
    resized.thumbnail((768, 768))
    gray = np.asarray(resized.convert("L"), dtype=np.float32)
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    gradient = np.sqrt(dx[:-1, :] ** 2 + dy[:, :-1] ** 2)
    lap = gray[1:-1, 1:-1] * -4.0 + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    return {
        "image_width": width,
        "image_height": height,
        "contrast_std": round(float(np.std(gray)), 4),
        "gradient_p90": round(float(np.percentile(gradient, 90)), 4),
        "laplacian_var": round(float(np.var(lap)), 4),
    }


def seed_image_keys(seed_path: Path) -> set[str]:
    keys: set[str] = set()
    for row in read_csv(seed_path):
        for key in [row.get("canonical_image_key", ""), row.get("image_uri", "")]:
            if key:
                keys.add(normalize_image_url(key))
    return keys


def existing_detection_rows() -> dict[str, dict[str, str]]:
    rows = read_csv(DETECTIONS_CSV)
    return {normalize_image_url(row.get("image_uri", "")): row for row in rows if row.get("image_uri")}


def best_detection(model: YOLO, image: Image.Image, image_size: int, conf: float) -> dict[str, Any]:
    result = model.predict(image, imgsz=image_size, conf=conf, verbose=False)[0]
    names = result.names
    width, height = image.size
    best: dict[str, Any] | None = None
    if result.boxes is None:
        return {}
    for box in result.boxes:
        cls_id = int(box.cls.item())
        cls_name = str(names.get(cls_id, cls_id))
        if cls_name not in ALLOWED_ANIMAL_CLASSES:
            continue
        x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
        bbox_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        area_fraction = bbox_area / max(1.0, float(width * height))
        row = {
            "detected_class": cls_name,
            "detected_confidence": round(float(box.conf.item()), 5),
            "subject_bbox_x1": round(x1, 2),
            "subject_bbox_y1": round(y1, 2),
            "subject_bbox_x2": round(x2, 2),
            "subject_bbox_y2": round(y2, 2),
            "subject_area_fraction": round(area_fraction, 6),
            "subject_width_fraction": round(max(0.0, x2 - x1) / max(1.0, width), 6),
            "subject_height_fraction": round(max(0.0, y2 - y1) / max(1.0, height), 6),
        }
        if best is None or row["subject_area_fraction"] > best["subject_area_fraction"]:
            best = row
    return best or {}


def best_detection_from_result(result: Any, width: int, height: int) -> dict[str, Any]:
    names = result.names
    best: dict[str, Any] | None = None
    if result.boxes is None:
        return {}
    for box in result.boxes:
        cls_id = int(box.cls.item())
        cls_name = str(names.get(cls_id, cls_id))
        if cls_name not in ALLOWED_ANIMAL_CLASSES:
            continue
        x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
        bbox_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        area_fraction = bbox_area / max(1.0, float(width * height))
        row = {
            "detected_class": cls_name,
            "detected_confidence": round(float(box.conf.item()), 5),
            "subject_bbox_x1": round(x1, 2),
            "subject_bbox_y1": round(y1, 2),
            "subject_bbox_x2": round(x2, 2),
            "subject_bbox_y2": round(y2, 2),
            "subject_area_fraction": round(area_fraction, 6),
            "subject_width_fraction": round(max(0.0, x2 - x1) / max(1.0, width), 6),
            "subject_height_fraction": round(max(0.0, y2 - y1) / max(1.0, height), 6),
        }
        if best is None or row["subject_area_fraction"] > best["subject_area_fraction"]:
            best = row
    return best or {}


def annotate_completeness_proxy(row: dict[str, Any]) -> None:
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

    margins = [
        max(0.0, x1) / width,
        max(0.0, y1) / height,
        max(0.0, width - x2) / width,
        max(0.0, height - y2) / height,
    ]
    edge_contact_count = sum(1 for margin in margins if margin <= 0.02)
    min_margin = min(margins)
    area = safe_float(row.get("subject_area_fraction"))
    width_fraction = safe_float(row.get("subject_width_fraction"))
    height_fraction = safe_float(row.get("subject_height_fraction"))

    if edge_contact_count >= 2:
        risk = "high"
    elif edge_contact_count == 1 and (area >= 0.30 or width_fraction >= 0.70 or height_fraction >= 0.70):
        risk = "medium"
    elif edge_contact_count == 1:
        risk = "low"
    else:
        risk = "low"

    if edge_contact_count == 0 and area >= 0.20 and width_fraction >= 0.30 and height_fraction >= 0.23:
        proxy = "complete_body_likely"
    elif edge_contact_count <= 1 and area >= 0.20:
        proxy = "review_partial_or_occlusion_risk"
    else:
        proxy = "not_comparable_or_unknown"

    row["subject_edge_contact_count"] = edge_contact_count
    row["subject_min_edge_margin_fraction"] = round(min_margin, 6)
    row["partial_body_risk"] = risk
    row["completeness_proxy"] = proxy


def download_candidate(candidate: dict[str, str], timeout: int) -> tuple[dict[str, str], Image.Image | None, dict[str, Any]]:
    image_key = normalize_image_url(candidate.get("image_uri", ""))
    try:
        image = download_image(image_key, timeout=timeout)
        metrics = image_quality_metrics(image)
        return candidate, image, metrics
    except Exception as error:
        return (
            candidate,
            None,
            {
                "image_uri": image_key,
                "subject_gate_pass": "no",
                "subject_gate_reasons": f"download_or_detector_failed:{type(error).__name__}:{str(error)[:120]}",
            },
        )


def gate_reasons(row: dict[str, Any], min_area: float, min_width: float, min_height: float, min_conf: float) -> list[str]:
    reasons: list[str] = []
    if not row.get("detected_class"):
        reasons.append("no_allowed_animal_detection")
    if safe_float(row.get("detected_confidence")) < min_conf:
        reasons.append("low_detector_confidence")
    if safe_float(row.get("subject_area_fraction")) < min_area:
        reasons.append(f"subject_area_lt_{int(min_area * 100)}pct")
    if safe_float(row.get("subject_width_fraction")) < min_width:
        reasons.append(f"subject_width_lt_{int(min_width * 100)}pct")
    if safe_float(row.get("subject_height_fraction")) < min_height:
        reasons.append(f"subject_height_lt_{int(min_height * 100)}pct")
    if safe_float(row.get("contrast_std")) < 42:
        reasons.append("low_contrast")
    if safe_float(row.get("gradient_p90")) < 18:
        reasons.append("weak_edges_or_mosaic")
    if safe_float(row.get("laplacian_var")) < 80:
        reasons.append("low_sharpness_or_mosaic")
    return reasons


def score_candidates(args: argparse.Namespace) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    label = args.label or f"subject{int(args.min_subject_area * 100)}"
    queue_csv = OUTPUT_DIR / f"bobcat_photo_selection_{label}_review_queue.csv"
    audit_json = OUTPUT_DIR / f"bobcat_photo_selection_{label}_audit.json"
    gallery_html = OUTPUT_DIR / f"bobcat_photo_selection_{label}_gallery.html"
    model = YOLO(args.model)
    candidates = read_csv(Path(args.candidates))
    seed_keys = seed_image_keys(Path(args.seed))
    source_rows = candidates[: args.limit] if args.limit else candidates
    source_keys = {normalize_image_url(row.get("image_uri", "")) for row in source_rows if normalize_image_url(row.get("image_uri", ""))}
    existing = existing_detection_rows()
    rows: list[dict[str, Any]] = list(existing.values())
    processed_keys = set(existing)
    start = time.time()
    pending_candidates = [
        candidate
        for candidate in source_rows
        if normalize_image_url(candidate.get("image_uri", ""))
        and normalize_image_url(candidate.get("image_uri", "")) not in processed_keys
    ]
    for batch_start in range(0, len(pending_candidates), args.download_batch_size):
        batch_candidates = pending_candidates[batch_start : batch_start + args.download_batch_size]
        downloaded: list[tuple[dict[str, str], Image.Image, dict[str, Any]]] = []
        with ThreadPoolExecutor(max_workers=args.download_workers) as executor:
            futures = [executor.submit(download_candidate, candidate, args.timeout) for candidate in batch_candidates]
            for future in as_completed(futures):
                candidate, image, payload = future.result()
                image_key = normalize_image_url(candidate.get("image_uri", ""))
                if image is None:
                    rows.append({**candidate, **payload, "detector_model": args.model})
                    processed_keys.add(image_key)
                else:
                    downloaded.append((candidate, image, payload))
        for detect_start in range(0, len(downloaded), args.batch_size):
            detect_batch = downloaded[detect_start : detect_start + args.batch_size]
            images = [item[1] for item in detect_batch]
            results = model.predict(images, imgsz=args.image_size, conf=args.detector_conf, verbose=False)
            for (candidate, image, metrics), result in zip(detect_batch, results):
                image_key = normalize_image_url(candidate.get("image_uri", ""))
                detection = best_detection_from_result(result, image.size[0], image.size[1])
                row = {
                    **candidate,
                    **metrics,
                    **detection,
                    "image_uri": image_key,
                    "detector_model": args.model,
                }
                rows.append(row)
                processed_keys.add(image_key)
        processed = min(batch_start + len(batch_candidates), len(pending_candidates))
        print(
            f"processed_new={processed}/{len(pending_candidates)} total_rows={len(rows)} "
            f"pass={sum(1 for r in rows if r.get('subject_gate_pass') == 'yes')}",
            flush=True,
        )
        write_csv(DETECTIONS_CSV, rows, OUTPUT_FIELDS)
    for row in rows:
        annotate_completeness_proxy(row)
        reasons = gate_reasons(row, args.min_subject_area, args.min_subject_width, args.min_subject_height, args.detector_conf)
        row["subject_gate_pass"] = "yes" if not reasons else "no"
        row["subject_gate_reasons"] = "|".join(reasons) if reasons else "pass"
        row["final_gate_rule"] = (
            f"animal bbox area >= {args.min_subject_area:.2f}, width >= {args.min_subject_width:.2f}, "
            f"height >= {args.min_subject_height:.2f}, sharp/contrast proxy pass; final human CLEAR still required"
        )
    write_csv(DETECTIONS_CSV, rows, OUTPUT_FIELDS)

    scored_rows = [row for row in rows if normalize_image_url(row.get("image_uri", "")) in source_keys]
    passed = [row for row in scored_rows if row.get("subject_gate_pass") == "yes"]
    if args.exclude_seed:
        passed = [row for row in passed if normalize_image_url(row.get("image_uri", "")) not in seed_keys]
    passed.sort(
        key=lambda row: (
            safe_int(row.get("subject_edge_contact_count")),
            {"low": 0, "medium": 1, "high": 2, "unknown": 3}.get(str(row.get("partial_body_risk", "unknown")), 3),
            0 if row.get("completeness_proxy") == "complete_body_likely" else 1,
            -safe_float(row.get("subject_area_fraction")),
            -safe_float(row.get("detected_confidence")),
            -safe_float(row.get("laplacian_var")),
        )
    )
    selected = passed[: args.target_count]
    for rank, row in enumerate(selected, start=1):
        row["selection_rank"] = rank
        row["selection_status"] = "subject_detector_pass_review_candidate"
    write_csv(queue_csv, selected, OUTPUT_FIELDS)
    write_gallery(selected[: args.gallery_count], gallery_html)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_rows_considered": len(source_rows),
        "detector_rows_total": len(rows),
        "scored_rows_total": len(scored_rows),
        "subject_gate_pass_rows": len(passed),
        "subject40_pass_rows": len(passed),
        "selected_rows": len(selected),
        "target_count": args.target_count,
        "gate": {
            "allowed_detector_classes": sorted(ALLOWED_ANIMAL_CLASSES),
            "min_subject_area_fraction": args.min_subject_area,
            "min_subject_width_fraction": args.min_subject_width,
            "min_subject_height_fraction": args.min_subject_height,
            "detector_confidence_min": args.detector_conf,
            "contrast_std_min": 42,
            "gradient_p90_min": 18,
            "laplacian_var_min": 80,
        },
        "pass_class_counts": dict(Counter(row.get("detected_class", "") for row in passed)),
        "partial_body_risk_counts": dict(Counter(row.get("partial_body_risk", "") for row in passed)),
        "completeness_proxy_counts": dict(Counter(row.get("completeness_proxy", "") for row in passed)),
        "exclude_seed": bool(args.exclude_seed),
        "rejection_reason_counts": dict(Counter(row.get("subject_gate_reasons", "") for row in rows).most_common(30)),
        "output_queue_csv": str(queue_csv),
        "detector_scores_csv": str(DETECTIONS_CSV),
        "gallery_html": str(gallery_html),
        "elapsed_seconds": round(time.time() - start, 2),
        "claim_boundary": "Detector pass is a review candidate gate, not final truth. Human CLEAR remains required.",
    }
    audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "NOTES.md").write_text(
        "\n".join(
            [
                "# Bobcat Photo Selection",
                "",
                "Unified photo-selection workspace. Older Phase17 lettered queues are historical inputs only.",
                "",
                "Current hard target: image is sharp, no mosaic/compression blur, animal is large enough for comparison, and human CLEAR remains final.",
                "Current review ordering prefers complete-body-likely candidates before partial-body or occlusion-risk candidates.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return audit


def write_gallery(rows: list[dict[str, Any]], output_path: Path) -> None:
    cards = []
    for row in rows:
        image_uri = html.escape(str(row.get("image_uri", "")), quote=True)
        label = html.escape(
            f"{row.get('candidate_id')} | area={row.get('subject_area_fraction')} | conf={row.get('detected_confidence')} | {row.get('detected_class')}",
            quote=False,
        )
        cards.append(
            f"""
            <a class="card" href="{image_uri}" target="_blank" rel="noreferrer">
              <img src="{image_uri}" loading="lazy" />
              <div>{label}</div>
            </a>
            """
        )
    output_path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Bobcat subject detector gate</title>
  <style>
    body {{ margin: 24px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f6f3; color: #202124; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }}
    .card {{ display: block; color: inherit; text-decoration: none; background: white; border: 1px solid #d7d9d2; border-radius: 6px; overflow: hidden; }}
    img {{ width: 100%; aspect-ratio: 4 / 3; object-fit: contain; display: block; background: #eceee8; }}
    .card div {{ padding: 8px; font-size: 12px; line-height: 1.35; }}
  </style>
</head>
<body>
  <h1>Bobcat subject detector gate</h1>
  <p>Detector-gated candidates only. Final human CLEAR still required.</p>
  <div class="grid">{''.join(cards)}</div>
</body>
</html>
""",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--seed", default=str(DEFAULT_SEED))
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--target-count", type=int, default=3000)
    parser.add_argument("--gallery-count", type=int, default=200)
    parser.add_argument("--min-subject-area", type=float, default=0.40)
    parser.add_argument("--min-subject-width", type=float, default=0.45)
    parser.add_argument("--min-subject-height", type=float, default=0.35)
    parser.add_argument("--detector-conf", type=float, default=0.25)
    parser.add_argument("--image-size", type=int, default=960)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--label", default="")
    parser.add_argument("--download-workers", type=int, default=12)
    parser.add_argument("--download-batch-size", type=int, default=96)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--exclude-seed", action="store_true")
    return parser.parse_args()


def main() -> int:
    audit = score_candidates(parse_args())
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
