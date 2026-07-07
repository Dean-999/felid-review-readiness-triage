#!/usr/bin/env python3
"""Apply a bobcat bbox area >=10% gate to the Phase19 iNat clarity queue."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from PIL import Image
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_bobcat_inat_clarity_second_pass/phase19_bobcat_inat_clarity_second_pass_review_queue.csv"
)
MODEL_PATH = PROJECT_ROOT / "models/phase19/yolo26s_finetuned_bobcat_by_J.Gong_uwyo_2026-05-28.pt"
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_inat_area10_gate"
CACHE_DIR = PROJECT_ROOT / "data/phase19_cache/inat_bobcat_area10_images"
SCORED_CSV = OUT_DIR / "phase19_bobcat_inat_area10_all_scored.csv"
QUEUE_CSV = OUT_DIR / "phase19_bobcat_inat_area10_review_queue.csv"
SAMPLE_CSV = OUT_DIR / "phase19_bobcat_inat_area10_sample100.csv"
AUDIT_JSON = OUT_DIR / "phase19_bobcat_inat_area10_audit.json"

EXTRA_FIELDS = [
    "phase19_area10_detector_model",
    "phase19_area10_detection_status",
    "phase19_area10_confidence",
    "phase19_area10_bbox_x1",
    "phase19_area10_bbox_y1",
    "phase19_area10_bbox_x2",
    "phase19_area10_bbox_y2",
    "phase19_area10_bbox_width_fraction",
    "phase19_area10_bbox_height_fraction",
    "phase19_area10_area_fraction",
    "phase19_area10_area_bin",
    "phase19_area10_gate_decision",
    "phase19_area10_gate_reason",
    "phase19_area10_local_image_path",
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


def cache_path_for(url: str) -> Path:
    suffix = Path(url.split("?")[0]).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{digest}{suffix}"


def download_image(url: str, timeout: int) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_path_for(url)
    if path.exists() and path.stat().st_size > 0:
        return path
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "felid-phase19-area10/0.1"})
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            image.save(path, quality=95)
            return path
        except Exception as error:
            last_error = error
            time.sleep(1.2 * attempt)
    raise RuntimeError(f"download failed: {last_error}")


def area_bin(area: float | None) -> str:
    if area is None:
        return "unknown"
    if area < 0.10:
        return "lt_10pct"
    if area < 0.15:
        return "10_15pct"
    if area < 0.20:
        return "15_20pct"
    if area < 0.30:
        return "20_30pct"
    return "ge_30pct"


def score_one(model: YOLO, row: dict[str, str], timeout: int, conf: float, imgsz: int) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    for field in EXTRA_FIELDS:
        out[field] = ""
    out["phase19_area10_detector_model"] = str(MODEL_PATH.relative_to(PROJECT_ROOT))
    try:
        image_path = download_image(row["source_image_uri"], timeout=timeout)
        out["phase19_area10_local_image_path"] = str(image_path.relative_to(PROJECT_ROOT))
        with Image.open(image_path) as image:
            width, height = image.size
        result = model.predict(str(image_path), conf=conf, imgsz=imgsz, verbose=False)[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            out["phase19_area10_detection_status"] = "no_detection"
            out["phase19_area10_gate_decision"] = "reject_area_proxy"
            out["phase19_area10_gate_reason"] = "no_bobcat_detection"
            out["phase19_area10_area_bin"] = "unknown"
            return out
        best: dict[str, float] | None = None
        for box in boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            confidence = float(box.conf[0])
            area = max(0.0, x2 - x1) * max(0.0, y2 - y1) / max(1.0, float(width * height))
            candidate = {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "confidence": confidence,
                "area": area,
            }
            if best is None or (area, confidence) > (best["area"], best["confidence"]):
                best = candidate
        assert best is not None
        area = best["area"]
        out["phase19_area10_detection_status"] = "detected"
        out["phase19_area10_confidence"] = f"{best['confidence']:.6f}"
        out["phase19_area10_bbox_x1"] = f"{best['x1']:.2f}"
        out["phase19_area10_bbox_y1"] = f"{best['y1']:.2f}"
        out["phase19_area10_bbox_x2"] = f"{best['x2']:.2f}"
        out["phase19_area10_bbox_y2"] = f"{best['y2']:.2f}"
        out["phase19_area10_bbox_width_fraction"] = f"{max(0.0, best['x2'] - best['x1']) / max(1.0, width):.8f}"
        out["phase19_area10_bbox_height_fraction"] = f"{max(0.0, best['y2'] - best['y1']) / max(1.0, height):.8f}"
        out["phase19_area10_area_fraction"] = f"{area:.8f}"
        out["phase19_area10_area_bin"] = area_bin(area)
        if area >= 0.10:
            out["phase19_area10_gate_decision"] = "keep_area_ge_10pct"
            out["phase19_area10_gate_reason"] = ""
        else:
            out["phase19_area10_gate_decision"] = "reject_area_proxy"
            out["phase19_area10_gate_reason"] = "detected_area_lt_10pct"
        return out
    except Exception as error:
        out["phase19_area10_detection_status"] = "error"
        out["phase19_area10_gate_decision"] = "reject_area_proxy"
        out["phase19_area10_gate_reason"] = f"{type(error).__name__}: {str(error)[:160]}"
        out["phase19_area10_area_bin"] = "unknown"
        return out


def initialized_row(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    for field in EXTRA_FIELDS:
        out[field] = ""
    out["phase19_area10_detector_model"] = str(MODEL_PATH.relative_to(PROJECT_ROOT))
    return out


def prepare_download(row: dict[str, str], timeout: int) -> dict[str, Any]:
    out = initialized_row(row)
    try:
        image_path = download_image(row["source_image_uri"], timeout=timeout)
        out["phase19_area10_local_image_path"] = str(image_path.relative_to(PROJECT_ROOT))
        with Image.open(image_path) as image:
            width, height = image.size
        out["_local_path_abs"] = str(image_path)
        out["_image_width_det"] = width
        out["_image_height_det"] = height
    except Exception as error:
        out["phase19_area10_detection_status"] = "error"
        out["phase19_area10_gate_decision"] = "reject_area_proxy"
        out["phase19_area10_gate_reason"] = f"{type(error).__name__}: {str(error)[:160]}"
        out["phase19_area10_area_bin"] = "unknown"
    return out


def apply_detection_result(row: dict[str, Any], result: Any) -> dict[str, Any]:
    width = float(row.get("_image_width_det") or row.get("image_width") or 0)
    height = float(row.get("_image_height_det") or row.get("image_height") or 0)
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        row["phase19_area10_detection_status"] = "no_detection"
        row["phase19_area10_gate_decision"] = "reject_area_proxy"
        row["phase19_area10_gate_reason"] = "no_bobcat_detection"
        row["phase19_area10_area_bin"] = "unknown"
        return row
    best: dict[str, float] | None = None
    for box in boxes:
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
        confidence = float(box.conf[0])
        area = max(0.0, x2 - x1) * max(0.0, y2 - y1) / max(1.0, width * height)
        candidate = {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "confidence": confidence,
            "area": area,
        }
        if best is None or (area, confidence) > (best["area"], best["confidence"]):
            best = candidate
    assert best is not None
    area = best["area"]
    row["phase19_area10_detection_status"] = "detected"
    row["phase19_area10_confidence"] = f"{best['confidence']:.6f}"
    row["phase19_area10_bbox_x1"] = f"{best['x1']:.2f}"
    row["phase19_area10_bbox_y1"] = f"{best['y1']:.2f}"
    row["phase19_area10_bbox_x2"] = f"{best['x2']:.2f}"
    row["phase19_area10_bbox_y2"] = f"{best['y2']:.2f}"
    row["phase19_area10_bbox_width_fraction"] = f"{max(0.0, best['x2'] - best['x1']) / max(1.0, width):.8f}"
    row["phase19_area10_bbox_height_fraction"] = f"{max(0.0, best['y2'] - best['y1']) / max(1.0, height):.8f}"
    row["phase19_area10_area_fraction"] = f"{area:.8f}"
    row["phase19_area10_area_bin"] = area_bin(area)
    if area >= 0.10:
        row["phase19_area10_gate_decision"] = "keep_area_ge_10pct"
        row["phase19_area10_gate_reason"] = ""
    else:
        row["phase19_area10_gate_decision"] = "reject_area_proxy"
        row["phase19_area10_gate_reason"] = "detected_area_lt_10pct"
    return row


def score_rows_batch(
    model: YOLO,
    rows: list[dict[str, str]],
    timeout: int,
    conf: float,
    imgsz: int,
    batch: int,
    workers: int,
) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(prepare_download, row, timeout) for row in rows]
        for index, future in enumerate(as_completed(futures), start=1):
            prepared.append(future.result())
            if index % 100 == 0:
                print(f"downloaded_or_cached={index}/{len(rows)}", flush=True)
    ready = [row for row in prepared if row.get("_local_path_abs")]
    paths = [row["_local_path_abs"] for row in ready]
    for start in range(0, len(paths), batch):
        chunk = paths[start : start + batch]
        results = model.predict(chunk, conf=conf, imgsz=imgsz, batch=batch, verbose=False)
        for offset, result in enumerate(results):
            row = ready[start + offset]
            apply_detection_result(row, result)
        print(f"area_detected={min(start + batch, len(paths))}/{len(paths)}", flush=True)
    for row in prepared:
        for key in ["_local_path_abs", "_image_width_det", "_image_height_det"]:
            row.pop(key, None)
    return prepared


def sort_key(row: dict[str, Any]) -> tuple[int, float, float, str]:
    tier_rank = {
        "tier1_second_pass_high_clarity": 0,
        "tier2_second_pass_clear_review": 1,
    }.get(str(row.get("phase19_clarity_second_pass_tier", "")), 9)
    return (
        tier_rank,
        -f(row, "phase19_area10_area_fraction"),
        -f(row, "phase19_clarity_second_pass_score"),
        str(row.get("phase19_review_id", "")),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", type=Path, default=INPUT_CSV)
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--conf", type=float, default=0.20)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.model.exists():
        raise FileNotFoundError(f"Missing detector model: {args.model}")
    global MODEL_PATH
    MODEL_PATH = args.model
    rows = read_csv(args.input_csv)
    if args.limit:
        rows = rows[: args.limit]
    model = YOLO(str(args.model))
    scored = score_rows_batch(
        model,
        rows,
        timeout=args.timeout,
        conf=args.conf,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
    )
    kept = [row for row in scored if row.get("phase19_area10_gate_decision") == "keep_area_ge_10pct"]
    kept.sort(key=sort_key)
    fieldnames = list(scored[0].keys()) if scored else []
    for field in EXTRA_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(SCORED_CSV, scored, fieldnames)
    write_csv(QUEUE_CSV, kept, fieldnames)
    write_csv(SAMPLE_CSV, kept[:100], fieldnames)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_csv": str(args.input_csv.relative_to(PROJECT_ROOT)),
        "input_rows": len(rows),
        "model": str(args.model.relative_to(PROJECT_ROOT)),
        "conf": args.conf,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "workers": args.workers,
        "scored_rows": len(scored),
        "kept_area_ge_10pct_rows": len(kept),
        "rejected_rows": len(scored) - len(kept),
        "detection_status_counts": dict(Counter(row.get("phase19_area10_detection_status", "") for row in scored)),
        "area_bin_counts": dict(Counter(row.get("phase19_area10_area_bin", "") for row in scored)),
        "kept_second_pass_tier_counts": dict(Counter(row.get("phase19_clarity_second_pass_tier", "") for row in kept)),
        "reject_reason_counts": dict(Counter(row.get("phase19_area10_gate_reason", "") or "none" for row in scored).most_common(30)),
        "outputs": {
            "all_scored_csv": str(SCORED_CSV.relative_to(PROJECT_ROOT)),
            "queue_csv": str(QUEUE_CSV.relative_to(PROJECT_ROOT)),
            "sample_csv": str(SAMPLE_CSV.relative_to(PROJECT_ROOT)),
            "audit_json": str(AUDIT_JSON.relative_to(PROJECT_ROOT)),
        },
        "claim_boundary": "Detector area proxy only; human review must still confirm actual visible bobcat body size and completeness.",
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
