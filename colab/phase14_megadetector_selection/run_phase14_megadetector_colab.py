#!/usr/bin/env python3
"""Colab runner for Phase 14 MegaDetector high-candidate screening.

Expected Drive layout after uploading and unzipping package chunks:

phase14_colab_megadetector/
  phase14_colab_megadetector_manifest.csv
  images/
    bobcat/*.jpg
    czechlynx/*.jpg

Run in Colab:

python run_phase14_megadetector_colab.py \
  --input-dir /content/drive/MyDrive/phase14_colab_megadetector \
  --output-dir /content/drive/MyDrive/phase14_colab_megadetector_outputs \
  --device cuda
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from PIL import Image
from tqdm import tqdm


def detection_to_row(result: dict[str, Any], input_path: Path) -> dict[str, Any]:
    detections = result.get("detections")
    coords = result.get("normalized_coords") or []
    row: dict[str, Any] = {
        "colab_image_relpath": str(input_path),
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


def ensure_image(input_dir: Path, row: pd.Series, timeout: int, retries: int) -> Path:
    relpath = Path(str(row["colab_image_relpath"]))
    image_path = input_dir / relpath
    if image_path.exists():
        return image_path
    url = str(row.get("download_url", "") or "")
    if not url or url.lower() == "nan":
        return image_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for _ in range(retries):
        try:
            with requests.get(url, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                with image_path.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
            return image_path
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"download failed for {url}: {last_error!r}")


def run_detection(
    input_dir: Path,
    manifest: pd.DataFrame,
    output_dir: Path,
    device: str,
    threshold: float,
    download_timeout: int,
    download_retries: int,
) -> pd.DataFrame:
    from PytorchWildlife.models import detection as pw_detection

    model = pw_detection.MegaDetectorV5(device=device, pretrained=True)
    rows = []
    for _, row in tqdm(manifest.iterrows(), total=len(manifest), desc="MegaDetector"):
        relpath = Path(str(row["colab_image_relpath"]))
        try:
            image_path = ensure_image(input_dir, row, download_timeout, download_retries)
            rgb = np.asarray(Image.open(image_path).convert("RGB"))
            result = model.single_image_detection(rgb, img_path=str(image_path), det_conf_thres=threshold)
            out = detection_to_row(result, relpath)
        except Exception as exc:  # keep the run moving; failed rows become non-auto candidates
            out = detection_to_row({}, relpath)
            out["md_error"] = repr(exc)
        out["phase14_md_candidate_id"] = row["phase14_md_candidate_id"]
        out["dataset_label"] = row["dataset_label"]
        rows.append(out)
    detections = pd.DataFrame(rows)
    detections.to_csv(output_dir / "phase14_colab_megadetector_detections.csv", index=False)
    return detections


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--det-conf-thres", type=float, default=0.2)
    parser.add_argument("--download-timeout", type=int, default=60)
    parser.add_argument("--download-retries", type=int, default=3)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = input_dir / "phase14_colab_megadetector_manifest.csv"
    manifest = pd.read_csv(manifest_path, low_memory=False)
    detections = run_detection(
        input_dir,
        manifest,
        output_dir,
        args.device,
        args.det_conf_thres,
        args.download_timeout,
        args.download_retries,
    )
    summary = {
        "input_dir": str(input_dir),
        "manifest_rows": int(len(manifest)),
        "detection_rows": int(len(detections)),
        "device": args.device,
        "det_conf_thres": args.det_conf_thres,
        "detected_rows": int(detections["md_detected"].sum()),
        "dataset_counts": {str(k): int(v) for k, v in detections["dataset_label"].value_counts().sort_index().items()},
        "outputs": {
            "detections": str(output_dir / "phase14_colab_megadetector_detections.csv"),
        },
    }
    (output_dir / "phase14_colab_megadetector_detection_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("PASS phase14 Colab MegaDetector", json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
