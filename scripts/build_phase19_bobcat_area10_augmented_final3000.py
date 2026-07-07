#!/usr/bin/env python3
"""Create enhanced local images for the Phase19 Bobcat area>=10 final batch."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AREA10_QUEUE = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_bobcat_inat_area10_gate/phase19_bobcat_inat_area10_review_queue.csv"
)
FINAL3000 = (
    PROJECT_ROOT
    / "outputs/phase19/phase19_bobcat_final3000_with_area10_seed/phase19_bobcat_final3000_with_area10_manifest.csv"
)
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_area10_augmented_final3000"
IMAGE_DIR = OUT_DIR / "images"
AREA10_AUGMENTED_CSV = OUT_DIR / "phase19_bobcat_area10_augmented_manifest.csv"
FINAL3000_AUGMENTED_CSV = OUT_DIR / "phase19_bobcat_final3000_with_area10_augmented_manifest.csv"
AUDIT_JSON = OUT_DIR / "phase19_bobcat_area10_augmented_final3000_audit.json"

EXTRA_FIELDS = [
    "phase19_augmented_image_path",
    "phase19_augmented_status",
    "phase19_augmented_error",
    "phase19_augmented_crop_x1",
    "phase19_augmented_crop_y1",
    "phase19_augmented_crop_x2",
    "phase19_augmented_crop_y2",
    "phase19_augmented_width",
    "phase19_augmented_height",
    "phase19_augmented_sha256",
    "phase19_augmented_rule",
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


def rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_source_path(row: dict[str, str]) -> Path:
    path_text = row.get("phase19_area10_local_image_path", "")
    if path_text:
        path = PROJECT_ROOT / path_text
        if path.exists():
            return path
    digest = hashlib.sha256(row["source_image_uri"].encode("utf-8")).hexdigest()[:24]
    path = OUT_DIR / "source_cache" / f"{digest}.jpg"
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(row["source_image_uri"], timeout=45, headers={"User-Agent": "felid-phase19-augment/0.1"})
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def crop_box(row: dict[str, str], width: int, height: int) -> tuple[int, int, int, int]:
    x1 = f(row, "phase19_area10_bbox_x1")
    y1 = f(row, "phase19_area10_bbox_y1")
    x2 = f(row, "phase19_area10_bbox_x2")
    y2 = f(row, "phase19_area10_bbox_y2")
    box_w = max(1.0, x2 - x1)
    box_h = max(1.0, y2 - y1)
    pad = 0.45
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    crop_w = max(box_w * (1.0 + pad * 2.0), min(width, height) * 0.35)
    crop_h = max(box_h * (1.0 + pad * 2.0), min(width, height) * 0.35)
    # Keep moderate context and avoid ultra-thin crops.
    aspect = crop_w / crop_h
    if aspect > 1.6:
        crop_h = crop_w / 1.6
    elif aspect < 0.75:
        crop_w = crop_h * 0.75
    left = max(0.0, cx - crop_w / 2.0)
    top = max(0.0, cy - crop_h / 2.0)
    right = min(float(width), cx + crop_w / 2.0)
    bottom = min(float(height), cy + crop_h / 2.0)
    if right - left < crop_w:
        if left <= 0:
            right = min(float(width), crop_w)
        elif right >= width:
            left = max(0.0, float(width) - crop_w)
    if bottom - top < crop_h:
        if top <= 0:
            bottom = min(float(height), crop_h)
        elif bottom >= height:
            top = max(0.0, float(height) - crop_h)
    return int(round(left)), int(round(top)), int(round(right)), int(round(bottom))


def enhance_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = ImageOps.autocontrast(image, cutoff=0.5)
    image = ImageEnhance.Sharpness(image).enhance(1.45)
    image = ImageEnhance.Contrast(image).enhance(1.08)
    image = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=115, threshold=3))
    max_side = max(image.size)
    if max_side < 1600:
        scale = 1600 / max_side
        image = image.resize((int(round(image.width * scale)), int(round(image.height * scale))), Image.Resampling.LANCZOS)
    return image


def augment_row(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    for field in EXTRA_FIELDS:
        out[field] = ""
    try:
        source_path = local_source_path(row)
        with Image.open(source_path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            left, top, right, bottom = crop_box(row, image.width, image.height)
            cropped = image.crop((left, top, right, bottom))
        enhanced = enhance_image(cropped)
        token = row.get("phase19_review_id", "") or hashlib.sha256(row["source_image_uri"].encode("utf-8")).hexdigest()[:16]
        safe_token = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in token)[:120]
        out_path = IMAGE_DIR / f"{safe_token}.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        enhanced.save(out_path, "JPEG", quality=95, optimize=True)
        out["phase19_augmented_image_path"] = rel(out_path)
        out["phase19_augmented_status"] = "ok"
        out["phase19_augmented_crop_x1"] = str(left)
        out["phase19_augmented_crop_y1"] = str(top)
        out["phase19_augmented_crop_x2"] = str(right)
        out["phase19_augmented_crop_y2"] = str(bottom)
        out["phase19_augmented_width"] = str(enhanced.width)
        out["phase19_augmented_height"] = str(enhanced.height)
        out["phase19_augmented_sha256"] = sha256_file(out_path)
        out["phase19_augmented_rule"] = "bbox_center_crop_pad_45pct_autocontrast_sharpen_unsharp_upscale_min_long_side_1600"
    except Exception as error:
        out["phase19_augmented_status"] = "failed"
        out["phase19_augmented_error"] = f"{type(error).__name__}: {str(error)[:180]}"
    return out


def merge_augmented_into_final(final_rows: list[dict[str, str]], augmented_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_image = {row.get("source_image_uri", "").split("?", 1)[0]: row for row in augmented_rows}
    output: list[dict[str, Any]] = []
    for row in final_rows:
        out: dict[str, Any] = dict(row)
        for field in EXTRA_FIELDS:
            out[field] = ""
        augmented = by_image.get(row.get("image_uri", "").split("?", 1)[0])
        if augmented:
            for field in EXTRA_FIELDS:
                out[field] = augmented.get(field, "")
        output.append(out)
    return output


def main() -> int:
    area_rows = read_csv(AREA10_QUEUE)
    final_rows = read_csv(FINAL3000)
    augmented = [augment_row(row) for row in area_rows]
    area_fields = list(area_rows[0].keys()) + [field for field in EXTRA_FIELDS if field not in area_rows[0]]
    write_csv(AREA10_AUGMENTED_CSV, augmented, area_fields)
    final_augmented = merge_augmented_into_final(final_rows, augmented)
    final_fields = list(final_rows[0].keys()) + [field for field in EXTRA_FIELDS if field not in final_rows[0]]
    write_csv(FINAL3000_AUGMENTED_CSV, final_augmented, final_fields)
    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "area10_input_rows": len(area_rows),
        "area10_augmented_ok": sum(row.get("phase19_augmented_status") == "ok" for row in augmented),
        "area10_augmented_failed": sum(row.get("phase19_augmented_status") == "failed" for row in augmented),
        "final3000_rows": len(final_augmented),
        "final3000_rows_with_augmented_image": sum(bool(row.get("phase19_augmented_image_path")) for row in final_augmented),
        "augmented_status_counts": dict(Counter(row.get("phase19_augmented_status", "") or "not_phase19_area10" for row in final_augmented)),
        "outputs": {
            "area10_augmented_manifest": rel(AREA10_AUGMENTED_CSV),
            "final3000_augmented_manifest": rel(FINAL3000_AUGMENTED_CSV),
            "image_dir": rel(IMAGE_DIR),
            "audit_json": rel(AUDIT_JSON),
        },
        "claim_boundary": "Augmented images are modeling inputs derived from accepted source images; original URLs and source metadata remain retained.",
    }
    AUDIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
