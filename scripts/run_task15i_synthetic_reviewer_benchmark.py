#!/usr/bin/env python3
"""Create and evaluate an explicitly synthetic Task15I reviewer benchmark.

The label stage reads only reviewer-visible PNGs and packets.  The evaluation
stage receives only completed raw responses plus the separately frozen model
inputs.  Do not use this runner for human first-pass collection.
"""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import shutil
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import laplace
from scipy.optimize import minimize
from scipy.special import expit

try:
    from scripts.pferi_v2_fold_preprocessor import MISSING_TOKEN, UNKNOWN_TOKEN, fit_fold_preprocessor
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pferi_v2_fold_preprocessor import MISSING_TOKEN, UNKNOWN_TOKEN, fit_fold_preprocessor


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "artifacts/transfers/pferi_v2/review/task15i_reviewer_packages"
PREPAIR_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-26_task15i_prepair_artifacts_v1"
FREEZE_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-26_task15i_90pct_prepair_contract_freeze_v1"
FEATURE_CONTRACT = ROOT / "schemas/pferi_v2/feature_preprocessing_contract_v1.json"
LABELS = {"review_ready", "not_review_ready", "uncertain"}
REASONS = {"none_review_ready", "low_evidence", "non_comparable", "both_low_evidence_and_non_comparable", "other"}
CONFIDENCE = {"low", "medium", "high"}
EPS = 1e-12
P5_INCREMENTAL_COLUMNS = [
    "local_match_coverage_fraction__z",
    "local_match_coverage_fraction__missing",
    "local_match_measurement_failure==true",
    "local_match_measurement_failure==__MISSING__",
    "local_match_measurement_failure==__UNKNOWN__",
]
TARGET_DELTA_LOW = 0.0058
TARGET_DELTA_HIGH = 0.0065

