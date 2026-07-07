#!/usr/bin/env python3
"""Build a pixel-based Bobcat-wild clarity queue.

This re-scores the body-gate queue by reading pixels from the original images.
It avoids fixed absolute thresholds as much as possible: images are ranked by
within-dataset percentiles of multi-scale sharpness and high-frequency detail.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image, ImageFilter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_wild_body_gate/bobcat_wild_blur_pass_body_gate_queue.csv"
OUT_DIR = PROJECT_ROOT / "outputs/phase19/phase19_bobcat_wild_pixel_clarity_v2"


def laplacian_variance(gray: np.ndarray) -> float:
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    lap = (
        -4.0 * gray[1:-1, 1:-1]
        + gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
    )
    return float(np.var(lap))


def gradient_metrics(gray: np.ndarray) -> tuple[float, float, float]:
    if gray.shape[0] < 2 or gray.shape[1] < 2:
        return 0.0, 0.0, 0.0
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    grad = np.sqrt(dx[:-1, :] ** 2 + dy[:, :-1] ** 2)
    return float(np.mean(grad)), float(np.percentile(grad, 90)), float(np.mean(grad > 18.0))


def local_contrast(gray: np.ndarray, grid: int = 8) -> float:
    h, w = gray.shape
    values: list[float] = []
    for y0 in np.linspace(0, h, grid + 1, dtype=int)[:-1]:
        y1 = min(h, y0 + max(1, h // grid))
        for x0 in np.linspace(0, w, grid + 1, dtype=int)[:-1]:
            x1 = min(w, x0 + max(1, w // grid))
            tile = gray[y0:y1, x0:x1]
            if tile.size:
                values.append(float(np.std(tile)))
    return float(np.median(values)) if values else 0.0


def pixel_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        resized = image.copy()
        resized.thumbnail((768, 768))
        gray_image = resized.convert("L")
        blurred = gray_image.filter(ImageFilter.GaussianBlur(radius=1.4))
        gray = np.asarray(gray_image, dtype=np.float32)
        blur_gray = np.asarray(blurred, dtype=np.float32)
        grad_mean, grad_p90, edge_density = gradient_metrics(gray)

        cx0 = int(gray.shape[1] * 0.10)
        cx1 = int(gray.shape[1] * 0.90)
        cy0 = int(gray.shape[0] * 0.10)
        cy1 = int(gray.shape[0] * 0.90)
        center = gray[cy0:cy1, cx0:cx1]
        c_grad_mean, c_grad_p90, c_edge_density = gradient_metrics(center)

        return {
            "pixel_width": width,
            "pixel_height": height,
            "pixel_megapixels": round((width * height) / 1_000_000, 4),
            "pixel_laplacian_var": round(laplacian_variance(gray), 4),
            "pixel_gradient_mean": round(grad_mean, 4),
            "pixel_gradient_p90": round(grad_p90, 4),
            "pixel_edge_density": round(edge_density, 6),
            "pixel_highfreq_residual_std": round(float(np.std(gray - blur_gray)), 4),
            "pixel_local_contrast_median": round(local_contrast(gray), 4),
            "pixel_center_laplacian_var": round(laplacian_variance(center), 4),
            "pixel_center_gradient_mean": round(c_grad_mean, 4),
            "pixel_center_gradient_p90": round(c_grad_p90, 4),
            "pixel_center_edge_density": round(c_edge_density, 6),
        }


def rank01(series: pd.Series) -> pd.Series:
    return series.rank(method="average", pct=True).fillna(0.0)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(INPUT, dtype=str, keep_default_na=False)
    metric_rows: list[dict[str, Any]] = []
    total = len(frame)
    for index, row in frame.iterrows():
        path = PROJECT_ROOT / row["source_image_path"]
        metrics: dict[str, Any]
        try:
            metrics = pixel_metrics(path)
            metrics["pixel_metric_error"] = ""
        except Exception as error:
            metrics = {"pixel_metric_error": f"{type(error).__name__}: {str(error)[:120]}"}
        metric_rows.append(metrics)
        if (index + 1) % 1000 == 0:
            print(f"pixel-scored {index + 1}/{total}", flush=True)

    metrics_df = pd.DataFrame(metric_rows)
    out = pd.concat([frame.reset_index(drop=True), metrics_df], axis=1)
    numeric_cols = [
        "pixel_laplacian_var",
        "pixel_gradient_p90",
        "pixel_edge_density",
        "pixel_highfreq_residual_std",
        "pixel_local_contrast_median",
        "pixel_center_laplacian_var",
        "pixel_center_gradient_p90",
        "pixel_center_edge_density",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["pixel_full_sharp_rank"] = (
        0.35 * rank01(out["pixel_laplacian_var"])
        + 0.25 * rank01(out["pixel_gradient_p90"])
        + 0.20 * rank01(out["pixel_highfreq_residual_std"])
        + 0.10 * rank01(out["pixel_edge_density"])
        + 0.10 * rank01(out["pixel_local_contrast_median"])
    )
    out["pixel_center_sharp_rank"] = (
        0.45 * rank01(out["pixel_center_laplacian_var"])
        + 0.35 * rank01(out["pixel_center_gradient_p90"])
        + 0.20 * rank01(out["pixel_center_edge_density"])
    )
    out["pixel_clarity_score"] = (
        100.0
        * (
            0.72 * out["pixel_full_sharp_rank"]
            + 0.28 * out["pixel_center_sharp_rank"]
            + 0.05 * rank01(pd.to_numeric(out.get("pixel_megapixels", 0), errors="coerce"))
        )
        / 1.05
    ).round(4)

    out["pixel_clarity_tier"] = pd.cut(
        out["pixel_clarity_score"],
        bins=[-math.inf, 30, 50, 70, 85, math.inf],
        labels=[
            "pixel_tier5_low_clarity",
            "pixel_tier4_manual_check",
            "pixel_tier3_moderate",
            "pixel_tier2_high",
            "pixel_tier1_very_high",
        ],
    ).astype(str)

    out = out.sort_values(["pixel_clarity_score", "pixel_laplacian_var"], ascending=[False, False])
    all_path = OUT_DIR / "bobcat_wild_pixel_clarity_v2_all_scored.csv"
    queue_path = OUT_DIR / "bobcat_wild_pixel_clarity_v2_review_queue_top70pct.csv"
    out.to_csv(all_path, index=False)

    cutoff = float(out["pixel_clarity_score"].quantile(0.30))
    queue = out[out["pixel_clarity_score"].ge(cutoff)].copy()
    queue["phase19_manual_decision"] = ""
    queue["phase19_manual_reject_reason"] = ""
    queue["phase19_manual_notes"] = ""
    queue["phase19_manual_audited_at_utc"] = ""
    queue.to_csv(queue_path, index=False)

    audit = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_body_gate_rows": int(len(frame)),
        "all_scored_rows": int(len(out)),
        "review_queue_top70pct_rows": int(len(queue)),
        "pixel_score_cutoff_top70pct": cutoff,
        "counts_by_cutoff": {
            "top50pct": int(out["pixel_clarity_score"].ge(float(out["pixel_clarity_score"].quantile(0.50))).sum()),
            "top60pct": int(out["pixel_clarity_score"].ge(float(out["pixel_clarity_score"].quantile(0.40))).sum()),
            "top70pct": int(len(queue)),
            "top80pct": int(out["pixel_clarity_score"].ge(float(out["pixel_clarity_score"].quantile(0.20))).sum()),
        },
        "tier_counts": out["pixel_clarity_tier"].value_counts().to_dict(),
        "source_counts_top70pct": queue["source_dataset"].value_counts().to_dict(),
        "outputs": {
            "all_scored": str(all_path.relative_to(PROJECT_ROOT)),
            "review_queue_top70pct": str(queue_path.relative_to(PROJECT_ROOT)),
        },
        "principle": "Pixel-based clarity ranking only; no fixed source/model/YOLO exclusion and no final acceptance claim.",
    }
    (OUT_DIR / "bobcat_wild_pixel_clarity_v2_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
