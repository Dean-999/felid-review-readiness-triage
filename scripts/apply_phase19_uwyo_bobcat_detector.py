#!/usr/bin/env python3
"""Apply UWyo HuggingFace Bobcat detector to the Phase19 iNat clean queue."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import requests
from PIL import Image
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_bobcat_inat_daylight_clean_queue/phase19_bobcat_inat_daylight_nonblur_review_queue.csv"
)
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_uwyo_detector_gate"
MODEL_DIR = PROJECT_ROOT / "models/phase19"
MODEL_PATH = MODEL_DIR / "yolo26s_finetuned_bobcat_by_J.Gong_uwyo_2026-05-28.pt"
MODEL_URL = (
    "https://huggingface.co/UWyo/wildlife-bobcat/resolve/main/"
    "yolo26s_finetuned_bobcat_by_J.Gong_uwyo_2026-05-28.pt"
)
SCORED_CSV = OUT_DIR / "phase19_bobcat_inat_uwyo_detector_scored.csv"
REVIEW_CSV = OUT_DIR / "phase19_bobcat_inat_uwyo_detector_review_queue.csv"
SAMPLE_CSV = OUT_DIR / "phase19_bobcat_inat_uwyo_detector_review_sample100.csv"
AUDIT_JSON = OUT_DIR / "phase19_bobcat_uwyo_detector_gate_audit.json"

EXTRA_FIELDS = [
    "uwyo_detector_status",
    "uwyo_detector_confidence",
    "uwyo_bbox_x1",
    "uwyo_bbox_y1",
    "uwyo_bbox_x2",
    "uwyo_bbox_y2",
    "uwyo_bbox_area_fraction",
    "uwyo_bbox_width_fraction",
    "uwyo_bbox_height_fraction",
    "uwyo_bbox_edge_touch",
    "uwyo_crop_laplacian_var",
    "uwyo_crop_gradient_p90",
    "uwyo_crop_contrast_std",
    "uwyo_detector_gate_decision",
    "uwyo_detector_gate_tier",
    "uwyo_detector_gate_reasons",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        text = str(row.get(key, "")).strip()
        if text in {"", "nan", "None"}:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def ensure_model() -> None:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 1_000_000:
        return
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp = MODEL_PATH.with_suffix(".pt.tmp")
    with requests.get(MODEL_URL, stream=True, timeout=120) as response:
        response.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    tmp.replace(MODEL_PATH)


def download_image(url: str, timeout: int) -> Image.Image:
    last_error: Exception | None = None
    variants = [url]
    if "/large." in url:
        variants.extend([url.replace("/large.", "/original."), url.replace("/large.", "/medium.")])
    for candidate in dict.fromkeys(variants):
        try:
            response = requests.get(candidate, timeout=timeout, headers={"User-Agent": "felid-phase19-uwyo-detector"})
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content)).convert("RGB")
        except Exception as error:
            last_error = error
            time.sleep(0.2)
    raise RuntimeError(f"image download failed: {last_error}")


def crop_metrics(image: Image.Image, box: tuple[float, float, float, float]) -> dict[str, float]:
    x1, y1, x2, y2 = [int(round(v)) for v in box]
    x1 = max(0, min(image.width, x1))
    x2 = max(0, min(image.width, x2))
    y1 = max(0, min(image.height, y1))
    y2 = max(0, min(image.height, y2))
    if x2 <= x1 or y2 <= y1:
        return {"crop_laplacian": 0.0, "crop_gradient_p90": 0.0, "crop_contrast": 0.0}
    crop = image.crop((x1, y1, x2, y2)).convert("L")
    crop.thumbnail((768, 768))
    gray = np.asarray(crop, dtype=np.float32)
    if min(gray.shape) < 3:
        return {"crop_laplacian": 0.0, "crop_gradient_p90": 0.0, "crop_contrast": 0.0}
    lap = cv2.Laplacian(gray, cv2.CV_32F)
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    gradient = np.sqrt(dx[:-1, :] ** 2 + dy[:, :-1] ** 2)
    return {
        "crop_laplacian": float(np.var(lap)),
        "crop_gradient_p90": float(np.percentile(gradient, 90)),
        "crop_contrast": float(np.std(gray)),
    }


def best_detection(model: YOLO, image: Image.Image, imgsz: int, conf: float) -> tuple[float, tuple[float, float, float, float]] | None:
    rgb = np.asarray(image)
    results = model.predict(rgb, imgsz=imgsz, conf=conf, verbose=False)
    if not results or results[0].boxes is None or len(results[0].boxes) == 0:
        return None
    boxes = results[0].boxes
    xyxy = boxes.xyxy.cpu().numpy()
    confs = boxes.conf.cpu().numpy()
    best_index = int(np.argmax(confs))
    return float(confs[best_index]), tuple(float(v) for v in xyxy[best_index])


def gate(row: dict[str, Any]) -> tuple[str, str, str]:
    reasons: list[str] = []
    status = row.get("uwyo_detector_status", "")
    if status != "detected":
        return "reject_detector", "no_detector_box", status
    conf = f(row, "uwyo_detector_confidence")
    area = f(row, "uwyo_bbox_area_fraction")
    edge_touch = str(row.get("uwyo_bbox_edge_touch", "")).lower() == "true"
    crop_lap = f(row, "uwyo_crop_laplacian_var")
    crop_grad = f(row, "uwyo_crop_gradient_p90")
    crop_contrast = f(row, "uwyo_crop_contrast_std")
    if conf < 0.25:
        reasons.append("low_detector_confidence")
    if area < 0.10:
        reasons.append("subject_area_lt_10pct")
    if edge_touch:
        reasons.append("bbox_touches_edge_possible_partial")
    if crop_lap < 80:
        reasons.append("crop_low_laplacian_or_soft")
    if crop_grad < 12:
        reasons.append("crop_weak_edges_or_motion_blur")
    if crop_contrast < 28:
        reasons.append("crop_low_contrast")
    if reasons:
        return "reject_detector", "detector_risk", ";".join(reasons)
    if area >= 0.20 and conf >= 0.40 and crop_lap >= 160 and crop_grad >= 18:
        return "review_detector_pass", "tier1_detector_strong", ""
    return "review_detector_pass", "tier2_detector_supported", "human_check_size_or_crop_quality"


def score_rows(args: argparse.Namespace) -> dict[str, Any]:
    ensure_model()
    model = YOLO(str(MODEL_PATH))
    rows = read_csv(args.source_csv)
    if args.limit:
        rows = rows[: args.limit]
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        out = dict(row)
        try:
            image = download_image(row["source_image_uri"], timeout=args.timeout)
            detection = best_detection(model, image, imgsz=args.imgsz, conf=args.conf)
            if detection is None:
                out["uwyo_detector_status"] = "no_detection"
            else:
                confidence, box = detection
                x1, y1, x2, y2 = box
                width = max(1.0, float(image.width))
                height = max(1.0, float(image.height))
                area = max(0.0, x2 - x1) * max(0.0, y2 - y1) / (width * height)
                margin_x = width * 0.025
                margin_y = height * 0.025
                metrics = crop_metrics(image, box)
                out.update(
                    {
                        "uwyo_detector_status": "detected",
                        "uwyo_detector_confidence": f"{confidence:.6f}",
                        "uwyo_bbox_x1": f"{x1:.2f}",
                        "uwyo_bbox_y1": f"{y1:.2f}",
                        "uwyo_bbox_x2": f"{x2:.2f}",
                        "uwyo_bbox_y2": f"{y2:.2f}",
                        "uwyo_bbox_area_fraction": f"{area:.8f}",
                        "uwyo_bbox_width_fraction": f"{max(0.0, x2 - x1) / width:.8f}",
                        "uwyo_bbox_height_fraction": f"{max(0.0, y2 - y1) / height:.8f}",
                        "uwyo_bbox_edge_touch": str(
                            x1 <= margin_x or y1 <= margin_y or x2 >= width - margin_x or y2 >= height - margin_y
                        ).lower(),
                        "uwyo_crop_laplacian_var": f"{metrics['crop_laplacian']:.4f}",
                        "uwyo_crop_gradient_p90": f"{metrics['crop_gradient_p90']:.4f}",
                        "uwyo_crop_contrast_std": f"{metrics['crop_contrast']:.4f}",
                    }
                )
        except Exception as error:
            out["uwyo_detector_status"] = f"error:{type(error).__name__}:{str(error)[:120]}"
        decision, tier, reasons = gate(out)
        out["uwyo_detector_gate_decision"] = decision
        out["uwyo_detector_gate_tier"] = tier
        out["uwyo_detector_gate_reasons"] = reasons
        output.append(out)
        if index % 100 == 0:
            print(f"uwyo_scored={index}/{len(rows)}")
    fieldnames = list(rows[0].keys()) if rows else []
    for field in EXTRA_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)
    review = [row for row in output if row.get("uwyo_detector_gate_decision") == "review_detector_pass"]
    review.sort(
        key=lambda row: (
            {"tier1_detector_strong": 0, "tier2_detector_supported": 1}.get(str(row.get("uwyo_detector_gate_tier", "")), 9),
            -f(row, "uwyo_bbox_area_fraction"),
            -f(row, "uwyo_detector_confidence"),
            str(row.get("phase19_review_id", "")),
        )
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(SCORED_CSV if not args.output_suffix else OUT_DIR / f"phase19_bobcat_inat_uwyo_detector_scored_{args.output_suffix}.csv", output, fieldnames)
    write_csv(REVIEW_CSV if not args.output_suffix else OUT_DIR / f"phase19_bobcat_inat_uwyo_detector_review_queue_{args.output_suffix}.csv", review, fieldnames)
    write_csv(SAMPLE_CSV if not args.output_suffix else OUT_DIR / f"phase19_bobcat_inat_uwyo_detector_review_sample100_{args.output_suffix}.csv", review[:100], fieldnames)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_csv": str(args.source_csv.relative_to(PROJECT_ROOT) if args.source_csv.is_relative_to(PROJECT_ROOT) else args.source_csv),
        "model_repo": "UWyo/wildlife-bobcat",
        "model_file": str(MODEL_PATH.relative_to(PROJECT_ROOT)),
        "model_url": MODEL_URL,
        "input_rows": len(rows),
        "scored_rows": len(output),
        "review_rows": len(review),
        "status_counts": dict(Counter(row.get("uwyo_detector_status", "") for row in output)),
        "gate_decision_counts": dict(Counter(row.get("uwyo_detector_gate_decision", "") for row in output)),
        "gate_tier_counts": dict(Counter(row.get("uwyo_detector_gate_tier", "") for row in output)),
        "top_reject_reason_counts": dict(Counter(row.get("uwyo_detector_gate_reasons", "") for row in output).most_common(30)),
        "parameters": {"imgsz": args.imgsz, "conf": args.conf, "limit": args.limit},
        "claim_boundary": "UWyo detector is a Bobcat bbox/area/crop-quality gate, not final human quality certification.",
    }
    audit_path = AUDIT_JSON if not args.output_suffix else OUT_DIR / f"phase19_bobcat_uwyo_detector_gate_audit_{args.output_suffix}.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", type=Path, default=SOURCE_CSV)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--conf", type=float, default=0.20)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--output-suffix", default="")
    return parser.parse_args()


def main() -> int:
    score_rows(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
