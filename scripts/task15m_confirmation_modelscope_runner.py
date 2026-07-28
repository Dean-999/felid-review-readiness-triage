#!/usr/bin/env python3
"""Outcome-free Task15M descriptor, measurement, frozen-score, and calibration runner."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import task15i_descriptor_modelscope_runner as descriptors
import task15k_calibration_modelscope_runner as scoring


IMAGE_COLUMNS = ["candidate_image_id", "content_sha256", "local_relative_path", "image_filename"]
PAIR_COLUMNS = [
    "canonical_pair_id", "component_id", "formal_sampling_stage", "endpoint_a_image_id", "endpoint_b_image_id",
    "descriptor_support_category", "best_rank_band", "selection_evidence_state",
]
SCORED_PAIR_COLUMNS = PAIR_COLUMNS[:5] + [
    "descriptor_support_category", "best_rank_band", "megadescriptor_rank_a_to_b", "megadescriptor_rank_b_to_a",
    "dinov2_rank_a_to_b", "dinov2_rank_b_to_a", "selection_evidence_state",
]
PAIR_MEASUREMENT_COLUMNS = [
    "canonical_pair_id", "descriptor_support_category", "best_rank_band", "megadescriptor_rank_a_to_b",
    "megadescriptor_rank_b_to_a", "dinov2_rank_a_to_b", "dinov2_rank_b_to_a", "support_status",
]
UNSUPPORTED_COLUMNS = ["canonical_pair_id", "unsupported_reason"]
QUALITY_REFERENCE_COLUMNS = [
    "candidate_image_id", "content_sha256", "image_decode_status", "native_pixel_count",
    "sharpness_measure", "exposure_clipping_fraction", "failure_code", "value_status",
]
PREDICTION_COLUMNS = [
    "canonical_pair_id", "model_id", "raw_probability_not_ready_or_uncertain",
    "calibrated_probability_not_ready_or_uncertain",
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv_exact(path: Path, fields: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise ValueError(f"unexpected CSV schema: {path.name}")
        return list(reader)


def verify_package(package_root: Path) -> str:
    return descriptors.verify_package_manifest(package_root)


def load_inputs(package_root: Path) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    contract_path = package_root / "contracts/task15m_confirmation_execution_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_version") != "pferi_v2_task15m_confirmation_execution_contract_v1":
        raise ValueError("unexpected Task15M execution contract")
    binding = contract["execution_binding"]
    pairs = read_csv_exact(package_root / "inputs/confirmation_candidate_pairs.csv", PAIR_COLUMNS)
    images = read_csv_exact(package_root / "inputs/selected_image_manifest.csv", IMAGE_COLUMNS)
    reference = read_csv_exact(package_root / "inputs/task15i_quality_reference.csv", QUALITY_REFERENCE_COLUMNS)
    bundle = json.loads((package_root / "inputs/final_model_bundle.json").read_text(encoding="utf-8"))
    if len(pairs) != int(binding["expected_pair_count"]) or len(images) != int(binding["expected_image_count"]) or len(reference) != int(binding["quality_reference_image_count"]):
        raise ValueError("Task15M input cardinality mismatch")
    required_hashes = {
        "inputs/confirmation_candidate_pairs.csv": "candidate_pair_manifest_sha256",
        "inputs/selected_image_manifest.csv": "selected_image_manifest_sha256",
        "inputs/task15i_quality_reference.csv": "quality_reference_sha256",
    }
    for relative, key in required_hashes.items():
        if sha256(package_root / relative) != binding[key]:
            raise RuntimeError(f"frozen input hash mismatch: {relative}")
    if bundle.get("bundle_payload_sha256") != binding["final_model_bundle_payload_sha256"]:
        raise RuntimeError("frozen Task15J model bundle binding mismatch")
    return contract, pairs, images, reference, bundle


def verify_images(images: list[dict[str, str]], image_root: Path) -> tuple[dict[str, Path], list[dict[str, str]]]:
    resolved = image_root.resolve()
    paths: dict[str, Path] = {}
    descriptor_rows: list[dict[str, str]] = []
    hashes, names = set(), set()
    for row in images:
        image_id, expected, name = row["candidate_image_id"], row["content_sha256"], row["image_filename"]
        if image_id in paths or expected in hashes or name in names or Path(name).name != name:
            raise ValueError("duplicate or unsafe Task15M image manifest value")
        target = resolved / name
        if not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"image integrity failure: {image_id}")
        paths[image_id] = target
        descriptor_rows.append({"image_id": image_id, "content_sha256": expected, "image_path": str(target)})
        hashes.add(expected)
        names.add(name)
    return paths, descriptor_rows


def ranks_by_direction(score_rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    result: dict[tuple[str, str], int] = {}
    for row in score_rows:
        key = (str(row["query_image_id"]), str(row["candidate_image_id"]))
        rank = int(row["candidate_rank"])
        if key in result or rank < 1 or rank > 20:
            raise ValueError("invalid or duplicate descriptor rank")
        result[key] = rank
    return result


def classify_pairs(pairs: list[dict[str, str]], mega_scores: list[dict[str, Any]], dino_scores: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    mega, dino = ranks_by_direction(mega_scores), ranks_by_direction(dino_scores)
    measurements, supported, unsupported = [], [], []
    for pair in pairs:
        left, right = pair["endpoint_a_image_id"], pair["endpoint_b_image_id"]
        ranks = {
            "megadescriptor_rank_a_to_b": mega.get((left, right)),
            "megadescriptor_rank_b_to_a": mega.get((right, left)),
            "dinov2_rank_a_to_b": dino.get((left, right)),
            "dinov2_rank_b_to_a": dino.get((right, left)),
        }
        forward = ranks["megadescriptor_rank_a_to_b"] is not None and ranks["dinov2_rank_a_to_b"] is not None
        backward = ranks["megadescriptor_rank_b_to_a"] is not None and ranks["dinov2_rank_b_to_a"] is not None
        category = "both_reciprocal" if forward and backward else "both_agreement" if forward or backward else "unsupported"
        rank_values = []
        if forward:
            rank_values.extend([ranks["megadescriptor_rank_a_to_b"], ranks["dinov2_rank_a_to_b"]])
        if backward:
            rank_values.extend([ranks["megadescriptor_rank_b_to_a"], ranks["dinov2_rank_b_to_a"]])
        band = "top_5" if rank_values and max(rank_values) <= 5 else "top_10" if rank_values and max(rank_values) <= 10 else "top_20" if rank_values else "not_retrieved"
        measurement = {
            "canonical_pair_id": pair["canonical_pair_id"], "descriptor_support_category": category,
            "best_rank_band": band, **{key: "" if value is None else value for key, value in ranks.items()},
            "support_status": "supported" if category != "unsupported" else "unsupported",
        }
        measurements.append(measurement)
        if category == "unsupported":
            unsupported.append({"canonical_pair_id": pair["canonical_pair_id"], "unsupported_reason": "no_same_direction_dual_descriptor_top20_consensus"})
        else:
            supported.append({
                **{key: pair[key] for key in PAIR_COLUMNS[:5]}, "descriptor_support_category": category,
                "best_rank_band": band, **{key: measurement[key] for key in ranks},
                "selection_evidence_state": "outcome_unopened",
            })
    return measurements, supported, unsupported


def percentile_reference(quality: list[dict[str, Any]], reference: list[dict[str, str]]) -> list[dict[str, Any]]:
    if any(row["failure_code"] != "none" for row in quality):
        raise RuntimeError("quality failure cannot silently enter frozen model scoring")
    if any(row["failure_code"] != "none" for row in reference):
        raise RuntimeError("frozen Task15I quality reference contains failures")
    fields = ["native_pixel_count", "sharpness_measure", "exposure_clipping_fraction"]
    distributions = {field: np.sort(np.asarray([float(row[field]) for row in reference], dtype=float)) for field in fields}
    if any(len(values) != len(reference) or not np.isfinite(values).all() for values in distributions.values()):
        raise RuntimeError("invalid frozen quality reference distribution")
    rows = []
    names = {
        "native_pixel_count": "endpoint_native_pixel_quality_percentile",
        "sharpness_measure": "endpoint_sharpness_quality_percentile",
        "exposure_clipping_fraction": "endpoint_exposure_quality_percentile",
    }
    for row in quality:
        output = {"candidate_image_id": row["candidate_image_id"], "content_sha256": row["content_sha256"]}
        for source, target in names.items():
            output[target] = f"{np.searchsorted(distributions[source], float(row[source]), side='right') / len(reference):.12f}"
        rows.append(output)
    return rows


def apply_calibration(raw: list[dict[str, Any]], contract: dict[str, Any]) -> list[dict[str, Any]]:
    calibration = contract["fixed_task15l_calibration"]
    rows = []
    for row in raw:
        probability = float(row["probability_not_ready_or_uncertain"])
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise RuntimeError("invalid frozen raw probability")
        clipped = min(max(probability, 1e-12), 1.0 - 1e-12)
        parameters = calibration[row["model_id"]]
        linear = float(parameters["intercept"]) + float(parameters["slope"]) * math.log(clipped / (1.0 - clipped))
        calibrated = 1.0 / (1.0 + math.exp(-max(min(linear, 36.0), -36.0)))
        rows.append({"canonical_pair_id": row["canonical_pair_id"], "model_id": row["model_id"], "raw_probability_not_ready_or_uncertain": f"{probability:.17g}", "calibrated_probability_not_ready_or_uncertain": f"{calibrated:.17g}"})
    return rows


def validate_descriptor_outputs(results_dir: Path, descriptor_rows: list[dict[str, str]], contract: dict[str, Any], contract_sha: str) -> list[str]:
    failures: list[str] = []
    expected_ids = [row["image_id"] for row in descriptor_rows]
    expected_hashes = {row["image_id"]: row["content_sha256"] for row in descriptor_rows}
    for name, descriptor in contract["descriptor_inference"]["descriptors"].items():
        score_name = "pair_scores.csv" if name == "megadescriptor_l_384" else "scores.csv"
        target = results_dir / name
        try:
            embeddings = np.load(target / "embeddings.npy", allow_pickle=False)
            if embeddings.shape != (len(expected_ids), int(descriptor["embedding_dimension"])) or not np.allclose(np.linalg.norm(embeddings, axis=1), 1.0, rtol=1e-4, atol=1e-4):
                raise ValueError("invalid embedding shape or normalization")
            mapping = read_csv_exact(target / "embedding_manifest_v2.csv", descriptors.EMBEDDING_COLUMNS)
            if [row["image_id"] for row in mapping] != expected_ids or {row["image_id"]: row["content_sha256"] for row in mapping} != expected_hashes:
                raise ValueError("embedding manifest coverage mismatch")
            scores = read_csv_exact(target / score_name, descriptors.SCORE_COLUMNS)
            top_k = int(contract["descriptor_inference"]["top_k"])
            if len(scores) != len(expected_ids) * top_k:
                raise ValueError("directed score row count mismatch")
            expected_pairs = {(query, rank) for query in expected_ids for rank in range(1, top_k + 1)}
            observed_pairs = {(row["query_image_id"], int(row["candidate_rank"])) for row in scores}
            if observed_pairs != expected_pairs:
                raise ValueError("directed score rank coverage mismatch")
            for row in scores:
                if row["descriptor_name"] != name or row["query_image_id"] == row["candidate_image_id"] or row["candidate_image_id"] not in expected_hashes or not math.isfinite(float(row["descriptor_similarity"])):
                    raise ValueError("invalid directed descriptor score")
            audit = json.loads((target / "run_audit.json").read_text(encoding="utf-8"))
            if audit.get("status") != "PASS" or audit.get("contract_sha256") != contract_sha:
                raise ValueError("descriptor audit contract mismatch")
        except Exception as error:
            failures.append(f"{name}:{type(error).__name__}")
    return failures


def run(package_root: Path, image_root: Path, output_dir: Path, batch_size: int) -> dict[str, Any]:
    package_root, image_root, output_dir = package_root.resolve(), image_root.resolve(), output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite results directory: {output_dir}")
    package_sha = verify_package(package_root)
    contract, pairs, images, reference, bundle = load_inputs(package_root)
    paths, descriptor_rows = verify_images(images, image_root)
    try:
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU is required for Task15M descriptor inference")
    except ImportError as error:
        raise RuntimeError("missing torch dependency") from error
    output_dir.mkdir(parents=True)
    descriptor_contract = contract["descriptor_inference"]
    contract_sha = sha256(package_root / "contracts/task15m_confirmation_execution_contract.json")
    mega, mega_runtime = descriptors.infer_mega(descriptor_rows, descriptor_contract["descriptors"]["megadescriptor_l_384"], batch_size, "cuda")
    mega_audit = descriptors.write_descriptor_output(output_dir, "megadescriptor_l_384", descriptor_contract["descriptors"]["megadescriptor_l_384"], descriptor_rows, mega, mega_runtime, contract_sha, int(descriptor_contract["top_k"]))
    dino, dino_runtime = descriptors.infer_dino(descriptor_rows, descriptor_contract["descriptors"]["dinov2_vitl14"], batch_size, "cuda")
    dino_audit = descriptors.write_descriptor_output(output_dir, "dinov2_vitl14", descriptor_contract["descriptors"]["dinov2_vitl14"], descriptor_rows, dino, dino_runtime, contract_sha, int(descriptor_contract["top_k"]))
    mega_scores = descriptors.score_rows([row["image_id"] for row in descriptor_rows], mega, "megadescriptor_l_384", int(descriptor_contract["top_k"]))
    dino_scores = descriptors.score_rows([row["image_id"] for row in descriptor_rows], dino, "dinov2_vitl14", int(descriptor_contract["top_k"]))
    measurements, supported, unsupported = classify_pairs(pairs, mega_scores, dino_scores)
    quality = scoring.measure_quality(images, paths)
    local = scoring.measure_local(supported, paths)
    percentiles = percentile_reference(quality, reference)
    feature_rows, raw = scoring.score(bundle, scoring.build_feature_frame(supported, quality, local, percentiles)) if supported else ([], [])
    calibrated = apply_calibration(raw, contract)
    write_csv(output_dir / "descriptor_pair_measurements.csv", measurements, PAIR_MEASUREMENT_COLUMNS)
    write_csv(output_dir / "supported_pair_manifest.csv", supported, SCORED_PAIR_COLUMNS)
    write_csv(output_dir / "unsupported_pair_manifest.csv", unsupported, UNSUPPORTED_COLUMNS)
    write_csv(output_dir / "automatic_quality_measurements.csv", quality, scoring.QUALITY_COLUMNS)
    write_csv(output_dir / "quality_reference_percentiles.csv", percentiles, scoring.REFERENCE_COLUMNS)
    write_csv(output_dir / "local_match_measurements.csv", local, scoring.LOCAL_COLUMNS)
    feature_fields = list(feature_rows[0]) if feature_rows else ["canonical_pair_id"]
    write_csv(output_dir / "frozen_model_score_inputs.csv", feature_rows, feature_fields)
    write_csv(output_dir / "frozen_model_calibrated_predictions.csv", calibrated, PREDICTION_COLUMNS)
    audit = {
        "status": "PASS", "created_at_utc": utc_now(), "package_manifest_sha256": package_sha,
        "contract_sha256": contract_sha, "verified_image_count": len(paths), "candidate_pair_count": len(pairs),
        "supported_pair_count": len(supported), "unsupported_pair_count": len(unsupported),
        "model_prediction_count": len(calibrated), "batch_size": batch_size, "device": torch.cuda.get_device_name(0),
        "python": platform.python_version(), "confirmation_outcomes_accessed": False,
        "descriptor_runs": [mega_audit, dino_audit], "claim_boundary": contract["claim_boundary"],
    }
    write_json(output_dir / "run_audit.json", audit)
    return audit


def validate(package_root: Path, results_dir: Path) -> dict[str, Any]:
    contract, pairs, images, reference, bundle = load_inputs(package_root.resolve())
    failures: list[str] = []
    try:
        descriptor_rows = [{"image_id": row["candidate_image_id"], "content_sha256": row["content_sha256"]} for row in images]
        failures.extend(validate_descriptor_outputs(results_dir, descriptor_rows, contract, sha256(package_root / "contracts/task15m_confirmation_execution_contract.json")))
        measurements = read_csv_exact(results_dir / "descriptor_pair_measurements.csv", PAIR_MEASUREMENT_COLUMNS)
        supported = read_csv_exact(results_dir / "supported_pair_manifest.csv", SCORED_PAIR_COLUMNS)
        unsupported = read_csv_exact(results_dir / "unsupported_pair_manifest.csv", UNSUPPORTED_COLUMNS)
        quality = read_csv_exact(results_dir / "automatic_quality_measurements.csv", scoring.QUALITY_COLUMNS)
        percentiles = read_csv_exact(results_dir / "quality_reference_percentiles.csv", scoring.REFERENCE_COLUMNS)
        local = read_csv_exact(results_dir / "local_match_measurements.csv", scoring.LOCAL_COLUMNS)
        predictions = read_csv_exact(results_dir / "frozen_model_calibrated_predictions.csv", PREDICTION_COLUMNS)
        all_ids = {row["canonical_pair_id"] for row in pairs}
        supported_ids, unsupported_ids = {row["canonical_pair_id"] for row in supported}, {row["canonical_pair_id"] for row in unsupported}
        if len(measurements) != len(pairs) or {row["canonical_pair_id"] for row in measurements} != all_ids:
            failures.append("descriptor_measurement_coverage")
        if supported_ids & unsupported_ids or supported_ids | unsupported_ids != all_ids:
            failures.append("unsupported_disposition")
        if any(row["descriptor_support_category"] not in {"both_agreement", "both_reciprocal"} for row in supported):
            failures.append("unsupported_pair_scored")
        if len(quality) != len(images) or len(percentiles) != len(images) or any(row["failure_code"] != "none" for row in quality):
            failures.append("quality_measurement")
        if len(local) != len(supported_ids) or {row["canonical_pair_id"] for row in local} != supported_ids:
            failures.append("local_measurement")
        expected_predictions = {(identifier, model) for identifier in supported_ids for model in ("P3", "P5")}
        if {(row["canonical_pair_id"], row["model_id"]) for row in predictions} != expected_predictions:
            failures.append("prediction_coverage")
        for row in predictions:
            for key in ("raw_probability_not_ready_or_uncertain", "calibrated_probability_not_ready_or_uncertain"):
                value = float(row[key])
                if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                    failures.append("invalid_probability")
                    break
        feature_fields = ["canonical_pair_id"] + [f"P3__{column}" for column in bundle["models"]["P3"]["feature_columns"]] + [f"P5__{column}" for column in bundle["models"]["P5"]["feature_columns"]]
        features = read_csv_exact(results_dir / "frozen_model_score_inputs.csv", feature_fields)
        if {row["canonical_pair_id"] for row in features} != supported_ids or len(features) != len(supported_ids):
            failures.append("frozen_feature_coverage")
        audit = json.loads((results_dir / "run_audit.json").read_text(encoding="utf-8"))
        if audit.get("status") != "PASS" or audit.get("confirmation_outcomes_accessed") is not False:
            failures.append("run_audit")
    except Exception as error:
        failures.append(f"inventory:{type(error).__name__}")
    result = {"status": "PASS" if not failures else "FAIL", "validated_at_utc": utc_now(), "candidate_pair_count": len(pairs), "image_count": len(images), "failures": failures, "confirmation_outcomes_accessed": False}
    write_json(results_dir / "validation_audit.json", result)
    if failures:
        raise RuntimeError("validation failed: " + "; ".join(failures))
    return result


def export_results(results_dir: Path, zip_path: Path) -> dict[str, Any]:
    if zip_path.exists():
        raise FileExistsError(f"refusing to overwrite export: {zip_path}")
    validation = json.loads((results_dir / "validation_audit.json").read_text(encoding="utf-8"))
    if validation.get("status") != "PASS":
        raise RuntimeError("a passing validate command is required before export")
    required = [results_dir / name for name in [
        "descriptor_pair_measurements.csv", "supported_pair_manifest.csv", "unsupported_pair_manifest.csv",
        "automatic_quality_measurements.csv", "quality_reference_percentiles.csv", "local_match_measurements.csv",
        "frozen_model_score_inputs.csv", "frozen_model_calibrated_predictions.csv", "run_audit.json", "validation_audit.json",
    ]]
    for descriptor_name, score_file in (("megadescriptor_l_384", "pair_scores.csv"), ("dinov2_vitl14", "scores.csv")):
        required.extend([results_dir / descriptor_name / name for name in ("embeddings.npy", "embedding_manifest_v2.csv", score_file, "run_audit.json")])
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("result inventory incomplete")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in required:
            archive.write(path, arcname=f"PF_ERI_TASK15M_CONFIRMATION_FINAL_EXPORT/{path.relative_to(results_dir)}")
    if zipfile.ZipFile(zip_path).testzip() is not None:
        raise RuntimeError("export ZIP CRC failure")
    result = {"status": "PASS", "created_at_utc": utc_now(), "zip": zip_path.name, "zip_sha256": sha256(zip_path), "file_count": len(required)}
    write_json(results_dir / "export_audit.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--package-root", type=Path, default=Path("."))
    run_parser.add_argument("--image-root", type=Path, default=Path("images"))
    run_parser.add_argument("--output-dir", type=Path, required=True)
    run_parser.add_argument("--batch-size", type=int, default=16)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--package-root", type=Path, default=Path("."))
    validate_parser.add_argument("--results-dir", type=Path, required=True)
    export_parser = sub.add_parser("export")
    export_parser.add_argument("--results-dir", type=Path, required=True)
    export_parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            if args.batch_size < 1:
                raise ValueError("batch size must be positive")
            result = run(args.package_root, args.image_root, args.output_dir, args.batch_size)
        elif args.command == "validate":
            result = validate(args.package_root, args.results_dir)
        else:
            result = export_results(args.results_dir.resolve(), args.zip.resolve())
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
