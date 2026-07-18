#!/usr/bin/env python3
"""Measure retained outcome-free quality fields on the full frozen v2 image set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_v2_pilot_quality_measurements import native_metrics


RUN_VERSION = "pferi_v2_full_retained_image_quality_run_v1"
MEASUREMENT_PROTOCOL_VERSION = "pferi_v2_automatic_quality_measurement_protocol_v1"
INPUT_COLUMNS = ["image_id", "image_path_relative", "content_sha256"]
OUTPUT_COLUMNS = [
    "run_version",
    "measurement_protocol_version",
    "image_id",
    "content_sha256",
    "image_integrity_status",
    "image_decode_status",
    "native_pixel_count",
    "native_pixel_count_value_status",
    "native_pixel_count_failure_code",
    "sharpness_measure",
    "sharpness_value_status",
    "sharpness_failure_code",
    "exposure_clipping_fraction",
    "exposure_value_status",
    "exposure_failure_code",
    "native_metrics_runtime_seconds",
    "total_runtime_seconds",
    "manual_rescue_count",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or []) != INPUT_COLUMNS:
            raise ValueError(f"execution manifest must contain exactly {INPUT_COLUMNS}")
        rows = list(reader)
    if len(rows) != len({row["image_id"] for row in rows}):
        raise ValueError("execution manifest contains duplicate image IDs")
    return rows


def failure_row(source: Mapping[str, str], *, integrity: str, decode: str, failure_code: str, runtime: float) -> dict[str, Any]:
    status = "image_decode_failure" if decode == "failure" else "upstream_input_absent"
    return {
        "run_version": RUN_VERSION,
        "measurement_protocol_version": MEASUREMENT_PROTOCOL_VERSION,
        "image_id": source["image_id"],
        "content_sha256": source["content_sha256"],
        "image_integrity_status": integrity,
        "image_decode_status": decode,
        "native_pixel_count_value_status": status,
        "native_pixel_count_failure_code": failure_code,
        "sharpness_value_status": status,
        "sharpness_failure_code": failure_code,
        "exposure_value_status": status,
        "exposure_failure_code": failure_code,
        "total_runtime_seconds": f"{runtime:.6f}",
        "manual_rescue_count": 0,
    }


def measure_one(source: Mapping[str, str], *, project_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    relative = Path(source["image_path_relative"])
    absolute = (project_root / relative).resolve()
    if relative.is_absolute() or ".." in relative.parts or not absolute.is_relative_to(project_root.resolve()):
        return failure_row(source, integrity="fail", decode="not_attempted", failure_code="file_unavailable", runtime=time.perf_counter() - started)
    if not absolute.is_file() or sha256_file(absolute) != source["content_sha256"]:
        return failure_row(source, integrity="fail", decode="not_attempted", failure_code="file_unavailable", runtime=time.perf_counter() - started)
    try:
        with Image.open(absolute) as decoded:
            image = np.array(decoded.convert("RGB"), copy=True)
    except Exception:
        return failure_row(source, integrity="pass", decode="failure", failure_code="image_decode_failure", runtime=time.perf_counter() - started)
    metrics_started = time.perf_counter()
    metrics = native_metrics(image)
    metrics_runtime = time.perf_counter() - metrics_started
    return {
        "run_version": RUN_VERSION,
        "measurement_protocol_version": MEASUREMENT_PROTOCOL_VERSION,
        "image_id": source["image_id"],
        "content_sha256": source["content_sha256"],
        "image_integrity_status": "pass",
        "image_decode_status": "ok",
        "native_pixel_count": metrics["native_pixel_count"],
        "native_pixel_count_value_status": "not_missing",
        "native_pixel_count_failure_code": "none",
        "sharpness_measure": f"{metrics['sharpness_measure']:.8f}",
        "sharpness_value_status": "not_missing",
        "sharpness_failure_code": "none",
        "exposure_clipping_fraction": f"{metrics['exposure_clipping_fraction']:.8f}",
        "exposure_value_status": "not_missing",
        "exposure_failure_code": "none",
        "native_metrics_runtime_seconds": f"{metrics_runtime:.6f}",
        "total_runtime_seconds": f"{time.perf_counter() - started:.6f}",
        "manual_rescue_count": 0,
    }


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=3000)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args(argv)
    sources = read_manifest(args.execution_manifest)
    if len(sources) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} execution rows, found {len(sources)}")
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(sources, start=1):
        rows.append(measure_one(source, project_root=ROOT))
        if index % 250 == 0 or index == len(sources):
            print(f"processed {index}/{len(sources)}", flush=True)
    write_csv(args.output_csv, rows)
    retained_status_fields = ["native_pixel_count_value_status", "sharpness_value_status", "exposure_value_status"]
    valid = all(row["image_integrity_status"] == "pass" and row["image_decode_status"] == "ok" and all(row[field] == "not_missing" for field in retained_status_fields) for row in rows)
    audit = {
        "run_version": RUN_VERSION,
        "measurement_protocol_version": MEASUREMENT_PROTOCOL_VERSION,
        "status": "PASS" if valid else "FAIL",
        "expected_image_count": args.expected_count,
        "output_row_count": len(rows),
        "unique_image_id_count": len({row["image_id"] for row in rows}),
        "manual_rescue_count": sum(int(row["manual_rescue_count"]) for row in rows),
        "value_status_counts": {field: dict(Counter(str(row.get(field, "")) for row in rows)) for field in retained_status_fields},
        "execution_manifest": str(args.execution_manifest.resolve().relative_to(ROOT)),
        "execution_manifest_sha256": sha256_file(args.execution_manifest),
        "measurement_csv": str(args.output_csv.resolve().relative_to(ROOT)),
        "measurement_csv_sha256": sha256_file(args.output_csv),
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "pil_version": Image.__version__,
            "opencv_version": cv2.__version__,
            "numpy_version": np.__version__,
        },
        "excluded_feature": "animal_coverage_fraction",
        "claim_boundary": "Outcome-free retained image-quality measurements only. This run does not create a partition, sample a pair, inspect an outcome, or establish predictive value.",
    }
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
