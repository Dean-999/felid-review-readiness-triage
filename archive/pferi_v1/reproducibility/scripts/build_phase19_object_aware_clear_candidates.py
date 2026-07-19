#!/usr/bin/env python3
"""Build object-aware Phase19 clear-photo candidates.

This replaces whole-image sharpness with animal-box evidence. A row is kept only
when YOLO finds a large-enough felid-like animal box and the animal crop itself
is sharp enough for visual comparison.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageStat
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREFILTER_DIR = PROJECT_ROOT / "outputs/phase19/phase19_strict_photo_prefilter"
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_object_aware_clear_candidates"
MODEL_PATH = PROJECT_ROOT / "yolo11n.pt"

POOLS = [
    "bobcat_wild_camera_trap",
    "bobcat_urban_heterogeneous",
    "lynx_external_heterogeneous_supplement",
]

ANIMAL_CLASSES = {"cat", "dog", "bear", "horse", "sheep", "cow"}

OUTPUT_FIELDS = [
    "phase19_review_id",
    "phase19_cell",
    "source_dataset",
    "source_platform",
    "source_candidate_id",
    "source_image_path",
    "source_image_uri",
    "species",
    "domain_label",
    "license",
    "attribution",
    "image_width",
    "image_height",
    "yolo_class",
    "yolo_confidence",
    "animal_bbox_x1",
    "animal_bbox_y1",
    "animal_bbox_x2",
    "animal_bbox_y2",
    "animal_area_fraction",
    "animal_width_fraction",
    "animal_height_fraction",
    "animal_crop_width",
    "animal_crop_height",
    "animal_crop_megapixels",
    "animal_crop_contrast_std",
    "animal_crop_gradient_p90",
    "animal_crop_laplacian_var",
    "animal_crop_entropy",
    "animal_crop_brightness_mean",
    "animal_crop_saturation_mean",
    "animal_crop_grayscale_proxy",
    "object_aware_score",
    "object_aware_decision",
    "object_aware_reject_reasons",
    "phase19_manual_decision",
    "phase19_manual_reject_reason",
    "phase19_manual_notes",
    "phase19_manual_audited_at_utc",
    "phase19_claim_boundary",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any, default: float = -999.0) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def laplacian_variance(gray: np.ndarray) -> float:
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    center = gray[1:-1, 1:-1] * -4.0
    lap = center + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    return float(np.var(lap))


def crop_metrics(image: Image.Image, box: tuple[int, int, int, int]) -> dict[str, Any]:
    crop = image.crop(box).convert("RGB")
    width, height = crop.size
    resized = crop.copy()
    resized.thumbnail((768, 768))
    gray_image = resized.convert("L")
    gray = np.asarray(gray_image, dtype=np.float32)
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    gradient = np.sqrt(dx[:-1, :] ** 2 + dy[:, :-1] ** 2) if gray.shape[0] > 1 and gray.shape[1] > 1 else np.asarray([0.0])
    hist = gray_image.histogram()
    total = sum(hist) or 1
    entropy = -sum((count / total) * math.log2(count / total) for count in hist if count)
    r, g, b = [np.asarray(channel, dtype=np.float32) for channel in resized.split()]
    channel_spread = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    hsv = resized.convert("HSV")
    saturation = np.asarray(hsv.getchannel("S"), dtype=np.float32)
    stat = ImageStat.Stat(resized)
    return {
        "animal_crop_width": width,
        "animal_crop_height": height,
        "animal_crop_megapixels": round((width * height) / 1_000_000, 4),
        "animal_crop_contrast_std": round(float(np.std(gray)), 4),
        "animal_crop_gradient_p90": round(float(np.percentile(gradient, 90)), 4),
        "animal_crop_laplacian_var": round(laplacian_variance(gray), 4),
        "animal_crop_entropy": round(float(entropy), 4),
        "animal_crop_brightness_mean": round(float(stat.mean[0]), 4),
        "animal_crop_saturation_mean": round(float(np.mean(saturation)), 4),
        "animal_crop_grayscale_proxy": round(float(np.mean(channel_spread < 8.0)), 6),
    }


def input_rows_for_pool(pool: str) -> list[dict[str, str]]:
    rows = read_csv(PREFILTER_DIR / f"{pool}_strict_photo_prefilter.csv")
    out: list[dict[str, str]] = []
    for row in rows:
        if row.get("phase19_prefilter_decision") != "review":
            continue
        # Keep only rows that passed the current broad image-level gate before
        # spending YOLO time. Animal-level gates below decide final inclusion.
        if row.get("technical_quality_rule") not in {"technical_strict_pass", "technical_cautious_pass"}:
            continue
        out.append(row)
    out.sort(key=lambda r: -safe_float(r.get("phase19_strict_photo_score")))
    return out


def best_detection(result: Any) -> dict[str, Any] | None:
    names = result.names
    best: dict[str, Any] | None = None
    for box in result.boxes:
        cls_id = int(box.cls.item())
        cls_name = str(names.get(cls_id, cls_id))
        conf = float(box.conf.item())
        if cls_name not in ANIMAL_CLASSES:
            continue
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
        area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        candidate = {"class": cls_name, "confidence": conf, "xyxy": (x1, y1, x2, y2), "area": area}
        if best is None or candidate["area"] * candidate["confidence"] > best["area"] * best["confidence"]:
            best = candidate
    return best


def score_candidate(row: dict[str, str], detection: dict[str, Any], metrics: dict[str, Any], image_size: tuple[int, int]) -> dict[str, Any]:
    width, height = image_size
    x1, y1, x2, y2 = detection["xyxy"]
    area_fraction = ((x2 - x1) * (y2 - y1)) / max(1.0, width * height)
    width_fraction = (x2 - x1) / max(1.0, width)
    height_fraction = (y2 - y1) / max(1.0, height)
    reject: list[str] = []
    if detection["confidence"] < 0.18:
        reject.append("yolo_conf_lt_0_18")
    if area_fraction < 0.20:
        reject.append("animal_area_lt_0_20")
    if min(width_fraction, height_fraction) < 0.24:
        reject.append("animal_box_dimension_too_small")
    if metrics["animal_crop_width"] < 260 or metrics["animal_crop_height"] < 260:
        reject.append("animal_crop_dimension_lt_260")
    if metrics["animal_crop_megapixels"] < 0.10:
        reject.append("animal_crop_megapixels_lt_0_10")
    if metrics["animal_crop_laplacian_var"] < 1400:
        reject.append("animal_crop_motion_or_soft_laplacian_lt_1400")
    if metrics["animal_crop_gradient_p90"] < 38:
        reject.append("animal_crop_weak_edges_lt_38")
    if metrics["animal_crop_contrast_std"] < 48:
        reject.append("animal_crop_low_contrast_lt_48")
    if metrics["animal_crop_brightness_mean"] < 60:
        reject.append("animal_crop_too_dark_or_night")
    if metrics["animal_crop_saturation_mean"] < 22 or metrics["animal_crop_grayscale_proxy"] > 0.80:
        reject.append("animal_crop_low_color_or_ir")
    if metrics["animal_crop_entropy"] < 5.3:
        reject.append("animal_crop_low_entropy")

    score = 0.0
    score += min(30.0, area_fraction * 100.0)
    score += min(16.0, detection["confidence"] * 20.0)
    score += min(16.0, metrics["animal_crop_laplacian_var"] / 180.0)
    score += min(14.0, metrics["animal_crop_gradient_p90"] / 4.0)
    score += min(12.0, metrics["animal_crop_contrast_std"] / 5.0)
    score += min(8.0, metrics["animal_crop_entropy"])
    score += min(6.0, metrics["animal_crop_megapixels"] * 20.0)

    out = {field: "" for field in OUTPUT_FIELDS}
    for field in [
        "phase19_review_id",
        "phase19_cell",
        "source_dataset",
        "source_platform",
        "source_candidate_id",
        "source_image_path",
        "source_image_uri",
        "species",
        "domain_label",
        "license",
        "attribution",
        "image_width",
        "image_height",
    ]:
        out[field] = row.get(field, "")
    out.update(metrics)
    out["yolo_class"] = detection["class"]
    out["yolo_confidence"] = round(float(detection["confidence"]), 6)
    out["animal_bbox_x1"] = round(x1, 2)
    out["animal_bbox_y1"] = round(y1, 2)
    out["animal_bbox_x2"] = round(x2, 2)
    out["animal_bbox_y2"] = round(y2, 2)
    out["animal_area_fraction"] = round(area_fraction, 6)
    out["animal_width_fraction"] = round(width_fraction, 6)
    out["animal_height_fraction"] = round(height_fraction, 6)
    out["object_aware_score"] = round(score, 4)
    out["object_aware_decision"] = "keep" if not reject else "reject"
    out["object_aware_reject_reasons"] = ";".join(reject)
    out["phase19_claim_boundary"] = "YOLO object-aware candidate only; final inclusion still requires human CLEAR"
    return out


def process_pool(model: YOLO, pool: str, limit: int | None, imgsz: int, batch: int, chunk_size: int) -> list[dict[str, Any]]:
    rows = input_rows_for_pool(pool)
    if limit:
        rows = rows[:limit]
    outputs: list[dict[str, Any]] = []
    processed = 0
    for start in range(0, len(rows), chunk_size):
        chunk_rows = rows[start : start + chunk_size]
        paths = [str(PROJECT_ROOT / row["source_image_path"]) for row in chunk_rows]
        for offset, result in enumerate(model.predict(paths, stream=True, imgsz=imgsz, conf=0.10, batch=batch, verbose=False)):
            row = chunk_rows[offset]
            detection = best_detection(result)
            if detection is None:
                out = {field: "" for field in OUTPUT_FIELDS}
                for field in out:
                    if field in row:
                        out[field] = row[field]
                out["object_aware_decision"] = "reject"
                out["object_aware_reject_reasons"] = "no_yolo_animal_box"
                outputs.append(out)
            else:
                image_path = PROJECT_ROOT / row["source_image_path"]
                with Image.open(image_path) as image:
                    image = image.convert("RGB")
                    width, height = image.size
                    x1, y1, x2, y2 = detection["xyxy"]
                    box = (
                        max(0, int(math.floor(x1))),
                        max(0, int(math.floor(y1))),
                        min(width, int(math.ceil(x2))),
                        min(height, int(math.ceil(y2))),
                    )
                    metrics = crop_metrics(image, box)
                    outputs.append(score_candidate(row, detection, metrics, (width, height)))
            processed += 1
            if processed % 250 == 0:
                print(f"{pool}: YOLO processed {processed}/{len(rows)}", flush=True)
    return outputs


def validation_sample(rows: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    kept = [row for row in rows if row.get("object_aware_decision") == "keep"]
    kept.sort(key=lambda row: -safe_float(row.get("object_aware_score")))
    if len(kept) <= n:
        return kept
    indexes = sorted({round(i * (len(kept) - 1) / (n - 1)) for i in range(n)})
    return [kept[index] for index in indexes]


def build(args: argparse.Namespace) -> None:
    out_dir = Path(args.output_dir) if args.output_dir else OUT_DIR
    if not out_dir.is_absolute():
        out_dir = PROJECT_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(MODEL_PATH))
    audit: dict[str, Any] = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": str(MODEL_PATH.relative_to(PROJECT_ROOT)),
        "logic": "Keep only images with a YOLO animal box >=20% and sharp/clear animal crop metrics.",
        "pools": {},
    }
    combined_sample: list[dict[str, Any]] = []
    for pool in args.pools:
        rows = process_pool(model, pool, args.limit_per_pool, args.imgsz, args.batch, args.chunk_size)
        rows.sort(key=lambda row: (row.get("object_aware_decision") != "keep", -safe_float(row.get("object_aware_score"))))
        kept = [row for row in rows if row.get("object_aware_decision") == "keep"]
        sample = validation_sample(rows, args.sample_per_pool)
        combined_sample.extend(sample)
        write_csv(out_dir / f"{pool}_object_aware_all_scored.csv", rows)
        write_csv(out_dir / f"{pool}_object_aware_keep_candidates.csv", kept)
        write_csv(out_dir / f"{pool}_object_aware_sample{args.sample_per_pool}.csv", sample)
        reason_counts = Counter()
        for row in rows:
            reasons = row.get("object_aware_reject_reasons") or "none"
            for reason in str(reasons).split(";"):
                reason_counts[reason] += 1
        audit["pools"][pool] = {
            "scored_rows": len(rows),
            "kept_rows": len(kept),
            "sample_rows": len(sample),
            "decision_counts": dict(Counter(row.get("object_aware_decision", "") for row in rows)),
            "reject_reason_counts": dict(reason_counts.most_common(30)),
        }
    write_csv(out_dir / "phase19_object_aware_validation_sample_combined.csv", combined_sample)
    audit["combined_sample_rows"] = len(combined_sample)
    audit["combined_sample_csv"] = str((out_dir / "phase19_object_aware_validation_sample_combined.csv").relative_to(PROJECT_ROOT))
    (out_dir / "phase19_object_aware_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote object-aware Phase19 candidates to {out_dir.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pools", nargs="+", choices=POOLS, default=POOLS)
    parser.add_argument("--limit-per-pool", type=int, default=0, help="debug limit; 0 means all input rows")
    parser.add_argument("--sample-per-pool", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--chunk-size", type=int, default=64)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()
    args.limit_per_pool = args.limit_per_pool or None
    return args


if __name__ == "__main__":
    build(parse_args())
