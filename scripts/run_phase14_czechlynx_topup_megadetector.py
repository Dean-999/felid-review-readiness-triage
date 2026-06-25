#!/usr/bin/env python3
"""Run MegaDetector on CzechLynx high-confidence top-up candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "outputs/phase14/phase14_czechlynx_high_topup/phase14_czechlynx_high_topup_candidate_manifest.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "outputs/phase14/phase14_czechlynx_high_topup"


def resolve(path_text: object) -> Path:
    path = Path(str(path_text))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def detection_to_row(result: dict[str, Any]) -> dict[str, Any]:
    detections = result.get("detections")
    coords = result.get("normalized_coords") or []
    row: dict[str, Any] = {
        "md_detected": False,
        "md_detection_count": 0,
        "md_best_confidence": 0.0,
        "md_best_class_id": "",
        "md_x0": np.nan,
        "md_y0": np.nan,
        "md_x1": np.nan,
        "md_y1": np.nan,
        "md_width_fraction": 0.0,
        "md_height_fraction": 0.0,
        "md_area_fraction": 0.0,
        "md_aspect_ratio": 0.0,
        "md_edge_touch": False,
        "md_error": "",
    }
    if detections is None or len(getattr(detections, "confidence", [])) == 0 or not coords:
        return row
    confs = list(map(float, detections.confidence))
    class_ids = list(map(int, detections.class_id))
    best_idx = max(range(len(confs)), key=lambda i: confs[i])
    x0, y0, x1, y1 = [float(v) for v in coords[best_idx]]
    width = max(0.0, x1 - x0)
    height = max(0.0, y1 - y0)
    edge_margin = 0.025
    row.update(
        {
            "md_detected": True,
            "md_detection_count": len(confs),
            "md_best_confidence": confs[best_idx],
            "md_best_class_id": class_ids[best_idx],
            "md_x0": x0,
            "md_y0": y0,
            "md_x1": x1,
            "md_y1": y1,
            "md_width_fraction": width,
            "md_height_fraction": height,
            "md_area_fraction": width * height,
            "md_aspect_ratio": width / max(height, 1e-9),
            "md_edge_touch": bool(
                x0 <= edge_margin or y0 <= edge_margin or x1 >= 1 - edge_margin or y1 >= 1 - edge_margin
            ),
        }
    )
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--device", default="mps")
    parser.add_argument("--det-conf-thres", type=float, default=0.2)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    manifest_path = resolve(args.manifest)
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(manifest_path, low_memory=False)
    if args.limit:
        manifest = manifest.head(args.limit).copy()

    from PytorchWildlife.models import detection as pw_detection

    model = pw_detection.MegaDetectorV5(device=args.device, pretrained=True)
    rows = []
    for _, row in tqdm(manifest.iterrows(), total=len(manifest), desc="CzechLynx MegaDetector top-up"):
        image_path = resolve(row["candidate_source_path"])
        try:
            rgb = np.asarray(Image.open(image_path).convert("RGB"))
            result = model.single_image_detection(rgb, img_path=str(image_path), det_conf_thres=args.det_conf_thres)
            out = detection_to_row(result)
        except Exception as exc:
            out = detection_to_row({})
            out["md_error"] = repr(exc)
        out["phase14_md_candidate_id"] = row["phase14_md_candidate_id"]
        out["dataset_label"] = "czechlynx"
        out["candidate_source_path"] = row["candidate_source_path"]
        rows.append(out)

    detections = pd.DataFrame(rows)
    suffix = f"_limit{args.limit}" if args.limit else ""
    detections_path = out_dir / f"phase14_czechlynx_high_topup_megadetector_detections{suffix}.csv"
    detections.to_csv(detections_path, index=False)
    summary = {
        "manifest": rel(manifest_path),
        "manifest_rows_processed": int(len(manifest)),
        "device": args.device,
        "det_conf_thres": args.det_conf_thres,
        "detected_rows": int(detections["md_detected"].sum()),
        "md_error_rows": int(detections["md_error"].fillna("").ne("").sum()),
        "outputs": {"detections": rel(detections_path)},
    }
    summary_path = out_dir / f"phase14_czechlynx_high_topup_megadetector_detection_summary{suffix}.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS CzechLynx top-up MegaDetector rows={len(detections)} detections={rel(detections_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
