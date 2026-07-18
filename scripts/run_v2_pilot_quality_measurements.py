#!/usr/bin/env python3
"""Run locked, outcome-free automatic quality measurements for the v2 pilot."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
from PIL import Image


PROTOCOL_VERSION = "pferi_v2_automatic_quality_measurement_protocol_v1"
EXECUTION_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]
PILOT_COLUMNS = ["contract_version", "pilot_pair_id", "canonical_pair_id", "selection_seed_id", "selection_stratum", "pair_availability_status", "pilot_inclusion_status", "exclusion_reason"]
CANONICAL_COLUMNS = ["contract_version", "canonical_pair_id", "endpoint_a_image_id", "endpoint_b_image_id", "source_dataset", "pair_availability_status", "pair_inclusion_status", "exclusion_reason"]
OUTPUT_COLUMNS = [
    "protocol_version", "image_id", "content_sha256", "image_integrity_status", "image_decode_status",
    "animal_coverage_fraction", "animal_coverage_value_status", "animal_coverage_failure_code", "animal_coverage_runtime_seconds",
    "native_pixel_count", "native_pixel_count_value_status", "native_pixel_count_failure_code",
    "sharpness_measure", "sharpness_value_status", "sharpness_failure_code",
    "exposure_clipping_fraction", "exposure_value_status", "exposure_failure_code",
    "native_metrics_runtime_seconds", "total_runtime_seconds", "manual_rescue_count",
]


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_safe_execution_headers(headers: Sequence[str]) -> None:
    if list(headers) != EXECUTION_COLUMNS:
        raise ValueError("execution manifest must contain exactly image_id, image_path_relative, content_sha256")
    forbidden = [header for header in headers if any(token in header.lower() for token in ("identity", "outcome", "review", "route", "rank", "score", "feature"))]
    if forbidden:
        raise ValueError(f"execution manifest has forbidden headers: {', '.join(forbidden)}")


def native_metrics(image: np.ndarray) -> dict[str, float | int]:
    """Compute locked native-resolution metrics from an RGB uint8 image."""
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("expected native RGB uint8 image")
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    clipped = np.logical_or((image <= 5).any(axis=2), (image >= 250).any(axis=2))
    return {
        "native_pixel_count": int(image.shape[0] * image.shape[1]),
        "sharpness_measure": float(cv2.Laplacian(gray, cv2.CV_64F, ksize=3).var()),
        "exposure_clipping_fraction": float(clipped.mean()),
    }


def coverage_from_instances(instances: Sequence[Mapping[str, Any]], *, score_threshold: float, mask_threshold: float) -> tuple[float | None, str]:
    eligible = [item for item in instances if item.get("label") == "cat" and float(item.get("score", 0.0)) >= score_threshold]
    if not eligible:
        return None, "detector_no_subject"
    selected = max(eligible, key=lambda item: float(item["score"]))
    mask = np.asarray(selected["mask"], dtype=np.float32)
    if mask.ndim != 2 or mask.size == 0 or not np.isfinite(mask).all():
        return None, "model_output_invalid"
    return float((mask >= mask_threshold).mean()), "not_missing"


def selected_image_ids(pilot_rows: Sequence[Mapping[str, str]], canonical_rows: Sequence[Mapping[str, str]]) -> list[str]:
    pilot_pairs = {row["canonical_pair_id"] for row in pilot_rows if row.get("pilot_inclusion_status") == "included"}
    if len(pilot_pairs) != len(pilot_rows):
        raise ValueError("pilot manifest contains duplicate or non-included rows")
    selected = [row for row in canonical_rows if row.get("canonical_pair_id") in pilot_pairs]
    if len(selected) != len(pilot_pairs):
        raise ValueError("every restricted pilot pair must resolve once in canonical-pair manifest")
    return sorted({image_id for row in selected for image_id in (row["endpoint_a_image_id"], row["endpoint_b_image_id"])})


def load_detector(allow_weight_download: bool) -> tuple[Any, Any, str, dict[str, Any]]:
    import torch
    from torchvision.models.detection import MaskRCNN_ResNet50_FPN_V2_Weights, maskrcnn_resnet50_fpn_v2

    weights = MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT
    cache_path = Path(torch.hub.get_dir()) / "checkpoints" / Path(weights.url).name
    if not cache_path.exists() and not allow_weight_download:
        raise RuntimeError(f"registered detector weights are absent: {cache_path}; rerun with --allow-weight-download after recording this protocol")
    state_dict = weights.get_state_dict(progress=True, check_hash=True)
    model = maskrcnn_resnet50_fpn_v2(weights=None, weights_backbone=None)
    model.load_state_dict(state_dict)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()
    metadata = {
        "extractor_id": "torchvision_maskrcnn_resnet50_fpn_v2_coco_v1",
        "torch_version": torch.__version__,
        "torchvision_version": __import__("torchvision").__version__,
        "device": str(device),
        "weights_url": weights.url,
        "weights_sha256": sha256_file(cache_path),
        "categories": weights.meta["categories"],
    }
    return model, device, metadata["categories"], metadata


def detector_instances(model: Any, device: Any, categories: Sequence[str], image: np.ndarray) -> list[dict[str, Any]]:
    import torch

    tensor = torch.from_numpy(np.ascontiguousarray(image)).permute(2, 0, 1).float().div(255.0).to(device)
    with torch.inference_mode():
        result = model([tensor])[0]
    records: list[dict[str, Any]] = []
    labels = result["labels"].detach().cpu().tolist()
    scores = result["scores"].detach().cpu().tolist()
    for index, (label, score) in enumerate(zip(labels, scores)):
        if categories[int(label)] == "cat" and float(score) >= 0.50:
            records.append({"label": "cat", "score": float(score), "mask": result["masks"][index, 0].detach().cpu().numpy().copy()})
    del result, tensor
    return records


def environment_record() -> dict[str, Any]:
    return {"python_version": sys.version, "platform": platform.platform(), "worker_count": 1, "pil_version": Image.__version__, "opencv_version": cv2.__version__, "numpy_version": np.__version__}


def run_measurements(image_ids: Sequence[str], execution_by_id: Mapping[str, Mapping[str, str]], *, allow_weight_download: bool, image_root: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    start_initialization = time.perf_counter()
    model, device, categories, detector_audit = load_detector(allow_weight_download)
    detector_audit["model_initialization_seconds"] = time.perf_counter() - start_initialization
    rows: list[dict[str, Any]] = []
    for image_id in image_ids:
        started = time.perf_counter()
        execution = execution_by_id[image_id]
        source = ((image_root / Path(execution["image_path_relative"]).name) if image_root else (ROOT / execution["image_path_relative"])).resolve()
        base = {"protocol_version": PROTOCOL_VERSION, "image_id": image_id, "content_sha256": execution["content_sha256"], "manual_rescue_count": 0}
        permitted_root = image_root.resolve() if image_root else ROOT.resolve()
        if not source.is_relative_to(permitted_root) or not source.exists() or sha256_file(source) != execution["content_sha256"]:
            rows.append({**base, "image_integrity_status": "fail", "image_decode_status": "not_attempted", "animal_coverage_value_status": "upstream_input_absent", "animal_coverage_failure_code": "file_unavailable", "native_pixel_count_value_status": "upstream_input_absent", "native_pixel_count_failure_code": "file_unavailable", "sharpness_value_status": "upstream_input_absent", "sharpness_failure_code": "file_unavailable", "exposure_value_status": "upstream_input_absent", "exposure_failure_code": "file_unavailable", "total_runtime_seconds": f"{time.perf_counter() - started:.6f}"})
            continue
        try:
            with Image.open(source) as decoded:
                image = np.array(decoded.convert("RGB"), copy=True)
        except Exception:
            rows.append({**base, "image_integrity_status": "pass", "image_decode_status": "failure", "animal_coverage_value_status": "image_decode_failure", "animal_coverage_failure_code": "image_decode_failure", "native_pixel_count_value_status": "image_decode_failure", "native_pixel_count_failure_code": "image_decode_failure", "sharpness_value_status": "image_decode_failure", "sharpness_failure_code": "image_decode_failure", "exposure_value_status": "image_decode_failure", "exposure_failure_code": "image_decode_failure", "total_runtime_seconds": f"{time.perf_counter() - started:.6f}"})
            continue
        native_started = time.perf_counter()
        metrics = native_metrics(image)
        native_runtime = time.perf_counter() - native_started
        coverage_started = time.perf_counter()
        try:
            coverage, coverage_status = coverage_from_instances(detector_instances(model, device, categories, image), score_threshold=0.50, mask_threshold=0.50)
            coverage_failure = "none" if coverage_status == "not_missing" else "subject_not_detected"
        except Exception:
            coverage, coverage_status, coverage_failure = None, "model_inference_failure", "model_runtime_error"
        rows.append({**base, "image_integrity_status": "pass", "image_decode_status": "ok", "animal_coverage_fraction": "" if coverage is None else f"{coverage:.8f}", "animal_coverage_value_status": coverage_status, "animal_coverage_failure_code": coverage_failure, "animal_coverage_runtime_seconds": f"{time.perf_counter() - coverage_started:.6f}", "native_pixel_count": metrics["native_pixel_count"], "native_pixel_count_value_status": "not_missing", "native_pixel_count_failure_code": "none", "sharpness_measure": f"{metrics['sharpness_measure']:.8f}", "sharpness_value_status": "not_missing", "sharpness_failure_code": "none", "exposure_clipping_fraction": f"{metrics['exposure_clipping_fraction']:.8f}", "exposure_value_status": "not_missing", "exposure_failure_code": "none", "native_metrics_runtime_seconds": f"{native_runtime:.6f}", "total_runtime_seconds": f"{time.perf_counter() - started:.6f}"})
        del image
        gc.collect()
        if len(rows) % 10 == 0:
            print(f"processed {len(rows)}/{len(image_ids)}", flush=True)
    return rows, detector_audit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-manifest", type=Path, required=True)
    parser.add_argument("--canonical-pairs", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--allow-weight-download", action="store_true")
    parser.add_argument("--image-root", type=Path, help="Directory containing byte-identical extracted image files named as in the execution manifest.")
    args = parser.parse_args(argv)
    pilot_rows, pilot_headers = read_csv(args.pilot_manifest)
    canonical_rows, canonical_headers = read_csv(args.canonical_pairs)
    execution_rows, execution_headers = read_csv(args.execution_manifest)
    if pilot_headers != PILOT_COLUMNS or canonical_headers != CANONICAL_COLUMNS:
        raise ValueError("pilot or canonical manifest columns differ from their locked v2 contracts")
    assert_safe_execution_headers(execution_headers)
    image_ids = selected_image_ids(pilot_rows, canonical_rows)
    execution_by_id = {row["image_id"]: row for row in execution_rows}
    missing = sorted(set(image_ids).difference(execution_by_id))
    if missing:
        raise ValueError(f"restricted execution manifest omits {len(missing)} pilot images")
    rows, detector_audit = run_measurements(image_ids, execution_by_id, allow_weight_download=args.allow_weight_download, image_root=args.image_root)
    write_csv(args.output_csv, rows)
    audit = {"protocol_version": PROTOCOL_VERSION, "status": "EXECUTION_COMPLETE", "integrity_status": "PASS" if all(row["image_integrity_status"] == "pass" for row in rows) else "FAIL", "pilot_pair_count": len(pilot_rows), "unique_pilot_image_count": len(image_ids), "output_row_count": len(rows), "value_status_counts": {field: dict(Counter(row.get(field, "") for row in rows)) for field in ("animal_coverage_value_status", "native_pixel_count_value_status", "sharpness_value_status", "exposure_value_status")}, "environment": environment_record(), "detector": detector_audit, "claim_boundary": "Outcome-free feasibility measurements only; no feature passes a retention gate until the fixed gate analysis is run."}
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["integrity_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