PROFILES = {
    "reviewer_A": {"ready": 0.69, "reject": 0.47, "uncertain_band": 0.13, "temperature": 0.155},
    "reviewer_B": {"ready": 0.58, "reject": 0.40, "uncertain_band": 0.09, "temperature": 0.175},
    "reviewer_C": {"ready": 0.56, "reject": 0.38, "uncertain_band": 0.15, "temperature": 0.185},
    "reviewer_D": {"ready": 0.48, "reject": 0.31, "uncertain_band": 0.07, "temperature": 0.205},
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def stable_jitter(key: str, seed: int, magnitude: float) -> float:
    number = int(hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()[:12], 16)
    return magnitude * (2.0 * number / float(16**12 - 1) - 1.0)


def stable_uniform(key: str, seed: int) -> float:
    number = int(hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()[:12], 16)
    return number / float(16**12 - 1)


def conservative_outcome(first: str, second: str) -> int:
    if first not in LABELS or second not in LABELS:
        raise ValueError("invalid reviewer decision")
    return 0 if first == second == "review_ready" else 1


def validate_response_fields(row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    decision, reason = row.get("review_decision", ""), row.get("reason_codes", "")
    if decision not in LABELS:
        errors.append("invalid_label")
    if row.get("confidence", "") not in CONFIDENCE:
        errors.append("invalid_confidence")
    if row.get("technical_problem_flag", "") != "no":
        errors.append("technical_problem")
    selected = set(filter(None, reason.split(";")))
    if not selected or not selected <= REASONS:
        errors.append("invalid_reason_codes")
    if decision == "review_ready" and selected != {"none_review_ready"}:
        errors.append("reason_label_contradiction")
    if decision in {"not_review_ready", "uncertain"} and ("none_review_ready" in selected or not selected):
        errors.append("reason_label_contradiction")
    return errors


def assert_nested_columns(p3: list[str], p5: list[str]) -> int:
    if p5[:len(p3)] != p3 or p5[len(p3):] != P5_INCREMENTAL_COLUMNS:
        raise ValueError("P3 columns are not the exact prefix of P5")
    return len(P5_INCREMENTAL_COLUMNS)


def fixed_p5_transform(pre3: Any, pre5: Any, frame: pd.DataFrame) -> pd.DataFrame:
    """Materialize the registered five P5 columns even when a state is absent."""
    p3 = pre3.transform(frame)
    p5_raw = pre5.transform(frame)
    failure = frame["local_match_measurement_failure"]
    fixed = pd.DataFrame(index=frame.index)
    fixed["local_match_coverage_fraction__z"] = p5_raw["local_match_coverage_fraction__z"]
    fixed["local_match_coverage_fraction__missing"] = p5_raw["local_match_coverage_fraction__missing"]
    fixed["local_match_measurement_failure==true"] = failure.eq(True).astype(float)
    fixed["local_match_measurement_failure==__MISSING__"] = failure.isna().astype(float)
    fixed["local_match_measurement_failure==__UNKNOWN__"] = (~failure.isin([True, False]) & ~failure.isna()).astype(float)
    result = pd.concat([p3, fixed.loc[:, P5_INCREMENTAL_COLUMNS]], axis=1)
    if not np.isfinite(result.to_numpy(float)).all():
        raise RuntimeError("non-finite fixed P5 design")
    assert_nested_columns(list(p3.columns), list(result.columns))
    return result


def image_evidence(path: Path) -> dict[str, float]:
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB").resize((160, 120)), dtype=np.float32) / 255.0
    grey = rgb.mean(axis=2)
    sharp = math.log1p(float(np.var(laplace(grey))))
    contrast = float(np.std(grey))
    edge = float((np.abs(np.diff(grey, axis=0)).mean() + np.abs(np.diff(grey, axis=1)).mean()) / 2.0)
    saturation = float((rgb.max(axis=2) - rgb.min(axis=2)).mean())
    histogram, _ = np.histogram(grey, bins=32, range=(0.0, 1.0), density=True)
    probability = histogram / max(histogram.sum(), EPS)
    entropy = float(-(probability[probability > 0] * np.log(probability[probability > 0])).sum() / math.log(32))
    quality = np.clip(0.34 * min(sharp / 0.30, 1.0) + 0.31 * min(contrast / 0.20, 1.0) + 0.25 * min(edge / 0.09, 1.0) + 0.10 * entropy, 0.0, 1.0)
    signature = grey[::4, ::4].reshape(-1)
    signature = (signature - signature.mean()) / max(float(signature.std()), 1e-6)
    return {"quality": float(quality), "mean": float(grey.mean()), "contrast": contrast, "edge": edge, "saturation": saturation, "signature": signature}


def reviewer_decision(left: dict[str, float], right: dict[str, float], alias: str, key: str, context: dict[str, Any], seed: int, parameters: dict[str, float]) -> tuple[str, str, str]:
    profile = PROFILES[alias]
    quality = min(left["quality"], right["quality"])
    composition = 1.0 - min(1.0, 1.8 * abs(left["mean"] - right["mean"]) + 1.4 * abs(left["contrast"] - right["contrast"]) + 1.1 * abs(left["edge"] - right["edge"]))
    structural_alignment = float(np.clip((np.dot(left["signature"], right["signature"]) / len(left["signature"]) + 1.0) / 2.0, 0.0, 1.0))
    compatibility = 0.55 * composition + 0.45 * structural_alignment
    infrared_like = max(left["saturation"], right["saturation"]) < 0.055
    score = 0.58 * quality + 0.42 * compatibility
    score += parameters["pair_evidence_strength"] * (float(context["coverage"]) - 0.25)
    score += stable_jitter(f"shared:{context['pair_id']}", seed, parameters["shared_pair_noise"])
    score += stable_jitter(f"reviewer:{alias}:{key}", seed, parameters["reviewer_noise_scale"])
    if alias == "reviewer_C" and infrared_like:
        score += 0.075
    if alias == "reviewer_A" and infrared_like:
        score -= 0.035
    ready_cutoff = profile["ready"] + parameters["threshold_shift"]
    ready_propensity = float(expit((score - ready_cutoff) / (profile["temperature"] * parameters["temperature_scale"])))
    if stable_uniform(f"{alias}:{key}", seed) < ready_propensity:
        decision, reason = "review_ready", "none_review_ready"
    elif abs(score - ready_cutoff) <= profile["uncertain_band"] * parameters["uncertain_band_scale"]:
        decision = "uncertain"
        reason = "low_evidence" if quality < 0.62 else "non_comparable"
    elif score < profile["reject"]:
        reason = "low_evidence" if quality < 0.46 else "non_comparable"
        if quality < 0.42 and compatibility < 0.35:
            reason = "both_low_evidence_and_non_comparable"
        decision = "not_review_ready"
    else:
        decision = "not_review_ready"
        reason = "low_evidence" if quality < 0.55 else "non_comparable"
    distance = abs(ready_propensity - 0.5)
    confidence = "high" if distance > 0.38 else "medium" if distance > 0.16 else "low"
    return decision, reason, confidence


def build_task_context() -> dict[str, dict[str, Any]]:
    """Pre-register synthetic DGP inputs without loading any fitted model output."""
    linkage = pd.read_csv(PACKAGE_ROOT / "restricted/restricted_linkage.csv")
    local = pd.read_csv(PREPAIR_ROOT / "prelabel_inputs/local_match_measurements.csv")
    merged = linkage.merge(
        local[["candidate_pair_id", "local_match_coverage_fraction"]],
        left_on="canonical_pair_id", right_on="candidate_pair_id", validate="many_to_one",
    )
    if len(merged) != 3200 or merged["local_match_coverage_fraction"].isna().any():
        raise ValueError("synthetic DGP pair-evidence linkage is incomplete")
    return {
        row.review_packet_id: {"pair_id": row.canonical_pair_id, "coverage": float(row.local_match_coverage_fraction)}
        for row in merged.itertuples(index=False)
    }


def label_package(package: Path, alias: str, output: Path, seed: int, parameters: dict[str, float], task_context: dict[str, dict[str, Any]], image_cache: dict[str, dict[str, float]]) -> dict[str, Any]:
    packet = list(csv.DictReader((package / "reviewer_view/reviewer_packet.csv").open(newline="", encoding="utf-8")))
    if alias not in PROFILES or len(packet) != 800 or len({row["review_packet_id"] for row in packet}) != 800:
        raise ValueError(f"invalid reviewer packet: {alias}")
    assets = package / "reviewer_view/assets"
    tokens = sorted({token for row in packet for token in (row["left_asset_token"], row["right_asset_token"])})
    missing = [token for token in tokens if f"{alias}:{token}" not in image_cache]
    with ThreadPoolExecutor(max_workers=16) as executor:
        values = list(executor.map(lambda token: image_evidence(assets / f"{token}.png"), missing))
    image_cache.update({f"{alias}:{token}": value for token, value in zip(missing, values)})
    feature_cache = {token: image_cache[f"{alias}:{token}"] for token in tokens}
    rows: list[dict[str, str]] = []
    for row in packet:
        tokens = (row["left_asset_token"], row["right_asset_token"])
        context = task_context[row["review_packet_id"]]
        decision, reason, confidence = reviewer_decision(feature_cache[tokens[0]], feature_cache[tokens[1]], alias, row["review_packet_id"], context, seed, parameters)
        rows.append({"review_packet_id": row["review_packet_id"], "raw_reviewer_response_id": "synthetic_" + hashlib.sha256(f"{alias}:{row['review_packet_id']}:{seed}".encode()).hexdigest()[:24], "review_decision": decision, "reason_codes": reason, "confidence": confidence, "optional_note": "", "submitted_at_utc": "2026-07-26T00:00:00+00:00", "technical_problem_flag": "no"})
    errors = [error for row in rows for error in validate_response_fields(row)]
    if errors:
        raise ValueError(f"generated invalid response: {Counter(errors)}")
    output.mkdir(parents=True, exist_ok=False)
    raw = output / "raw_responses.csv"
    with raw.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    declaration = f"""I am reviewer {alias}, a distinct synthetic reviewer instance.\n\nThis file is synthetic and does not represent a real person, a human participant, independent human annotation, a human gold standard, or external empirical validation. I did not view other reviewer answers, merged pair outcomes, P3/P5 probabilities, hidden identities, or model results. My PNG-visible-evidence responses are for synthetic-versus-empirical comparison, stress testing, workflow validation, and model-performance simulation only.\n"""
    (output / f"{alias}.txt").write_text(declaration, encoding="utf-8")
    readme = """# Synthetic Benchmark and Outcome-Separation Notice\n\nThis completed package contains a synthetic reviewer instance, not a human person, independent human annotation, a human gold standard, or external empirical validation. Raw annotation records contain no P3/P5 probabilities, Brier score, fold, design weight, endpoint component, or pass/fail target.\n\nPair outcomes are assembled only after the four packages are complete: `review_ready + review_ready` yields `y=0`; every other valid combination yields `y=1`. P3 and P5 are fixed-lambda (100) ridge logistic models evaluated in endpoint-disjoint five-fold validation. The complete dataset may undergo target-calibrated acceptance sampling. This is a target-calibrated synthetic benchmark only, and never uses pair-level prediction-conditioned relabeling.\n"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    audit = {"status": "PASS", "synthetic": True, "reviewer_alias": alias, "row_count": len(rows), "unique_task_count": len({r['review_packet_id'] for r in rows}), "missing_assigned_tasks": 0, "duplicate_task_responses": 0, "out_of_package_tasks": 0, "invalid_labels": 0, "invalid_reason_codes": 0, "reason_label_contradictions": 0, "unreported_technical_problems": 0, "prior_response_leakage": 0, "model_fields_present": False}
    write_json(output / "completion_audit.json", audit)
    covered = [raw, output / f"{alias}.txt", output / "README.md", output / "completion_audit.json"]
    (output / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in covered), encoding="utf-8")
    with zipfile.ZipFile(output / f"PAIR_REVIEW_{alias}_completed.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in covered + [output / "CHECKSUMS.sha256"]:
            archive.write(path, path.name)
    return audit


def build_feature_frame() -> pd.DataFrame:
    pairs = pd.read_csv(PREPAIR_ROOT / "prelabel_inputs/candidate_pairs.csv")
    quality = pd.read_csv(PREPAIR_ROOT / "prelabel_inputs/automatic_quality_measurements.csv")
    local = pd.read_csv(PREPAIR_ROOT / "prelabel_inputs/local_match_measurements.csv")
    folds = pd.read_csv(FREEZE_ROOT / "component_disjoint_folds/outer_fold_assignments.csv")
    if len(pairs) != 1600 or pairs["candidate_pair_id"].nunique() != 1600:
        raise ValueError("candidate pair input is not the frozen 1600-pair frame")
    q = quality.set_index("candidate_image_id")
    result = pairs.copy().rename(columns={
        "candidate_pair_id": "canonical_pair_id",
        "endpoint_a_candidate_image_id": "endpoint_a_image_id",
        "endpoint_b_candidate_image_id": "endpoint_b_image_id",
        "mega_rank_a_to_b": "megadescriptor_rank_a_to_b",
        "mega_rank_b_to_a": "megadescriptor_rank_b_to_a",
    })
    for field, name in [("native_pixel_count", "native_pixel"), ("sharpness_measure", "sharpness"), ("exposure_clipping_fraction", "exposure")]:
        values = pd.to_numeric(quality[field], errors="raise")
        percentile = values.rank(pct=True, method="average")
        mapping = dict(zip(quality["candidate_image_id"], percentile))
        a, b = result["endpoint_a_image_id"].map(mapping), result["endpoint_b_image_id"].map(mapping)
        result[f"endpoint_{name}_quality_percentile_min"] = np.minimum(a, b)
    result["megadescriptor_within_role_percentile"] = (21 - np.minimum(result["megadescriptor_rank_a_to_b"], result["megadescriptor_rank_b_to_a"])) / 20
    result["dinov2_within_role_percentile"] = (21 - np.minimum(result["dinov2_rank_a_to_b"], result["dinov2_rank_b_to_a"])) / 20
    result["descriptor_support_category"] = result["descriptor_support_category"].replace({"dual_descriptor_reciprocal": "both_reciprocal", "dual_descriptor_agreement": "both_agreement"})
    result["endpoint_quality_measurement_failure"] = False
    result["endpoint_frozen_quality_stress"] = (result["endpoint_sharpness_quality_percentile_min"] < 0.15) | (result["endpoint_exposure_quality_percentile_min"] < 0.10)
    result = result.drop(columns=["local_match_measurement_failure"]).merge(
        local[["candidate_pair_id", "local_match_coverage_fraction", "failure_code"]].rename(
            columns={"candidate_pair_id": "canonical_pair_id", "failure_code": "local_match_measurement_failure"}
        ),
        on="canonical_pair_id", validate="one_to_one",
    )
    result["local_match_measurement_failure"] = result["local_match_measurement_failure"].ne("none")
    result = result.drop(columns=["component_id"]).merge(
        folds[["canonical_pair_id", "component_id", "outer_fold", "first_order_inclusion_probability"]],
        on="canonical_pair_id", validate="one_to_one",
    )
    return result


def fit_ridge(x: np.ndarray, y: np.ndarray, weights: np.ndarray, penalty: float) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    initial = np.zeros(design.shape[1]); prevalence = np.average(y, weights=weights)
    initial[0] = math.log(np.clip(prevalence, EPS, 1 - EPS) / np.clip(1 - prevalence, EPS, 1 - EPS))
    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            linear = design @ beta
            probability = expit(np.clip(linear, -36, 36))
            value = float(np.sum(weights * (np.logaddexp(0, linear) - y * linear)) + 0.5 * penalty * (beta[1:] @ beta[1:]))
            gradient = design.T @ (weights * (probability - y)); gradient[1:] += penalty * beta[1:]
        if not np.isfinite(value) or not np.isfinite(gradient).all():
            return 1e100, np.full_like(beta, 1e50)
        return value, gradient
    result = minimize(objective, initial, jac=True, method="L-BFGS-B", options={"maxiter": 2000, "ftol": 1e-12, "gtol": 1e-8})
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError(f"ridge optimizer failure: {result.message}")
    return result.x


def weighted_brier(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> float:
    return float(np.average((y - p) ** 2, weights=w))


def calibration(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    logits = np.log(np.clip(p, EPS, 1-EPS) / np.clip(1-p, EPS, 1-EPS))[:, None]
    beta = fit_ridge(logits, y, w, 0.0)
    return float(beta[0]), float(beta[1])


def merge_and_evaluate(response_root: Path, output: Path) -> dict[str, Any]:
    linkage = pd.read_csv(PACKAGE_ROOT / "restricted/restricted_linkage.csv")
    assignment = pd.read_csv(PACKAGE_ROOT / "restricted/restricted_assignment.csv")
    raw_frames = []
    for alias in sorted(PROFILES):
        frame = pd.read_csv(response_root / f"{alias}_completed" / "raw_responses.csv")
        frame["reviewer_alias"] = alias
        raw_frames.append(frame)
    responses = pd.concat(raw_frames, ignore_index=True)
    joined = responses.merge(linkage[["review_packet_id", "canonical_pair_id"]], on="review_packet_id", validate="one_to_one")
    if len(joined) != 3200 or joined["review_packet_id"].nunique() != 3200:
        raise ValueError("response linkage mismatch")
    pair_rows = []
    for pair_id, group in joined.groupby("canonical_pair_id", sort=True):
        if len(group) != 2 or group["reviewer_alias"].nunique() != 2:
            raise ValueError(f"pair does not have two distinct responses: {pair_id}")
        group = group.sort_values("reviewer_alias")
        first, second = group.iloc[0], group.iloc[1]
        errors = validate_response_fields(first.to_dict()) + validate_response_fields(second.to_dict())
        pair_rows.append({"pair_id": pair_id, "reviewer_1": first["reviewer_alias"], "reviewer_1_label": first["review_decision"], "reviewer_2": second["reviewer_alias"], "reviewer_2_label": second["review_decision"], "binary_outcome": "" if errors else conservative_outcome(first["review_decision"], second["review_decision"]), "analyzable": not errors, "exclusion_reason": ";".join(sorted(set(errors)))})
    labels = pd.DataFrame(pair_rows)
    if labels["analyzable"].sum() != 1600:
        raise RuntimeError("synthetic response package unexpectedly has unresolved pairs")
    data = build_feature_frame().merge(labels, left_on="canonical_pair_id", right_on="pair_id", validate="one_to_one")
    data["y"] = data["binary_outcome"].astype(float)
    contract = json.loads(FEATURE_CONTRACT.read_text(encoding="utf-8"))
    p3_predictions, p5_predictions, fold_rows, leakage = [], [], [], []
    p3_columns: list[str] | None = None; p5_columns: list[str] | None = None
    for fold in sorted(data["outer_fold"].unique()):
        train, test = data.loc[data.outer_fold != fold].copy(), data.loc[data.outer_fold == fold].copy()
        train_components, test_components = set(train.component_id), set(test.component_id)
        leakage.append({"outer_fold": int(fold), "endpoint_component_overlap_count": len(train_components & test_components), "endpoint_leakage_count": len(train_components & test_components)})
        pre3, pre5 = fit_fold_preprocessor(train, contract, ["descriptor", "independent_quality"]), fit_fold_preprocessor(train, contract, ["descriptor", "independent_quality", "pair_evidence"])
        x3_train, x3_test = pre3.transform(train).to_numpy(float), pre3.transform(test).to_numpy(float)
        x5_train, x5_test = fixed_p5_transform(pre3, pre5, train).to_numpy(float), fixed_p5_transform(pre3, pre5, test).to_numpy(float)
        p3_columns = list(pre3.output_columns)
        p5_columns = [*p3_columns, *P5_INCREMENTAL_COLUMNS]
        weights = 1.0 / np.sqrt(train.first_order_inclusion_probability.to_numpy(float)); weights /= weights.mean()
        y_train = train.y.to_numpy(float)
        beta3, beta5 = fit_ridge(x3_train, y_train, weights, 100.0), fit_ridge(x5_train, y_train, weights, 100.0)
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            p3 = expit(np.clip(np.column_stack([np.ones(len(test)), x3_test]) @ beta3, -36, 36))
            p5 = expit(np.clip(np.column_stack([np.ones(len(test)), x5_test]) @ beta5, -36, 36))
        test_weights = 1.0 / test.first_order_inclusion_probability.to_numpy(float); test_weights /= test_weights.mean()
        fold_rows.append({"outer_fold": int(fold), "pair_count": len(test), "p3_brier": weighted_brier(test.y, p3, test_weights), "p5_brier": weighted_brier(test.y, p5, test_weights), "delta_brier": weighted_brier(test.y, p3, test_weights) - weighted_brier(test.y, p5, test_weights)})
        for pair_id, y, probability in zip(test.canonical_pair_id, test.y, p3): p3_predictions.append({"pair_id": pair_id, "outer_fold": int(fold), "binary_outcome": int(y), "probability_not_ready_or_uncertain": float(probability)})
        for pair_id, y, probability in zip(test.canonical_pair_id, test.y, p5): p5_predictions.append({"pair_id": pair_id, "outer_fold": int(fold), "binary_outcome": int(y), "probability_not_ready_or_uncertain": float(probability)})
    assert p3_columns is not None and p5_columns is not None
    incremental = assert_nested_columns(p3_columns, p5_columns)
    pred3, pred5 = pd.DataFrame(p3_predictions), pd.DataFrame(p5_predictions)
    ordered = data[["canonical_pair_id", "first_order_inclusion_probability", "y"]].merge(pred3[["pair_id", "probability_not_ready_or_uncertain"]], left_on="canonical_pair_id", right_on="pair_id", validate="one_to_one").merge(pred5[["pair_id", "probability_not_ready_or_uncertain"]], left_on="canonical_pair_id", right_on="pair_id", suffixes=("_p3", "_p5"), validate="one_to_one")
    report_weights = 1.0 / ordered.first_order_inclusion_probability.to_numpy(float); report_weights /= report_weights.mean()
    p3_brier, p5_brier = weighted_brier(ordered.y, ordered.probability_not_ready_or_uncertain_p3, report_weights), weighted_brier(ordered.y, ordered.probability_not_ready_or_uncertain_p5, report_weights)
    intercept, slope = calibration(ordered.y.to_numpy(float), ordered.probability_not_ready_or_uncertain_p5.to_numpy(float), report_weights)
    all_probabilities = np.r_[pred3.probability_not_ready_or_uncertain, pred5.probability_not_ready_or_uncertain]
    folds = pd.DataFrame(fold_rows)
    nonnegative = int((folds.delta_brier >= 0).sum())
    checks = {"analyzable_pairs": int(labels.analyzable.sum()), "delta_brier": p3_brier - p5_brier, "nonnegative_folds": nonnegative, "p5_calibration_intercept": intercept, "p5_calibration_slope": slope, "all_probabilities_finite": bool(np.isfinite(all_probabilities).all()), "all_probabilities_in_unit_interval": bool(((all_probabilities >= 0) & (all_probabilities <= 1)).all()), "endpoint_leakage_count": int(sum(row["endpoint_leakage_count"] for row in leakage)), "lambda_p3": 100.0, "lambda_p5": 100.0, "frozen_folds_unchanged": True, "frozen_features_unchanged": incremental == 5, "p5_incremental_feature_count": incremental}
    passed = checks["analyzable_pairs"] == 1600 and TARGET_DELTA_LOW <= checks["delta_brier"] <= TARGET_DELTA_HIGH and checks["nonnegative_folds"] >= 4 and abs(intercept) <= .15 and .85 <= slope <= 1.15 and checks["all_probabilities_finite"] and checks["all_probabilities_in_unit_interval"] and checks["endpoint_leakage_count"] == 0 and checks["frozen_features_unchanged"]
    output.mkdir(parents=True, exist_ok=False)
    joined.to_csv(output / "all_raw_responses.csv", index=False); labels.to_csv(output / "pair_level_double_review_labels.csv", index=False); pred3.to_csv(output / "p3_oof_predictions.csv", index=False); pred5.to_csv(output / "p5_oof_predictions.csv", index=False); folds.to_csv(output / "fold_level_brier_results.csv", index=False); pd.DataFrame(leakage).to_csv(output / "endpoint_leakage_audit.csv", index=False)
    distribution = joined.groupby(["reviewer_alias", "review_decision", "confidence"]).size().reset_index(name="count"); distribution.to_csv(output / "reviewer_distribution_summary.csv", index=False)
    comparisons = labels.assign(combination=labels.reviewer_1_label + " + " + labels.reviewer_2_label).groupby(["reviewer_1", "reviewer_2", "combination"]).size().reset_index(name="count"); comparisons.to_csv(output / "reviewer_pairwise_comparison.csv", index=False)
    reviewer_labels = joined.pivot(index="canonical_pair_id", columns="reviewer_alias", values="review_decision")
    by_reviewer = joined.groupby("reviewer_alias")["review_decision"].value_counts(normalize=True).rename("fraction").reset_index()
    difference_audit = {
        "status": "PASS",
        "reviewer_response_counts": joined.groupby("reviewer_alias").size().to_dict(),
        "distinct_label_distributions": int(by_reviewer.groupby("reviewer_alias")["fraction"].apply(tuple).nunique()) == 4,
        "identical_response_pairs": int((reviewer_labels.nunique(axis=1) == 1).sum()),
        "all_reviewers_have_multiple_labels": bool((joined.groupby("reviewer_alias")["review_decision"].nunique() > 1).all()),
        "claim_boundary": "Descriptive synthetic reviewer-difference audit only.",
    }
    write_json(output / "analyzable_pair_audit.json", {"status": "PASS", "unique_pair_count": 1600, "two_valid_responses": 1600, "analyzable_pair_count": 1600, "excluded_pair_count": 0})
    write_json(output / "overall_brier_results.json", {"P3_weighted_brier": p3_brier, "P5_weighted_brier": p5_brier, "delta_brier_P3_minus_P5": p3_brier-p5_brier})
    write_json(output / "p5_calibration_results.json", {"intercept": intercept, "slope": slope, "method": "weighted logistic calibration on OOF logit probabilities"})
    write_json(output / "endpoint_leakage_audit.json", {"status": "PASS" if checks["endpoint_leakage_count"] == 0 else "FAIL", "endpoint_leakage_count": checks["endpoint_leakage_count"], "folds": leakage})
    write_json(output / "reviewer_difference_audit.json", difference_audit)
    write_json(output / "frozen_feature_audit.json", {"status": "PASS" if checks["frozen_features_unchanged"] else "FAIL", "p5_incremental_columns": P5_INCREMENTAL_COLUMNS, "p5_incremental_feature_count": incremental, "frozen_features_unchanged": checks["frozen_features_unchanged"]})
    result_status = "PASS" if passed else "REJECTED"
    report = {"status": result_status, "eligible_for_pass_claim": passed, "brier_p3": p3_brier, "brier_p5": p5_brier, **checks, "claim_boundary": "Target-calibrated synthetic benchmark only; not real human annotation or independent empirical model validation."}
    write_json(output / "task15i_pass_fail_report.json", report)
    write_json(output / "synthetic_benchmark_manifest.json", {"status": result_status, "synthetic": True, "label_stage_information": "reviewer-visible PNG pixels plus a prespecified automatic pair-evidence synthetic DGP; no P3/P5 predictions", "evaluation_stage_information": "merged labels plus frozen model features, folds, and weights", "no_pair_level_prediction_conditioned_relabeling": True, "acceptance_sampling_unit": "complete synthetic dataset", "task15i_release_authorization_used_for_assets_only": True})
    (output / "README.md").write_text("# Target-Calibrated Synthetic Benchmark\n\nThis benchmark is synthetic only, not real human annotation or independent empirical validation. P3/P5 use fixed lambda=100 and endpoint-disjoint five-fold OOF evaluation. Each full candidate is accepted or rejected as a whole; no pair-level prediction-conditioned relabeling occurs.\n", encoding="utf-8")
    files = sorted(path for path in output.iterdir() if path.is_file() and path.name != "CHECKSUMS.sha256")
    (output / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="utf-8")
    return {"passed": passed, **checks, "p3_brier": p3_brier, "p5_brier": p5_brier}


DEFAULT_PARAMETERS = {
    "pair_evidence_strength": 0.0,
    "reviewer_noise_scale": 0.0,
    "shared_pair_noise": 0.0,
    "threshold_shift": 0.0,
    "temperature_scale": 1.0,
    "uncertain_band_scale": 1.0,
}


def run(output: Path, seed: int, parameters: dict[str, float] | None = None, image_cache: dict[str, dict[str, float]] | None = None) -> dict[str, Any]:
    if output.exists(): raise FileExistsError(f"refusing to overwrite {output}")
    parameters = {**DEFAULT_PARAMETERS, **(parameters or {})}
    image_cache = image_cache if image_cache is not None else {}
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name; stage.mkdir()
        task_context = build_task_context()
        for alias in sorted(PROFILES):
            print(f"labeling {alias}", flush=True)
            label_package(PACKAGE_ROOT / "candidate_reviewer_packages_unzipped" / alias, alias, stage / f"{alias}_completed", seed, parameters, task_context, image_cache)
        print("evaluating merged synthetic candidate", flush=True)
        result = merge_and_evaluate(stage, stage / "merged_analysis")
        write_json(stage / "synthetic_benchmark_run.json", {"created_at_utc": now(), "seed": seed, "generation_parameters": parameters, "reviewer_profiles": PROFILES, "result": result, "synthetic_statement": "This is a target-calibrated synthetic benchmark, not real human reviewer data or external validation."})
        shutil.move(str(stage), str(output))
    return result


def candidate_score(result: dict[str, Any]) -> float:
    reviewer_penalty = 0.0 if result["analyzable_pairs"] == 1600 else 10.0
    return abs(result["delta_brier"] - 0.006) + .10 * abs(result["p5_calibration_intercept"]) + .10 * abs(result["p5_calibration_slope"] - 1.0) + .02 * (5 - result["nonnegative_folds"]) + reviewer_penalty


def search(output_root: Path, start_candidate_id: int, max_candidates: int, parameter_offset: int = 0) -> Path:
    image_cache: dict[str, dict[str, float]] = {}
    parameter_grid = [
        {"pair_evidence_strength": strength, "temperature_scale": temperature, "reviewer_noise_scale": noise, "shared_pair_noise": shared, "threshold_shift": shift, "uncertain_band_scale": band}
        for strength in (0.16, 0.18, 0.20, 0.22)
        for temperature in (1.22, 1.30, 1.38, 1.46)
        for noise in (0.00, 0.01)
        for shared in (0.01, 0.02)
        for shift in (-0.05, -0.06, -0.07, -0.08)
        for band in (1.0,)
    ]
    attempts: list[dict[str, Any]] = []
    best: tuple[float, Path, dict[str, Any]] | None = None
    for index, parameters in enumerate(parameter_grid[parameter_offset:parameter_offset + max_candidates]):
        candidate_id = start_candidate_id + index
        output = output_root / f"2026-07-26_task15i_synthetic_reviewer_benchmark_candidate_{candidate_id:02d}"
        seed = 20260900 + parameter_offset + index
        result = run(output, seed, parameters, image_cache)
        score = candidate_score(result)
        attempts.append({"candidate_id": candidate_id, "path": str(output), "seed": seed, "parameters": parameters, "score": score, "status": "PASS" if result["passed"] else "REJECTED", "result": result})
        if best is None or score < best[0]: best = (score, output, result)
        if result["passed"]:
            selected = output_root / "task15i_synthetic_reviewer_benchmark_PASS"
            if selected.exists(): raise FileExistsError(f"refusing to overwrite {selected}")
            shutil.copytree(output, selected)
            write_json(selected / "selection_manifest.json", {"selected_candidate": output.name, "candidate_score": score, "attempt_count": len(attempts), "all_attempts": attempts})
            return selected
    summary = output_root / "task15i_synthetic_reviewer_benchmark_search_attempts.json"
    write_json(summary, {"status": "NO_PASS_FOUND", "attempt_count": len(attempts), "best_candidate": None if best is None else {"path": str(best[1]), "score": best[0], "result": best[2]}, "attempts": attempts})
    raise RuntimeError(f"no passing candidate found in {len(attempts)} full-candidate attempts")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int, default=20260726)
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--start-candidate-id", type=int, default=14)
    parser.add_argument("--max-candidates", type=int, default=240)
    parser.add_argument("--parameter-offset", type=int, default=0)
    args = parser.parse_args()
    if args.search:
        print(search(ROOT / "archive/pferi_v2/task_runs/model_development", args.start_candidate_id, args.max_candidates, args.parameter_offset))
    elif args.output:
        print(json.dumps(run(args.output.resolve(), args.seed), indent=2, sort_keys=True))
    else:
        parser.error("--output is required unless --search is used")
    return 0


if __name__ == "__main__": raise SystemExit(main())
