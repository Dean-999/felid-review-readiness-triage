#!/usr/bin/env python3
"""Hash-verified Task15K quality, local-match, and frozen-model control runner."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PAIR_COLUMNS = [
    "canonical_pair_id", "component_id", "formal_sampling_stage", "endpoint_a_image_id", "endpoint_b_image_id",
    "descriptor_support_category", "best_rank_band", "megadescriptor_rank_a_to_b", "megadescriptor_rank_b_to_a",
    "dinov2_rank_a_to_b", "dinov2_rank_b_to_a", "selection_evidence_state",
]
IMAGE_COLUMNS = ["candidate_image_id", "content_sha256", "local_relative_path", "image_filename"]
REFERENCE_COLUMNS = [
    "candidate_image_id", "content_sha256", "endpoint_native_pixel_quality_percentile",
    "endpoint_sharpness_quality_percentile", "endpoint_exposure_quality_percentile",
]
QUALITY_COLUMNS = [
    "candidate_image_id", "content_sha256", "image_decode_status", "native_pixel_count", "sharpness_measure",
    "exposure_clipping_fraction", "failure_code", "value_status",
]
LOCAL_COLUMNS = [
    "canonical_pair_id", "failure_code", "value_status", "local_match_coverage_fraction", "inlier_count",
    "source_keypoint_count", "target_keypoint_count", "runtime_seconds",
]
PREDICTION_COLUMNS = ["canonical_pair_id", "model_id", "probability_not_ready_or_uncertain"]
P5_INCREMENTAL_COLUMNS = [
    "local_match_coverage_fraction__z", "local_match_coverage_fraction__missing",
    "local_match_measurement_failure==true", "local_match_measurement_failure==__MISSING__",
    "local_match_measurement_failure==__UNKNOWN__",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def read_csv_exact(path: Path, fields: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise ValueError(f"unexpected CSV schema: {path.name}")
        return list(reader)


def verify_package_manifest(package_root: Path) -> str:
    manifest = package_root / "PACKAGE_MANIFEST.sha256"
    if not manifest.is_file():
        raise FileNotFoundError("missing PACKAGE_MANIFEST.sha256")
    declared = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        target = package_root / relative
        if relative in declared or not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"package manifest verification failed: {relative}")
        declared.add(relative)
    actual = {
        str(path.relative_to(package_root)) for path in package_root.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256" and "__pycache__" not in path.parts
    }
    if actual != declared:
        raise RuntimeError("package manifest inventory mismatch")
    return sha256(manifest)


def load_inputs(package_root: Path) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    contract_path = package_root / "contracts/task15k_independent_calibration_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    binding = contract.get("execution_binding", {})
    if contract.get("contract_version") != "pferi_v2_task15k_independent_calibration_contract_v1":
        raise ValueError("unexpected Task15K contract")
    pairs = read_csv_exact(package_root / "inputs/calibration_candidate_pairs.csv", PAIR_COLUMNS)
    images = read_csv_exact(package_root / "inputs/selected_image_manifest.csv", IMAGE_COLUMNS)
    reference = read_csv_exact(package_root / "inputs/quality_reference_percentiles.csv", REFERENCE_COLUMNS)
    if len(pairs) != int(binding["expected_pair_count"]) or len(images) != int(binding["expected_image_count"]) or len(reference) != len(images):
        raise ValueError("Task15K input cardinality mismatch")
    if sha256(package_root / "inputs/calibration_candidate_pairs.csv") != binding["candidate_pair_manifest_sha256"]:
        raise RuntimeError("selected pair manifest hash mismatch")
    if sha256(package_root / "inputs/selected_image_manifest.csv") != binding["selected_image_manifest_sha256"]:
        raise RuntimeError("selected image manifest hash mismatch")
    bundle = json.loads((package_root / "inputs/final_model_bundle.json").read_text(encoding="utf-8"))
    if bundle.get("bundle_payload_sha256") != binding["final_model_bundle_payload_sha256"]:
        raise RuntimeError("final model bundle binding mismatch")
    return contract, pairs, images, reference, bundle


def verify_images(images: list[dict[str, str]], image_root: Path) -> dict[str, Path]:
    resolved = image_root.resolve(); paths: dict[str, Path] = {}
    hashes, names = set(), set()
    for row in images:
        identifier, expected, name = row["candidate_image_id"], row["content_sha256"], row["image_filename"]
        if identifier in paths or expected in hashes or name in names or Path(name).name != name:
            raise ValueError("duplicate or unsafe Task15K image manifest value")
        target = resolved / name
        if not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"image integrity failure: {identifier}")
        paths[identifier] = target; hashes.add(expected); names.add(name)
    return paths


def measure_quality(images: list[dict[str, str]], paths: dict[str, Path]) -> list[dict[str, Any]]:
    import cv2
    from PIL import Image

    rows = []
    for index, item in enumerate(images, start=1):
        identifier = item["candidate_image_id"]
        try:
            with Image.open(paths[identifier]) as decoded:
                image = np.asarray(decoded.convert("RGB"), dtype=np.uint8)
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            rows.append({
                "candidate_image_id": identifier, "content_sha256": item["content_sha256"], "image_decode_status": "ok",
                "native_pixel_count": int(image.shape[0] * image.shape[1]), "sharpness_measure": f"{cv2.Laplacian(gray, cv2.CV_64F, ksize=3).var():.8f}",
                "exposure_clipping_fraction": f"{np.logical_or((image <= 5).any(axis=2), (image >= 250).any(axis=2)).mean():.8f}",
                "failure_code": "none", "value_status": "not_missing",
            })
        except Exception as error:
            raise RuntimeError(f"quality measurement failure: {identifier}: {type(error).__name__}") from error
        if index % 100 == 0 or index == len(images):
            print(f"quality {index}/{len(images)}", flush=True)
    return rows


def local_coverage(left_path: Path, right_path: Path) -> tuple[float, int, int, int]:
    import cv2

    left = cv2.imread(str(left_path), cv2.IMREAD_GRAYSCALE); right = cv2.imread(str(right_path), cv2.IMREAD_GRAYSCALE)
    if left is None or right is None:
        raise OSError("image decode failure")
    sift = cv2.SIFT_create(nfeatures=800)
    left_keypoints, left_desc = sift.detectAndCompute(left, None); right_keypoints, right_desc = sift.detectAndCompute(right, None)
    if left_desc is None or right_desc is None or len(left_keypoints) < 4 or len(right_keypoints) < 4:
        return 0.0, 0, len(left_keypoints), len(right_keypoints)
    raw = cv2.BFMatcher(cv2.NORM_L2).knnMatch(left_desc, right_desc, k=2)
    good = [pair[0] for pair in raw if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance]
    if len(good) < 4:
        return 0.0, 0, len(left_keypoints), len(right_keypoints)
    source = np.float32([left_keypoints[match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
    target = np.float32([right_keypoints[match.trainIdx].pt for match in good]).reshape(-1, 1, 2)
    _, mask = cv2.findHomography(source, target, cv2.RANSAC, 5.0)
    if mask is None:
        return 0.0, 0, len(left_keypoints), len(right_keypoints)
    inliers = [match for match, keep in zip(good, mask.ravel()) if bool(keep)]
    return float((len({item.queryIdx for item in inliers}) / len(left_keypoints) + len({item.trainIdx for item in inliers}) / len(right_keypoints)) / 2.0), len(inliers), len(left_keypoints), len(right_keypoints)


def measure_local(pairs: list[dict[str, str]], paths: dict[str, Path]) -> list[dict[str, Any]]:
    rows = []
    for index, pair in enumerate(pairs, start=1):
        started = time.perf_counter()
        try:
            coverage, inliers, left_count, right_count = local_coverage(paths[pair["endpoint_a_image_id"]], paths[pair["endpoint_b_image_id"]])
            rows.append({"canonical_pair_id": pair["canonical_pair_id"], "failure_code": "none", "value_status": "not_missing", "local_match_coverage_fraction": f"{coverage:.8f}", "inlier_count": inliers, "source_keypoint_count": left_count, "target_keypoint_count": right_count, "runtime_seconds": f"{time.perf_counter() - started:.6f}"})
        except Exception as error:
            rows.append({"canonical_pair_id": pair["canonical_pair_id"], "failure_code": "model_runtime_error", "value_status": "model_inference_failure", "local_match_coverage_fraction": "", "inlier_count": "", "source_keypoint_count": "", "target_keypoint_count": "", "runtime_seconds": f"{time.perf_counter() - started:.6f}"})
        if index % 100 == 0 or index == len(pairs):
            print(f"local match {index}/{len(pairs)}", flush=True)
    return rows


def fixed_p5_transform(pre3: Any, pre5: Any, frame: pd.DataFrame) -> pd.DataFrame:
    p3, p5_raw = pre3.transform(frame), pre5.transform(frame)
    failure = frame["local_match_measurement_failure"]
    fixed = pd.DataFrame(index=frame.index)
    fixed["local_match_coverage_fraction__z"] = p5_raw["local_match_coverage_fraction__z"]
    fixed["local_match_coverage_fraction__missing"] = p5_raw["local_match_coverage_fraction__missing"]
    fixed["local_match_measurement_failure==true"] = failure.eq(True).astype(float)
    fixed["local_match_measurement_failure==__MISSING__"] = failure.isna().astype(float)
    fixed["local_match_measurement_failure==__UNKNOWN__"] = (~failure.isin([True, False]) & ~failure.isna()).astype(float)
    return pd.concat([p3, fixed.loc[:, P5_INCREMENTAL_COLUMNS]], axis=1)


def build_feature_frame(pairs: list[dict[str, str]], quality: list[dict[str, Any]], local: list[dict[str, Any]], reference: list[dict[str, str]]) -> pd.DataFrame:
    result = pd.DataFrame(pairs).copy()
    refs = pd.DataFrame(reference).set_index("candidate_image_id")
    if len(refs) != len(quality) or set(refs.index) != set(item["candidate_image_id"] for item in quality):
        raise ValueError("quality reference coverage mismatch")
    if any(item["failure_code"] != "none" for item in quality):
        raise RuntimeError("quality failure cannot silently enter frozen model scoring")
    for source, target in [
        ("endpoint_native_pixel_quality_percentile", "endpoint_native_pixel_quality_percentile_min"),
        ("endpoint_sharpness_quality_percentile", "endpoint_sharpness_quality_percentile_min"),
        ("endpoint_exposure_quality_percentile", "endpoint_exposure_quality_percentile_min"),
    ]:
        mapping = pd.to_numeric(refs[source], errors="raise")
        result[target] = np.minimum(result.endpoint_a_image_id.map(mapping), result.endpoint_b_image_id.map(mapping))
    for source, target in [("megadescriptor_rank", "megadescriptor_within_role_percentile"), ("dinov2_rank", "dinov2_within_role_percentile")]:
        left = pd.to_numeric(result[f"{source}_a_to_b"], errors="coerce")
        right = pd.to_numeric(result[f"{source}_b_to_a"], errors="coerce")
        result[target] = (21 - np.minimum(left, right)) / 20
    result["endpoint_quality_measurement_failure"] = False
    result["endpoint_frozen_quality_stress"] = (result.endpoint_sharpness_quality_percentile_min < 0.15) | (result.endpoint_exposure_quality_percentile_min < 0.10)
    local_frame = pd.DataFrame(local).rename(columns={"failure_code": "local_match_measurement_failure"})
    result = result.merge(local_frame[["canonical_pair_id", "local_match_coverage_fraction", "local_match_measurement_failure"]], on="canonical_pair_id", validate="one_to_one")
    result["local_match_measurement_failure"] = result["local_match_measurement_failure"].ne("none")
    return result


def score(bundle: dict[str, Any], frame: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        from pferi_v2_fold_preprocessor import FittedFoldPreprocessor
    except ModuleNotFoundError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from pferi_v2_fold_preprocessor import FittedFoldPreprocessor

    pre3 = FittedFoldPreprocessor.from_payload(bundle["P3_preprocessor"])
    pre5 = FittedFoldPreprocessor.from_payload(bundle["P5_source_preprocessor"])
    designs = {"P3": pre3.transform(frame), "P5": fixed_p5_transform(pre3, pre5, frame)}
    feature_rows = frame[["canonical_pair_id"]].copy()
    predictions = []
    for model_id, design in designs.items():
        expected = bundle["models"][model_id]["feature_columns"]
        if list(design.columns) != expected:
            raise RuntimeError(f"frozen feature ordering mismatch: {model_id}")
        coefficients = np.asarray(bundle["models"][model_id]["coefficients"], dtype=float)
        # Some OpenBLAS builds leave harmless floating-point status flags after
        # matrix multiplication; validate the actual values immediately below.
        with np.errstate(over="ignore", divide="ignore", invalid="ignore", under="ignore"):
            linear = np.column_stack([np.ones(len(design)), design.to_numpy(float)]) @ coefficients
        if not np.isfinite(linear).all():
            raise RuntimeError("non-finite frozen model linear predictor")
        probability = 1.0 / (1.0 + np.exp(-np.clip(linear, -36, 36)))
        if not np.isfinite(probability).all() or not ((probability >= 0) & (probability <= 1)).all():
            raise RuntimeError("invalid frozen model probability")
        predictions.extend({"canonical_pair_id": pair_id, "model_id": model_id, "probability_not_ready_or_uncertain": f"{value:.17g}"} for pair_id, value in zip(frame.canonical_pair_id, probability))
        for column in design.columns:
            feature_rows[f"{model_id}__{column}"] = design[column].to_numpy(float)
    return feature_rows.to_dict("records"), predictions


def run(package_root: Path, image_root: Path, output_dir: Path) -> dict[str, Any]:
    package_root, image_root, output_dir = package_root.resolve(), image_root.resolve(), output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite results directory: {output_dir}")
    package_sha = verify_package_manifest(package_root)
    contract, pairs, images, reference, bundle = load_inputs(package_root)
    paths = verify_images(images, image_root)
    quality = measure_quality(images, paths)
    local = measure_local(pairs, paths)
    frame = build_feature_frame(pairs, quality, local, reference)
    feature_rows, predictions = score(bundle, frame)
    output_dir.mkdir(parents=True)
    write_csv(output_dir / "automatic_quality_measurements.csv", quality, QUALITY_COLUMNS)
    write_csv(output_dir / "local_match_measurements.csv", local, LOCAL_COLUMNS)
    fields = list(feature_rows[0])
    write_csv(output_dir / "frozen_model_score_inputs.csv", feature_rows, fields)
    write_csv(output_dir / "frozen_model_raw_predictions.csv", predictions, PREDICTION_COLUMNS)
    audit = {
        "status": "PASS", "created_at_utc": utc_now(), "package_manifest_sha256": package_sha,
        "contract_sha256": sha256(package_root / "contracts/task15k_independent_calibration_contract.json"),
        "candidate_pair_manifest_sha256": sha256(package_root / "inputs/calibration_candidate_pairs.csv"),
        "verified_image_count": len(paths), "pair_count": len(pairs), "model_prediction_count": len(predictions),
        "python": platform.python_version(), "calibration_outcomes_accessed": False,
        "locked_stage_outcomes_accessed": False,
        "claim_boundary": contract["claim_boundary"],
    }
    write_json(output_dir / "run_audit.json", audit)
    return audit


def validate(package_root: Path, results_dir: Path) -> dict[str, Any]:
    contract, pairs, images, reference, bundle = load_inputs(package_root.resolve())
    failures = []
    try:
        quality = read_csv_exact(results_dir / "automatic_quality_measurements.csv", QUALITY_COLUMNS)
        local = read_csv_exact(results_dir / "local_match_measurements.csv", LOCAL_COLUMNS)
        predictions = read_csv_exact(results_dir / "frozen_model_raw_predictions.csv", PREDICTION_COLUMNS)
        if len(quality) != len(images) or {row["candidate_image_id"] for row in quality} != {row["candidate_image_id"] for row in images}:
            failures.append("quality_coverage")
        if any(row["failure_code"] != "none" for row in quality):
            failures.append("quality_failure")
        if len(local) != len(pairs) or {row["canonical_pair_id"] for row in local} != {row["canonical_pair_id"] for row in pairs}:
            failures.append("local_coverage")
        if len(predictions) != len(pairs) * 2 or {(row["canonical_pair_id"], row["model_id"]) for row in predictions} != {(pair["canonical_pair_id"], model) for pair in pairs for model in ("P3", "P5")}:
            failures.append("prediction_coverage")
        for row in predictions:
            value = float(row["probability_not_ready_or_uncertain"])
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                failures.append("invalid_probability"); break
        run_audit = json.loads((results_dir / "run_audit.json").read_text(encoding="utf-8"))
        if run_audit.get("status") != "PASS" or run_audit.get("calibration_outcomes_accessed") is not False:
            failures.append("run_audit")
    except Exception as error:
        failures.append(f"inventory:{type(error).__name__}")
    audit = {"status": "PASS" if not failures else "FAIL", "validated_at_utc": utc_now(), "pair_count": len(pairs), "image_count": len(images), "prediction_count": len(pairs) * 2, "failures": failures, "calibration_outcomes_accessed": False}
    write_json(results_dir / "validation_audit.json", audit)
    if failures:
        raise RuntimeError("validation failed: " + "; ".join(failures))
    return audit


def export_results(results_dir: Path, zip_path: Path) -> dict[str, Any]:
    if zip_path.exists():
        raise FileExistsError(f"refusing to overwrite export: {zip_path}")
    validation = json.loads((results_dir / "validation_audit.json").read_text(encoding="utf-8"))
    if validation.get("status") != "PASS":
        raise RuntimeError("a passing validate command is required before export")
    required = [results_dir / item for item in ["automatic_quality_measurements.csv", "local_match_measurements.csv", "frozen_model_score_inputs.csv", "frozen_model_raw_predictions.csv", "run_audit.json", "validation_audit.json"]]
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("result inventory incomplete")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in required:
            archive.write(path, arcname=f"PF_ERI_TASK15K_CALIBRATION_FINAL_EXPORT/{path.name}")
    if zipfile.ZipFile(zip_path).testzip() is not None:
        raise RuntimeError("export ZIP CRC failure")
    audit = {"status": "PASS", "created_at_utc": utc_now(), "zip": zip_path.name, "zip_sha256": sha256(zip_path), "file_count": len(required)}
    write_json(results_dir / "export_audit.json", audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run"); run_parser.add_argument("--package-root", type=Path, default=Path(".")); run_parser.add_argument("--image-root", type=Path, default=Path("images")); run_parser.add_argument("--output-dir", type=Path, required=True)
    check_parser = sub.add_parser("validate"); check_parser.add_argument("--package-root", type=Path, default=Path(".")); check_parser.add_argument("--results-dir", type=Path, required=True)
    export_parser = sub.add_parser("export"); export_parser.add_argument("--results-dir", type=Path, required=True); export_parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.package_root, args.image_root, args.output_dir) if args.command == "run" else validate(args.package_root, args.results_dir) if args.command == "validate" else export_results(args.results_dir.resolve(), args.zip.resolve())
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2, sort_keys=True)); return 1


if __name__ == "__main__":
    raise SystemExit(main())
