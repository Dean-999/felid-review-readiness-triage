#!/usr/bin/env python3
"""Build automated image prefeatures and provisional labels for FCF bobcat images."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageStat

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data/external/felidae_conservation_fund/manifests/fcf_bobcat_3000_manifest.csv"
OUT_DIR = PROJECT_ROOT / "data/external/felidae_conservation_fund/labels"
DEFAULT_OUT = OUT_DIR / "fcf_bobcat_3000_auto_prefeatures.csv"
DEFAULT_SUMMARY = OUT_DIR / "fcf_bobcat_3000_auto_prefeatures_summary.json"


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def entropy_from_gray(gray: np.ndarray) -> float:
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    prob = hist / max(float(hist.sum()), 1.0)
    prob = prob[prob > 0]
    return float(-(prob * np.log2(prob)).sum())


def edge_density(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 80, 160)
    return float((edges > 0).mean())


def center_saliency(gray: np.ndarray) -> tuple[float, float]:
    h, w = gray.shape
    y0, y1 = int(h * 0.20), int(h * 0.80)
    x0, x1 = int(w * 0.20), int(w * 0.80)
    center = gray[y0:y1, x0:x1]
    border_mask = np.ones_like(gray, dtype=bool)
    border_mask[y0:y1, x0:x1] = False
    border = gray[border_mask]
    center_contrast = abs(float(center.mean()) - float(border.mean())) / 255.0 if border.size else 0.0
    center_edges = edge_density(center)
    return center_contrast, center_edges


def color_metrics(image: Image.Image) -> dict[str, float]:
    rgb = image.convert("RGB")
    stat = ImageStat.Stat(rgb)
    channel_means = np.array(stat.mean, dtype=np.float64)
    channel_stds = np.array(stat.stddev, dtype=np.float64)
    colorfulness = float(np.mean(channel_stds) / 128.0)
    channel_spread = float((channel_means.max() - channel_means.min()) / 255.0)
    return {
        "mean_red": float(channel_means[0]),
        "mean_green": float(channel_means[1]),
        "mean_blue": float(channel_means[2]),
        "channel_spread": channel_spread,
        "colorfulness": colorfulness,
    }


def band(value: float, cuts: list[tuple[float, str]], default: str) -> str:
    if not math.isfinite(value):
        return "unknown"
    for threshold, label in cuts:
        if value <= threshold:
            return label
    return default


def score_row(metrics: dict[str, Any]) -> dict[str, Any]:
    brightness = float(metrics["brightness_mean"])
    contrast = float(metrics["contrast_std"])
    blur = float(metrics["blur_laplacian_var"])
    exposure_bad = float(metrics["underexposed_fraction"] + metrics["overexposed_fraction"])
    center_edges = float(metrics["center_edge_density"])
    center_contrast = float(metrics["center_contrast"])
    colorfulness = float(metrics["colorfulness"])

    night_ir = (
        brightness < 95
        and colorfulness < 0.18
        and float(metrics["channel_spread"]) < 0.12
    )
    blur_score = min(max((math.log1p(blur) - math.log1p(20)) / (math.log1p(900) - math.log1p(20)), 0.0), 1.0)
    exposure_score = min(max(1.0 - exposure_bad * 2.5, 0.0), 1.0)
    contrast_score = min(max((contrast - 20) / 55, 0.0), 1.0)
    center_score = min(max((center_edges / 0.12) * 0.55 + (center_contrast / 0.25) * 0.45, 0.0), 1.0)
    color_score = 0.72 if night_ir else min(max(colorfulness / 0.35, 0.0), 1.0)

    auto_quality_score = float(
        0.28 * blur_score
        + 0.24 * exposure_score
        + 0.18 * contrast_score
        + 0.18 * center_score
        + 0.12 * color_score
    )
    auto_quality_score = min(max(auto_quality_score, 0.0), 1.0)
    auto_evidence_score = float(0.68 * auto_quality_score + 0.32 * center_score)

    if auto_evidence_score >= 0.72:
        review_bucket = "likely_review_ready"
    elif auto_evidence_score >= 0.50:
        review_bucket = "review_limited"
    elif center_score >= 0.30 and exposure_score >= 0.35:
        review_bucket = "defer_manual_check"
    else:
        review_bucket = "likely_species_level_only"

    flags = []
    if blur_score < 0.35:
        flags.append("possible_blur")
    if exposure_score < 0.45:
        flags.append("possible_exposure_issue")
    if contrast_score < 0.35:
        flags.append("low_contrast")
    if center_score < 0.30:
        flags.append("weak_center_animal_signal")
    if night_ir:
        flags.append("likely_night_ir")
    if not flags:
        flags.append("no_major_auto_flag")

    return {
        "auto_night_ir": "yes" if night_ir else "no",
        "auto_blur_band": band(blur_score, [(0.25, "severe"), (0.45, "moderate"), (0.70, "mild")], "none"),
        "auto_exposure_band": band(exposure_score, [(0.35, "poor"), (0.65, "limited"), (0.85, "good")], "strong"),
        "auto_contrast_band": band(contrast_score, [(0.30, "low"), (0.60, "medium")], "high"),
        "auto_center_animal_signal": band(center_score, [(0.25, "weak"), (0.55, "medium")], "strong"),
        "auto_quality_score": auto_quality_score,
        "auto_evidence_score": auto_evidence_score,
        "auto_review_bucket": review_bucket,
        "auto_failure_flags": "|".join(flags),
        "needs_human_review": "yes" if review_bucket in {"review_limited", "defer_manual_check"} else "no",
    }


def resize_for_metrics(image: Image.Image, max_side: int) -> Image.Image:
    if max_side <= 0:
        return image
    width, height = image.size
    largest = max(width, height)
    if largest <= max_side:
        return image
    scale = max_side / largest
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.Resampling.BILINEAR)


def image_metrics(path: Path, max_side: int) -> dict[str, Any]:
    image = Image.open(path).convert("RGB")
    original_width, original_height = image.size
    metric_image = resize_for_metrics(image, max_side=max_side)
    width, height = metric_image.size
    arr = np.asarray(metric_image)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    brightness = float(gray.mean())
    contrast = float(gray.std())
    blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    under = float((gray < 20).mean())
    over = float((gray > 245).mean())
    center_contrast, center_edges = center_saliency(gray)
    color = color_metrics(metric_image)
    metrics = {
        "original_image_width": int(original_width),
        "original_image_height": int(original_height),
        "image_width": int(width),
        "image_height": int(height),
        "brightness_mean": brightness,
        "contrast_std": contrast,
        "blur_laplacian_var": blur_var,
        "entropy": entropy_from_gray(gray),
        "edge_density": edge_density(gray),
        "center_contrast": center_contrast,
        "center_edge_density": center_edges,
        "underexposed_fraction": under,
        "overexposed_fraction": over,
        **color,
    }
    metrics.update(score_row(metrics))
    return metrics


def build(manifest: pd.DataFrame, limit: int | None, max_side: int) -> pd.DataFrame:
    if limit is not None:
        manifest = manifest.head(limit).copy()
    rows: list[dict[str, Any]] = []
    for i, row in manifest.iterrows():
        path = PROJECT_ROOT / str(row["local_relative_path"])
        base = row.to_dict()
        base["image_exists"] = "yes" if path.exists() else "no"
        try:
            if not path.exists():
                raise FileNotFoundError(path)
            base.update(image_metrics(path, max_side=max_side))
            base["auto_prefeature_status"] = "ok"
            base["auto_prefeature_error"] = ""
        except Exception as exc:  # noqa: BLE001 - record image-level failures.
            base["auto_prefeature_status"] = "failed"
            base["auto_prefeature_error"] = repr(exc)
        rows.append(base)
        if (i + 1) % 250 == 0 or (i + 1) == len(manifest):
            print(f"processed {i + 1}/{len(manifest)}")
    return pd.DataFrame(rows)


def write_summary(table: pd.DataFrame, summary_path: Path) -> None:
    ok = table[table["auto_prefeature_status"].eq("ok")].copy()
    summary = {
        "row_count": int(len(table)),
        "ok_count": int(len(ok)),
        "failed_count": int(table["auto_prefeature_status"].eq("failed").sum()),
        "review_bucket_counts": {str(k): int(v) for k, v in ok["auto_review_bucket"].value_counts().sort_index().items()},
        "night_ir_counts": {str(k): int(v) for k, v in ok["auto_night_ir"].value_counts().sort_index().items()},
        "blur_band_counts": {str(k): int(v) for k, v in ok["auto_blur_band"].value_counts().sort_index().items()},
        "evidence_score_summary": {
            "mean": float(ok["auto_evidence_score"].mean()),
            "std": float(ok["auto_evidence_score"].std()),
            "min": float(ok["auto_evidence_score"].min()),
            "median": float(ok["auto_evidence_score"].median()),
            "max": float(ok["auto_evidence_score"].max()),
        },
        "claim_boundary": "machine_prefeatures_for_review_prioritization_not_ground_truth_labels",
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-side", type=int, default=1024, help="Resize longest side before computing metrics.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output = Path(args.output)
    summary = Path(args.summary)
    if not manifest_path.is_absolute():
        manifest_path = PROJECT_ROOT / manifest_path
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    if not summary.is_absolute():
        summary = PROJECT_ROOT / summary

    manifest = pd.read_csv(manifest_path)
    table = build(manifest, args.limit, args.max_side)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output, index=False)
    write_summary(table, summary)
    failed = int(table["auto_prefeature_status"].eq("failed").sum())
    print(
        f"{'PASS' if failed == 0 else 'FAIL'} phase14 FCF bobcat auto prefeatures "
        f"rows={len(table)} failed={failed} output={relative(output)} summary={relative(summary)}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
