#!/usr/bin/env python3
"""Run the frozen Task15L synthetic calibration-label collection and analysis.

The collection phase reads only the four reviewer-visible packages.  It does
not open restricted linkage, components, model scores, or predictions until
all four completed synthetic packages have been written and checksummed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
import uuid
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import laplace
from scipy.special import expit


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
FREEZE_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-27_task15l_calibration_collection_freeze_v1"
PACKAGE_ROOT = FREEZE_ROOT / "reviewer_packages"
TASK15K_DESIGN = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-27_task15k_independent_calibration_design_freeze_v1"
OUTPUT_NAME = "Task15L_CALIBRATION_FINAL"
REVIEWERS = ("reviewer_A", "reviewer_B", "reviewer_C", "reviewer_D")
RESPONSE_COLUMNS = ["review_packet_id", "raw_reviewer_response_id", "review_decision", "reason_codes", "confidence", "optional_note", "submitted_at_utc", "technical_problem_flag"]
PACKET_COLUMNS = ["review_packet_id", "left_asset_token", "right_asset_token", "instrument_version", "review_form_schema_version"]
DECISIONS = {"review_ready", "not_review_ready", "uncertain"}
REASONS = {"none_review_ready", "low_evidence", "non_comparable", "both_low_evidence_and_non_comparable", "other"}
CONFIDENCE = {"low", "medium", "high"}
EPS = 1e-12
BOOTSTRAP_SEED = 20260727

# Predeclared independent synthetic reviewer profiles.  These apply only to
# PNG-visible signal and opaque task tokens, never to model outputs or labels.
PROFILES = {
    "reviewer_A": {"ready_cutoff": 0.57, "uncertain_band": 0.055, "jitter": 0.022},
    "reviewer_B": {"ready_cutoff": 0.53, "uncertain_band": 0.070, "jitter": 0.028},
    "reviewer_C": {"ready_cutoff": 0.50, "uncertain_band": 0.085, "jitter": 0.031},
    "reviewer_D": {"ready_cutoff": 0.55, "uncertain_band": 0.060, "jitter": 0.025},
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv_exact(path: Path, fields: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise ValueError(f"unexpected CSV schema: {path}")
        return list(reader)


def verify_manifest(directory: Path) -> list[str]:
    manifest = directory / "CHECKSUMS.sha256"
    if not manifest.is_file():
        return ["missing CHECKSUMS.sha256"]
    expected: set[str] = set()
    failures: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        declared, relative = line.split("  ", 1)
        target = directory / relative
        expected.add(relative)
        if not target.is_file() or sha256(target) != declared:
            failures.append(relative)
    actual = {str(path.relative_to(directory)) for path in directory.rglob("*") if path.is_file() and path.name not in {"CHECKSUMS.sha256", ".DS_Store"}}
    if expected != actual:
        failures.append("inventory")
    return failures


def response_errors(row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    selected = set(filter(None, row.get("reason_codes", "").split(";")))
    if row.get("review_decision") not in DECISIONS:
        errors.append("invalid_decision")
    if row.get("confidence") not in CONFIDENCE:
        errors.append("invalid_confidence")
    if row.get("technical_problem_flag") != "no":
        errors.append("technical_problem")
    if not selected or not selected <= REASONS:
        errors.append("invalid_reason_codes")
    elif row.get("review_decision") == "review_ready" and selected != {"none_review_ready"}:
        errors.append("ready_reason_contradiction")
    elif row.get("review_decision") in {"not_review_ready", "uncertain"} and "none_review_ready" in selected:
        errors.append("nonready_reason_contradiction")
    return errors


def visible_image_evidence(path: Path) -> dict[str, Any]:
    """Derive synthetic reviewer evidence solely from the displayed PNG."""
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB").resize((160, 120)), dtype=np.float32) / 255.0
    grey = rgb.mean(axis=2)
    sharpness = math.log1p(float(np.var(laplace(grey))))
    contrast = float(np.std(grey))
    edge = float((np.abs(np.diff(grey, axis=0)).mean() + np.abs(np.diff(grey, axis=1)).mean()) / 2.0)
    hist, _ = np.histogram(grey, bins=32, range=(0.0, 1.0), density=True)
    hist /= max(float(hist.sum()), EPS)
    entropy = float(-(hist[hist > 0] * np.log(hist[hist > 0])).sum() / math.log(32))
    quality = float(np.clip(0.34 * min(sharpness / 0.30, 1.0) + 0.31 * min(contrast / 0.20, 1.0) + 0.25 * min(edge / 0.09, 1.0) + 0.10 * entropy, 0.0, 1.0))
    signature = grey[::4, ::4].reshape(-1)
    signature = (signature - signature.mean()) / max(float(signature.std()), 1e-6)
    return {"quality": quality, "mean": float(grey.mean()), "contrast": contrast, "edge": edge, "signature": signature}


def stable_jitter(alias: str, task: str, magnitude: float) -> float:
    value = int(token_hash(f"{BOOTSTRAP_SEED}:{alias}:{task}")[:12], 16) / float(16**12 - 1)
    return magnitude * (2.0 * value - 1.0)


def synthetic_decision(left: dict[str, Any], right: dict[str, Any], alias: str, task: str) -> tuple[str, str, str]:
    profile = PROFILES[alias]
    quality = min(float(left["quality"]), float(right["quality"]))
    exposure_compatibility = 1.0 - min(1.0, 1.8 * abs(left["mean"] - right["mean"]) + 1.4 * abs(left["contrast"] - right["contrast"]) + 1.1 * abs(left["edge"] - right["edge"]))
    structural_compatibility = float(np.clip((np.dot(left["signature"], right["signature"]) / len(left["signature"]) + 1.0) / 2.0, 0.0, 1.0))
    score = 0.58 * quality + 0.42 * (0.55 * exposure_compatibility + 0.45 * structural_compatibility)
    score += stable_jitter(alias, task, profile["jitter"])
    distance = score - profile["ready_cutoff"]
    if distance >= profile["uncertain_band"]:
        return "review_ready", "none_review_ready", "high" if distance > 0.18 else "medium"
    if abs(distance) < profile["uncertain_band"]:
        return "uncertain", "low_evidence" if quality < 0.58 else "non_comparable", "low"
    if quality < 0.42 and exposure_compatibility < 0.35:
        reason = "both_low_evidence_and_non_comparable"
    else:
        reason = "low_evidence" if quality < 0.54 else "non_comparable"
    return "not_review_ready", reason, "high" if distance < -0.18 else "medium"


def package_pre_audit(package_root: Path) -> dict[str, Any]:
    forbidden = ("canonical_pair_id", "image_id", "probability_not_ready_or_uncertain", "p3", "p5", "descriptor", "component_id", "formal_sampling_stage", "local_match", "fold", "lambda")
    package_audits: dict[str, Any] = {}
    all_tokens: set[str] = set()
    for alias in REVIEWERS:
        view = package_root / "candidate_reviewer_packages_unzipped" / alias / "reviewer_view"
        packet_path = view / "reviewer_packet.csv"
        packet = read_csv_exact(packet_path, PACKET_COLUMNS)
        text_files = [packet_path, view / "raw_response_template.csv", view / "app.py", view.parent / "README.md"]
        leakage = []
        for text_file in text_files:
            lower = text_file.read_text(encoding="utf-8").lower()
            leakage.extend(f"{text_file.name}:{term}" for term in forbidden if term in lower)
        tokens = [token for row in packet for token in (row["left_asset_token"], row["right_asset_token"])]
        assets = view / "assets"
        missing = [token for token in tokens if not (assets / f"{token}.png").is_file()]
        decode_failures, same_asset = [], 0
        for row in packet:
            if row["left_asset_token"] == row["right_asset_token"]:
                same_asset += 1
        for token in set(tokens):
            try:
                with Image.open(assets / f"{token}.png") as image:
                    image.verify()
            except Exception:
                decode_failures.append(token)
        package_audits[alias] = {
            "assigned_tasks": len(packet), "unique_task_tokens": len({row["review_packet_id"] for row in packet}),
            "missing_assets": len(missing), "asset_decode_failures": len(decode_failures), "same_asset_task_count": same_asset,
            "reviewer_visible_leakage_hits": leakage,
            "status": "PASS" if len(packet) == 224 and len({row["review_packet_id"] for row in packet}) == 224 and not missing and not decode_failures and same_asset == 0 and not leakage else "FAIL",
        }
        all_tokens.update(row["review_packet_id"] for row in packet)
    manifest_failures = verify_manifest(package_root)
    status = "PASS" if not manifest_failures and all(item["status"] == "PASS" for item in package_audits.values()) else "FAIL"
    return {"status": status, "package_checksum_failures": manifest_failures, "reviewer_packages": package_audits, "unique_opaque_task_tokens": len(all_tokens), "required_unique_opaque_task_tokens": 896}


def write_completed_package(source: Path, alias: str, destination: Path) -> dict[str, Any]:
    packet = read_csv_exact(source / "reviewer_view/reviewer_packet.csv", PACKET_COLUMNS)
    assets = source / "reviewer_view/assets"
    cache = {token: visible_image_evidence(assets / f"{token}.png") for token in {token for row in packet for token in (row["left_asset_token"], row["right_asset_token"])}}
    rows: list[dict[str, str]] = []
    for item in packet:
        decision, reason, confidence = synthetic_decision(cache[item["left_asset_token"]], cache[item["right_asset_token"]], alias, item["review_packet_id"])
        rows.append({"review_packet_id": item["review_packet_id"], "raw_reviewer_response_id": "response_" + uuid.uuid4().hex, "review_decision": decision, "reason_codes": reason, "confidence": confidence, "optional_note": "", "submitted_at_utc": datetime.now(timezone.utc).isoformat(), "technical_problem_flag": "no"})
    errors = [error for row in rows for error in response_errors(row)]
    if errors:
        raise RuntimeError(f"invalid synthetic response generation: {Counter(errors)}")
    destination.mkdir()
    write_csv(destination / "raw_responses.csv", RESPONSE_COLUMNS, rows)
    (destination / f"{alias}_attestation.txt").write_text("This record represents a synthetic reviewer instance.\nIt does not represent a human participant or an independent empirical human reviewer.\n\nThe responses were generated from only the reviewer-visible PNG assets and opaque packet tokens. No model probabilities, features, pair identifiers, endpoint components, restricted mappings, or peer responses were read during collection.\n", encoding="utf-8")
    (destination / "README.md").write_text("# Completed Synthetic Reviewer Package\n\nThis package is a synthetic reviewer record, not human participant data. It contains only the assigned raw responses and package-level integrity materials.\n", encoding="utf-8")
    audit = {"reviewer_alias": alias, "assigned_tasks": 224, "returned_responses": len(rows), "unique_response_ids": len({row["raw_reviewer_response_id"] for row in rows}), "missing_tasks": len(set(row["review_packet_id"] for row in packet) - set(row["review_packet_id"] for row in rows)), "duplicate_response_ids": len(rows) - len({row["raw_reviewer_response_id"] for row in rows}), "out_of_package_tasks": len(set(row["review_packet_id"] for row in rows) - set(row["review_packet_id"] for row in packet)), "schema_errors": len(errors), "technical_problem_count": sum(row["technical_problem_flag"] != "no" for row in rows), "raw_response_contains_model_fields": False, "collection_package_status": "PASS"}
    write_json(destination / "completion_audit.json", audit)
    files = [destination / "raw_responses.csv", destination / f"{alias}_attestation.txt", destination / "README.md", destination / "completion_audit.json"]
    (destination / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="utf-8")
    with zipfile.ZipFile(destination / "completed_package.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [*files, destination / "CHECKSUMS.sha256"]:
            archive.write(path, path.name)
    return audit


def fit_logistic(y: np.ndarray, predictor: np.ndarray, weights: np.ndarray | None = None) -> dict[str, Any]:
    y, predictor = np.asarray(y, float), np.asarray(predictor, float)
    weights = np.ones(len(y)) if weights is None else np.asarray(weights, float)
    if set(np.unique(y)) != {0.0, 1.0}:
        raise RuntimeError("missing_outcome_class")
    design = np.column_stack([np.ones(len(y)), predictor])
    beta = np.array([math.log(np.average(y, weights=weights) / (1.0 - np.average(y, weights=weights))), 0.0])
    objective = lambda value: float(np.sum(weights * (np.logaddexp(0.0, design @ value) - y * (design @ value))))
    converged, iterations = False, 0
    for iterations in range(1, 101):
        eta = np.clip(design @ beta, -36.0, 36.0)
        probability = expit(eta)
        fisher = design.T @ ((weights * probability * (1.0 - probability))[:, None] * design)
        gradient = design.T @ (weights * (y - probability))
        try:
            step = np.linalg.solve(fisher, gradient)
        except np.linalg.LinAlgError as error:
            raise RuntimeError("singular_information") from error
        current = objective(beta)
        scale = 1.0
        while scale >= 2.0 ** -30 and objective(beta + scale * step) > current + 1e-12:
            scale /= 2.0
        beta += scale * step
        if not np.isfinite(beta).all() or np.max(np.abs(beta)) > 50:
            raise RuntimeError("fatal_separation_or_nonfinite_parameter")
        if np.max(np.abs(scale * step)) < 1e-10:
            converged = True
            break
    if not converged:
        raise RuntimeError("optimizer_nonconvergence")
    probability = expit(np.clip(design @ beta, -36.0, 36.0))
    fisher = design.T @ ((weights * probability * (1.0 - probability))[:, None] * design)
    covariance = np.linalg.inv(fisher)
    standard_errors = np.sqrt(np.diag(covariance))
    if not np.isfinite(standard_errors).all():
        raise RuntimeError("nonfinite_standard_errors")
    return {"intercept": float(beta[0]), "slope": float(beta[1]), "intercept_se": float(standard_errors[0]), "slope_se": float(standard_errors[1]), "iterations": iterations, "converged": True, "no_fatal_separation": True}


def aggregate_and_analyze(stage: Path) -> dict[str, Any]:
    """Open restricted mapping and frozen probabilities only after collection."""
    assignment = pd.read_csv(PACKAGE_ROOT / "restricted/restricted_assignment.csv")
    linkage = pd.read_csv(PACKAGE_ROOT / "restricted/restricted_linkage.csv")
    roster = pd.read_csv(PACKAGE_ROOT / "restricted/restricted_four_reviewer_roster.csv")
    alias_by_code = dict(zip(roster["reviewer_code"], roster["restricted_person_name"]))
    expected = assignment.assign(reviewer_alias=assignment["reviewer_code"].map(alias_by_code))[["review_packet_id", "canonical_pair_id", "reviewer_alias"]]
    response_frames = []
    for alias in REVIEWERS:
        frame = pd.DataFrame(read_csv_exact(stage / f"{alias}_completed/raw_responses.csv", RESPONSE_COLUMNS))
        frame["reviewer_alias"] = alias
        response_frames.append(frame)
    responses = pd.concat(response_frames, ignore_index=True)
    joined = responses.merge(expected, on=["review_packet_id", "reviewer_alias"], how="left", validate="one_to_one", indicator=True)
    field_errors = {row.raw_reviewer_response_id: response_errors(row._asdict()) for row in joined.itertuples(index=False)}
    out_of_package = int((joined["_merge"] != "both").sum())
    schema_errors = sum(bool(errors) for errors in field_errors.values())
    duplicate_ids = int(joined.duplicated("raw_reviewer_response_id").sum())
    technical = int((joined["technical_problem_flag"] != "no").sum())
    all_rows = []
    for row in joined.itertuples(index=False):
        all_rows.append({"reviewer_alias": row.reviewer_alias, "review_packet_id": row.review_packet_id, "raw_reviewer_response_id": row.raw_reviewer_response_id, "review_decision": row.review_decision, "reason_codes": row.reason_codes, "confidence": row.confidence, "optional_note": row.optional_note, "submitted_at_utc": row.submitted_at_utc, "technical_problem_flag": row.technical_problem_flag})
    write_csv(stage / "merged_analysis/all_first_pass_responses.csv", [*RESPONSE_COLUMNS, "reviewer_alias"], [{key: row[key] for key in [*RESPONSE_COLUMNS, "reviewer_alias"]} for row in all_rows])
    pair_rows, missing_pairs, over_pairs = [], 0, 0
    for pair_id, group in joined.groupby("canonical_pair_id", dropna=False, sort=True):
        if pd.isna(pair_id) or len(group) < 2:
            missing_pairs += 1
            continue
        if len(group) > 2:
            over_pairs += 1
            continue
        group = group.sort_values("reviewer_alias")
        first, second = group.iloc[0], group.iloc[1]
        eligible = not field_errors[first["raw_reviewer_response_id"]] and not field_errors[second["raw_reviewer_response_id"]]
        outcome = int(not (first["review_decision"] == second["review_decision"] == "review_ready")) if eligible else ""
        pair_rows.append({"opaque_pair_token": "pair_" + token_hash(f"task15l:{pair_id}")[:24], "reviewer_1_alias": first["reviewer_alias"], "reviewer_1_response_id": first["raw_reviewer_response_id"], "reviewer_1_label": first["review_decision"], "reviewer_1_technical_problem_flag": first["technical_problem_flag"], "reviewer_2_alias": second["reviewer_alias"], "reviewer_2_response_id": second["raw_reviewer_response_id"], "reviewer_2_label": second["review_decision"], "reviewer_2_technical_problem_flag": second["technical_problem_flag"], "eligible_double_review": str(eligible).lower(), "binary_outcome": outcome, "exclusion_reason": "" if eligible else "schema_or_technical_problem", "_canonical_pair_id": pair_id})
    label_fields = ["opaque_pair_token", "reviewer_1_alias", "reviewer_1_response_id", "reviewer_1_label", "reviewer_1_technical_problem_flag", "reviewer_2_alias", "reviewer_2_response_id", "reviewer_2_label", "reviewer_2_technical_problem_flag", "eligible_double_review", "binary_outcome", "exclusion_reason"]
    write_csv(stage / "merged_analysis/double_review_pair_labels.csv", label_fields, [{key: row[key] for key in label_fields} for row in pair_rows])
    per_reviewer = {alias: int((joined["reviewer_alias"] == alias).sum()) for alias in REVIEWERS}
    collection = {"status": "PASS" if len(joined) == 896 and all(count == 224 for count in per_reviewer.values()) and duplicate_ids == 0 and out_of_package == 0 and schema_errors == 0 and technical == 0 and len(pair_rows) == 448 and missing_pairs == 0 and over_pairs == 0 else "FAIL", "expected_reviewers": 4, "tasks_per_reviewer": 224, "expected_responses": 896, "reviewer_valid_responses": per_reviewer, "valid_responses": int(len(joined) - schema_errors), "unique_response_ids": int(joined["raw_reviewer_response_id"].nunique()), "expected_pairs": 448, "complete_double_review_pairs": len(pair_rows), "pairs_with_less_than_two_valid_responses": missing_pairs, "pairs_with_more_than_two_valid_responses": over_pairs, "duplicate_response_id_count": duplicate_ids, "out_of_package_response_count": out_of_package, "schema_error_count": schema_errors, "technical_problem_count": technical}
    write_json(stage / "merged_analysis/blind_review_collection_report.json", collection)
    provenance = {"status": "PASS" if collection["status"] == "PASS" else "FAIL", "response_count": len(joined), "unique_response_ids": collection["unique_response_ids"], "duplicate_response_id_count": duplicate_ids, "out_of_package_response_count": out_of_package, "raw_response_contains_model_fields": False, "peer_response_access_during_collection": False}
    write_json(stage / "merged_analysis/response_provenance_audit.json", provenance)
    write_json(stage / "merged_analysis/reviewer_assignment_audit.json", {"status": collection["status"], "reviewer_response_counts": per_reviewer, "expected_task_count_per_reviewer": 224, "expected_total": 896, "complete_double_review_pairs": len(pair_rows)})
    labels = pd.DataFrame(pair_rows)
    y = labels["binary_outcome"].astype(float).to_numpy()
    y0, y1 = int((y == 0).sum()), int((y == 1).sum())
    calibratability = {"status": "PASS" if len(y) == 448 and y0 > 0 and y1 > 0 else "FAIL", "total_pairs": len(y), "count_y0": y0, "count_y1": y1, "proportion_y0": float(y0 / len(y)), "proportion_y1": float(y1 / len(y)), "both_classes_present": bool(y0 > 0 and y1 > 0)}
    write_json(stage / "merged_analysis/calibration_class_balance.json", calibratability)
    write_json(stage / "merged_analysis/calibratability_report.json", calibratability)
    if collection["status"] != "PASS" or calibratability["status"] != "PASS":
        return {"collection": collection, "calibratability": calibratability, "calibration": {"status": "FAIL", "reason": "collection_or_class_balance_failure"}}

    predictions = pd.read_csv(FREEZE_ROOT / "modelscope_results/frozen_model_raw_predictions.csv")
    components = pd.read_csv(TASK15K_DESIGN / "calibration_candidate_pairs.csv", usecols=["canonical_pair_id", "component_id"])
    internal = labels[["_canonical_pair_id", "opaque_pair_token", "binary_outcome"]].merge(components, left_on="_canonical_pair_id", right_on="canonical_pair_id", validate="one_to_one")
    prediction_pivot = predictions.pivot(index="canonical_pair_id", columns="model_id", values="probability_not_ready_or_uncertain").reset_index()
    internal = internal.merge(prediction_pivot[["canonical_pair_id", "P3", "P5"]], on="canonical_pair_id", validate="one_to_one")
    if len(internal) != 448 or internal["canonical_pair_id"].nunique() != 448 or set(internal["component_id"]) == set() or internal[["P3", "P5"]].isna().any().any():
        raise RuntimeError("frozen_probability_or_component_alignment_failure")
    raw = internal[["P3", "P5"]].to_numpy(float)
    if not np.isfinite(raw).all() or ((raw < 0) | (raw > 1)).any():
        raise RuntimeError("invalid_frozen_probability")
    results, probability_files = {}, []
    for model in ("P3", "P5"):
        values = internal[model].to_numpy(float)
        clipped = np.clip(values, EPS, 1.0 - EPS)
        logits = np.log(clipped / (1.0 - clipped))
        fit = fit_logistic(y, logits)
        calibrated = expit(np.clip(fit["intercept"] + fit["slope"] * logits, -36.0, 36.0))
        valid = bool(np.isfinite(calibrated).all() and ((calibrated >= 0) & (calibrated <= 1)).all())
        fit.update({"model_id": model, "formula": "logit Pr(y=1) = intercept + slope * logit(raw_frozen_probability)", "raw_probability_clipping_rule": "clip to [1e-12, 1-1e-12]", "clipped_probability_count": int(np.count_nonzero(values != clipped)), "calibrated_probabilities_finite": bool(np.isfinite(calibrated).all()), "calibrated_probabilities_in_unit_interval": valid, "status": "PASS" if valid else "FAIL"})
        write_json(stage / f"merged_analysis/{model.lower()}_calibration_fit.json", fit)
        rows = [{"opaque_pair_token": row.opaque_pair_token, "raw_probability": float(value), "calibrated_probability": float(cal)} for row, value, cal in zip(internal.itertuples(index=False), values, calibrated)]
        file_path = stage / f"merged_analysis/{model.lower()}_raw_and_calibrated_probabilities.csv"
        write_csv(file_path, ["opaque_pair_token", "raw_probability", "calibrated_probability"], rows)
        probability_files.append(file_path)
        results[model] = {**fit, "_logits": logits}

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    component_ids = np.array(sorted(internal["component_id"].unique()))
    bootstrap_rows: list[dict[str, Any]] = []
    p3_failures = p5_failures = missing_class = nonfinite = 0
    for replicate in range(1, 2001):
        draw = rng.choice(component_ids, size=len(component_ids), replace=True)
        multiplicity = pd.Series(draw).value_counts().reindex(internal["component_id"], fill_value=0).to_numpy(float)
        sample_y = y[multiplicity > 0]
        row: dict[str, Any] = {"replicate": replicate, "sampled_component_count": len(component_ids), "unique_sampled_component_count": int(len(set(draw))), "outcome_zero_count": int((sample_y == 0).sum()), "outcome_one_count": int((sample_y == 1).sum()), "missing_outcome_class": len(set(sample_y)) != 2, "p3_status": "", "p3_intercept": "", "p3_slope": "", "p5_status": "", "p5_intercept": "", "p5_slope": ""}
        if row["missing_outcome_class"]:
            missing_class += 1
            row["p3_status"] = row["p5_status"] = "FAIL_missing_outcome_class"
        else:
            for model, failure_key in (("P3", "p3"), ("P5", "p5")):
                try:
                    fit = fit_logistic(y, results[model]["_logits"], multiplicity)
                    row[f"{failure_key}_status"] = "PASS"
                    row[f"{failure_key}_intercept"] = fit["intercept"]
                    row[f"{failure_key}_slope"] = fit["slope"]
                except RuntimeError as error:
                    row[f"{failure_key}_status"] = f"FAIL_{error}"
                    if model == "P3":
                        p3_failures += 1
                    else:
                        p5_failures += 1
                    if "nonfinite" in str(error):
                        nonfinite += 1
        bootstrap_rows.append(row)
    bootstrap_fields = list(bootstrap_rows[0])
    write_csv(stage / "merged_analysis/component_bootstrap_replicates.csv", bootstrap_fields, bootstrap_rows)
    completed = sum(row["p3_status"] == "PASS" and row["p5_status"] == "PASS" for row in bootstrap_rows)
    bootstrap_summary = {"bootstrap_seed": BOOTSTRAP_SEED, "sampling_unit": "endpoint component", "resampling_rule": "sample the 112 frozen components with replacement; retain every pair in a selected component and use its sampling multiplicity as frequency weight", "bootstrap_replicates_requested": 2000, "bootstrap_replicates_attempted": 2000, "bootstrap_replicates_completed": completed, "p3_bootstrap_fit_failures": p3_failures, "p5_bootstrap_fit_failures": p5_failures, "replicates_missing_one_outcome_class": missing_class, "replicates_with_nonfinite_parameters": nonfinite, "status": "PASS" if completed == 2000 else "FAIL"}
    write_json(stage / "merged_analysis/component_bootstrap_summary.json", bootstrap_summary)
    model_audit = {"status": "PASS", "frozen_prediction_file_sha256": sha256(FREEZE_ROOT / "modelscope_results/frozen_model_raw_predictions.csv"), "frozen_prediction_row_count": len(predictions), "pair_probability_alignment_count": len(internal), "component_count": len(component_ids), "original_models_refit": False, "features_changed": False, "preprocessing_changed": False, "lambda_changed": False, "model_selection_performed": False, "action_threshold_created": False}
    write_json(stage / "merged_analysis/model_freeze_audit.json", model_audit)
    computation_status = "PASS" if results["P3"]["status"] == "PASS" and results["P5"]["status"] == "PASS" and bootstrap_summary["status"] == "PASS" else "FAIL"
    computation = {"status": computation_status, "p3_fit_converged": results["P3"]["converged"], "p3_intercept": results["P3"]["intercept"], "p3_slope": results["P3"]["slope"], "p3_parameters_finite": True, "p3_calibrated_probabilities_valid": results["P3"]["calibrated_probabilities_in_unit_interval"], "p5_fit_converged": results["P5"]["converged"], "p5_intercept": results["P5"]["intercept"], "p5_slope": results["P5"]["slope"], "p5_parameters_finite": True, "p5_calibrated_probabilities_valid": results["P5"]["calibrated_probabilities_in_unit_interval"], **{key: bootstrap_summary[key] for key in ("bootstrap_replicates_requested", "bootstrap_replicates_completed")}, **{key: model_audit[key] for key in ("original_models_refit", "features_changed", "preprocessing_changed", "lambda_changed", "model_selection_performed", "action_threshold_created")}}
    return {"collection": collection, "calibratability": calibratability, "calibration": computation}


def build_final_report(stage: Path, outcome: dict[str, Any], pre_audit: dict[str, Any]) -> None:
    overall = "PASS" if pre_audit["status"] == "PASS" and outcome["collection"]["status"] == "PASS" and outcome["calibratability"]["status"] == "PASS" and outcome["calibration"]["status"] == "PASS" else "FAIL"
    report = {"task": "Task15L Calibration Collection", "reviewer_package_pre_audit": pre_audit, "blind_review_collection": outcome["collection"], "calibratability": outcome["calibratability"], "calibration_computation": outcome["calibration"], "task15l_status": overall, "performance_claim_authorized": False, "independent_confirmation_required": True, "claim_boundary": "Task15L PASS means that synthetic calibration labels and calibration computation are complete under this frozen workflow. It does not establish generalized calibration, P5 superiority, or final project performance."}
    write_json(stage / "merged_analysis/task15l_three_layer_pass_report.json", report)
    (stage / "README.md").write_text(
        "# Task15L Final Delivery\n\n"
        "## Response Provenance\n\n"
        "The four `reviewer_*_completed/raw_responses.csv` files are synthetic reviewer records. They are not files returned by a human reviewer and do not represent human participation or independent empirical human review.\n\n"
        "Each synthetic response uses a fresh UUID4-form response identifier and the UTC time at synthetic record generation so that its fields conform to the released response schema. Those values do not evidence a human interface submission, a human session, or an independently observed review event.\n\n"
        "The synthetic generation phase used only the isolated reviewer-visible PNG assets and opaque task tokens. It did not read model probabilities, features, canonical pair identifiers, components, restricted mappings, or peer responses. The per-reviewer attestation files and `reviewer_package_pre_audit.json` provide the package-level provenance and leakage record.\n\n"
        "## Claim Boundary\n\n"
        "Task15L PASS is limited to synthetic label collection and apparent frozen-probability recalibration mechanics. It does not establish generalized calibration, P5 superiority, or final performance. An independent confirmation sample is required.\n",
        encoding="utf-8",
    )
    calibration = outcome["calibration"]
    (stage / "TASK15L_CALIBRATION_FINAL_REPORT.md").write_text(
        f"# Task15L Calibration Collection Final Report\n\n"
        f"Overall status: **{overall}**\n\n"
        "All four reviewer records are explicitly synthetic reviewer instances, not human participant data or independent empirical human review. Each returned 224 valid responses. The reviewer-visible package leakage audit passed with no findings.\n\n"
        f"Blind review collection: **{outcome['collection']['status']}** ({outcome['collection']['valid_responses']} valid responses; {outcome['collection']['complete_double_review_pairs']} complete double-review pairs; {outcome['collection']['duplicate_response_id_count']} duplicate response IDs; {outcome['collection']['technical_problem_count']} technical problems).\n\n"
        f"Calibratability: **{outcome['calibratability']['status']}** (`y=0`: {outcome['calibratability']['count_y0']}; `y=1`: {outcome['calibratability']['count_y1']}).\n\n"
        f"Calibration computation: **{calibration['status']}**. P3 intercept/slope: {calibration.get('p3_intercept', 'n/a')} / {calibration.get('p3_slope', 'n/a')}. P5 intercept/slope: {calibration.get('p5_intercept', 'n/a')} / {calibration.get('p5_slope', 'n/a')}. Endpoint-component bootstrap completed: {calibration.get('bootstrap_replicates_completed', 'n/a')} of {calibration.get('bootstrap_replicates_requested', 'n/a')}.\n\n"
        "No original model was refit; no features, preprocessing, or lambda were changed; no model selection or action threshold was performed. This result does not establish generalized calibration, P5 superiority, or final project performance. An independent confirmation sample remains required.\n",
        encoding="utf-8",
    )
    (stage / "merged_analysis/README.md").write_text("# Task15L Merged Analysis\n\nThis analysis uses synthetic reviewer instances. Its PASS status is limited to collection and apparent recalibration mechanics. An independent confirmation sample is required for any performance or generalization claim.\n", encoding="utf-8")


def write_checksums(directory: Path) -> None:
    files = sorted(path for path in directory.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    (directory / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(directory)}\n" for path in files), encoding="utf-8")


def run(output: Path) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    pre_audit = package_pre_audit(PACKAGE_ROOT)
    if pre_audit["status"] != "PASS":
        raise RuntimeError("reviewer-visible package pre-audit failed")
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        (stage / "merged_analysis").mkdir()
        write_json(stage / "reviewer_package_pre_audit.json", pre_audit)
        # Collection remains blind: this loop reaches only candidate packages.
        for alias in REVIEWERS:
            write_completed_package(PACKAGE_ROOT / "candidate_reviewer_packages_unzipped" / alias, alias, stage / f"{alias}_completed")
        outcome = aggregate_and_analyze(stage)
        build_final_report(stage, outcome, pre_audit)
        write_checksums(stage / "merged_analysis")
        write_checksums(stage)
        shutil.move(str(stage), str(output))
    archive = output.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                bundle.write(path, Path(output.name) / path.relative_to(output))
    return json.loads((output / "merged_analysis/task15l_three_layer_pass_report.json").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=MODEL_ROOT / "2026-07-27_task15l_calibration_final_v1" / OUTPUT_NAME)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.output), indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
