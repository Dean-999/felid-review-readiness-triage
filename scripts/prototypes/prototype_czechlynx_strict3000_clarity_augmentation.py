#!/usr/bin/env python3
"""PROTOTYPE: apply mild clarity augmentation to confirmed CzechLynx strict 3000.

Question:
After human review says the strict CzechLynx 3000 is visually acceptable, can we
produce an algorithm-entry manifest with lightly enhanced image copies while
preserving the original evidence chain?

This is throwaway prototype code. It does not invent information, crop animals,
or change labels. It creates full-frame copies with mild contrast/sharpness
enhancement and records the original path beside every augmented path.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CSV = (
    PROJECT_ROOT
    / "outputs/czechlynx/phase17_strict3000_supplement/phase17_czechlynx_strict3000_review_queue.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase17_strict3000_supplement/augmented"
IMAGE_DIR = OUTPUT_DIR / "images"
AUGMENTED_MANIFEST = OUTPUT_DIR / "phase17_czechlynx_strict3000_augmented_manifest.csv"
FINAL_CONFIRMED_MANIFEST = OUTPUT_DIR / "phase17_czechlynx_strict3000_final_confirmed_manifest.csv"
AUDIT_JSON = OUTPUT_DIR / "phase17_czechlynx_strict3000_clarity_augmentation_audit.json"
NOTES_MD = OUTPUT_DIR / "NOTES.md"


def read_csv(path: Path) -> list[dict[str, str]]:
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


def resolve_image_path(row: dict[str, str]) -> Path:
    for key in ["local_image_path", "image_uri"]:
        value = (row.get(key) or "").strip()
        if not value:
            continue
        path = Path(value)
        if path.exists():
            return path
        rooted = PROJECT_ROOT / value
        if rooted.exists():
            return rooted
    raise FileNotFoundError(row.get("candidate_id") or row.get("dedupe_key") or "unknown row")


def stable_output_path(row: dict[str, str], source_path: Path) -> Path:
    rank_text = row.get("phase17_strict3000_rank") or "0"
    try:
        rank = int(float(rank_text))
    except ValueError:
        rank = 0
    candidate = (row.get("candidate_id") or "czechlynx").replace("/", "_")[:64]
    digest = hashlib.sha1(str(source_path).encode("utf-8")).hexdigest()[:12]
    return IMAGE_DIR / f"czlx_final_{rank:04d}__{candidate}__{digest}.jpg"


def enhance_image(source_path: Path, output_path: Path) -> dict[str, Any]:
    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        original_width, original_height = image.size
        enhanced = ImageEnhance.Contrast(image).enhance(1.06)
        enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.25)
        enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1.0, percent=80, threshold=3))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        enhanced.save(output_path, format="JPEG", quality=94, subsampling=0, optimize=True)
    return {
        "original_width": original_width,
        "original_height": original_height,
        "augmented_width": original_width,
        "augmented_height": original_height,
        "augmented_file_bytes": output_path.stat().st_size,
    }


def process_row(index: int, row: dict[str, str]) -> dict[str, Any]:
    source_path = resolve_image_path(row)
    output_path = stable_output_path(row, source_path)
    metrics = enhance_image(source_path, output_path)
    out = dict(row)
    out.update(metrics)
    out.update(
        {
            "phase17_clarity_augmentation_status": "ok",
            "phase17_clarity_augmentation_type": "full_frame_mild_contrast_sharpness_unsharp_mask",
            "phase17_clarity_augmentation_parameters": (
                "contrast=1.06;sharpness=1.25;"
                "unsharp_mask_radius=1.0;unsharp_mask_percent=80;"
                "unsharp_mask_threshold=3;jpeg_quality=94;subsampling=0"
            ),
            "phase17_clarity_augmentation_boundary": (
                "readability_preprocessing_only_original_image_remains_source_of_truth"
            ),
            "original_image_path": str(source_path),
            "augmented_image_path": str(output_path),
            "algorithm_entry_image_path": str(output_path),
            "human_confirmed_quality_decision": "clear",
            "human_confirmed_quality_basis": (
                "user_reviewed_strict3000_queue_and_requested_clarity_augmentation_before_finalization"
            ),
            "phase17_final3000_status": "human_clear_augmented_ready_for_freeze",
            "phase17_final3000_order": index + 1,
        }
    )
    return out


def build(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_csv(Path(args.source_csv))
    if not rows:
        raise RuntimeError(f"no rows in {args.source_csv}")
    if args.target_count and len(rows) != args.target_count:
        raise RuntimeError(f"expected {args.target_count} rows, found {len(rows)}")

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    augmented: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_row, index, row): index for index, row in enumerate(rows)}
        for future in as_completed(futures):
            index = futures[future]
            try:
                augmented.append(future.result())
            except Exception as error:
                errors.append(
                    {
                        "row_index": str(index),
                        "candidate_id": rows[index].get("candidate_id", ""),
                        "error_type": type(error).__name__,
                        "error": str(error)[:300],
                    }
                )

    if errors:
        error_path = OUTPUT_DIR / "phase17_czechlynx_strict3000_clarity_augmentation_errors.csv"
        write_csv(error_path, errors, ["row_index", "candidate_id", "error_type", "error"])
        raise RuntimeError(f"augmentation failed for {len(errors)} rows; see {error_path}")

    augmented.sort(key=lambda row: int(row.get("phase17_final3000_order") or 0))
    source_fields = list(rows[0].keys())
    extra_fields = [
        "phase17_clarity_augmentation_status",
        "phase17_clarity_augmentation_type",
        "phase17_clarity_augmentation_parameters",
        "phase17_clarity_augmentation_boundary",
        "original_image_path",
        "augmented_image_path",
        "algorithm_entry_image_path",
        "original_width",
        "original_height",
        "augmented_width",
        "augmented_height",
        "augmented_file_bytes",
        "human_confirmed_quality_decision",
        "human_confirmed_quality_basis",
        "phase17_final3000_status",
        "phase17_final3000_order",
    ]
    fieldnames = source_fields + [field for field in extra_fields if field not in source_fields]
    write_csv(AUGMENTED_MANIFEST, augmented, fieldnames)
    write_csv(FINAL_CONFIRMED_MANIFEST, augmented, fieldnames)

    augmented_paths = [Path(row["augmented_image_path"]) for row in augmented]
    missing_outputs = [str(path) for path in augmented_paths if not path.exists()]
    audit = {
        "built_at_utc": built_at,
        "source_csv": str(Path(args.source_csv)),
        "augmented_manifest": str(AUGMENTED_MANIFEST),
        "final_confirmed_manifest": str(FINAL_CONFIRMED_MANIFEST),
        "source_rows": len(rows),
        "augmented_rows": len(augmented),
        "missing_augmented_files": len(missing_outputs),
        "unique_dedupe_keys": len({row.get("dedupe_key", "") for row in augmented if row.get("dedupe_key")}),
        "strict_gate_pass_counts": dict(Counter(row.get("strict_gate_pass", "") for row in augmented)),
        "final_status_counts": dict(Counter(row.get("phase17_final3000_status", "") for row in augmented)),
        "source_pool_counts": dict(Counter(row.get("source_pool", "") for row in augmented)),
        "augmentation_type": "full_frame_mild_contrast_sharpness_unsharp_mask",
        "augmentation_parameters": {
            "contrast": 1.06,
            "sharpness": 1.25,
            "unsharp_mask_radius": 1.0,
            "unsharp_mask_percent": 80,
            "unsharp_mask_threshold": 3,
            "jpeg_quality": 94,
            "jpeg_subsampling": 0,
            "crop": "none",
            "resize": "none",
        },
        "claim_boundary": (
            "This confirms a human-reviewed visual-quality-first CzechLynx 3000 with "
            "readability preprocessing. It is not an identity-balanced split and the "
            "original image remains the scientific source of truth."
        ),
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    NOTES_MD.write_text(
        "\n".join(
            [
                "# CzechLynx Strict 3000 Clarity Augmentation",
                "",
                "Question: can the human-reviewed strict CzechLynx 3000 be converted into an algorithm-entry manifest with mild clarity enhancement?",
                "",
                "Answer: yes, if the enhanced copy is treated as readability preprocessing only.",
                "",
                f"Source CSV: `{Path(args.source_csv)}`",
                f"Final confirmed manifest: `{FINAL_CONFIRMED_MANIFEST}`",
                f"Audit JSON: `{AUDIT_JSON}`",
                "",
                "Boundary: no crop, no resize, no label change, and no synthetic evidence. The original image path is retained for every row.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-csv", default=str(SOURCE_CSV))
    parser.add_argument("--target-count", type=int, default=3000)
    parser.add_argument("--workers", type=int, default=16)
    return parser.parse_args()


def main() -> int:
    audit = build(parse_args())
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
