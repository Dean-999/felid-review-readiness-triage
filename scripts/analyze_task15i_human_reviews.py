#!/usr/bin/env python3
"""Assemble study-owner-declared manual Task15I reviews and run frozen P3/P5 evaluation.

The AI-assisted tool supported reviewer workflow only.  It did not generate or
replace any photo-level review decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

try:
    from scripts.pferi_v2_fold_preprocessor import fit_fold_preprocessor
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pferi_v2_fold_preprocessor import fit_fold_preprocessor


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
RESPONSE_ROOT = MODEL_ROOT / "review"
PACKAGE_ROOT = MODEL_ROOT / "2026-07-26_task15i_candidate_reviewer_packages_v1"
PREPAIR_ROOT = MODEL_ROOT / "2026-07-26_task15i_prepair_artifacts_v1"
FREEZE_ROOT = MODEL_ROOT / "2026-07-26_task15i_90pct_prepair_contract_freeze_v1"
FEATURE_CONTRACT = ROOT / "schemas/pferi_v2/feature_preprocessing_contract_v1.json"
DEFAULT_OUTPUT = MODEL_ROOT / "2026-07-27_task15i_human_review_outcome_analysis/iterations/v3"
RAW_COLUMNS = [
    "review_packet_id", "raw_reviewer_response_id", "review_decision", "reason_codes",
    "confidence", "optional_note", "submitted_at_utc", "technical_problem_flag",
]
DECISIONS = {"review_ready", "not_review_ready", "uncertain"}
EPS = 1e-12
P5_INCREMENTAL_COLUMNS = [
    "local_match_coverage_fraction__z",
    "local_match_coverage_fraction__missing",
    "local_match_measurement_failure==true",
    "local_match_measurement_failure==__MISSING__",
    "local_match_measurement_failure==__UNKNOWN__",
]
HUMAN_REVIEW_PROVENANCE = (
    "STUDY_OWNER_DECLARED_MANUAL_PHOTO_REVIEW; "
    "AI_ASSISTED_CLASSIFICATION_TOOL_ONLY; "
    "AI_DID_NOT_GENERATE_PHOTO_LEVEL_LABELS"
)
REVIEWER_ELIGIBILITY_POLICY = (
    "Eligibility uses only frozen-assignment coverage, response-schema validity, "
    "unique response provenance, and absence of technical-problem flags. "
    "Reason, individual confidence, response time, and reviewer agreement are descriptive only."
)


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


def conservative_outcome(first: str, second: str) -> int:
    if first not in DECISIONS or second not in DECISIONS:
        raise ValueError("invalid first-pass decision")
    return 0 if first == second == "review_ready" else 1


def assert_nested_columns(p3: list[str], p5: list[str]) -> int:
    if p5[:len(p3)] != p3 or p5[len(p3):] != P5_INCREMENTAL_COLUMNS:
        raise ValueError("P3 columns are not the exact prefix of P5")
    return len(P5_INCREMENTAL_COLUMNS)


def fixed_p5_transform(pre3: Any, pre5: Any, frame: pd.DataFrame) -> pd.DataFrame:
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
        raise RuntimeError("non-finite P5 design")
    assert_nested_columns(list(p3.columns), list(result.columns))
    return result


def build_feature_frame() -> pd.DataFrame:
    pairs = pd.read_csv(PREPAIR_ROOT / "prelabel_inputs/candidate_pairs.csv")
    quality = pd.read_csv(PREPAIR_ROOT / "prelabel_inputs/automatic_quality_measurements.csv")
    local = pd.read_csv(PREPAIR_ROOT / "prelabel_inputs/local_match_measurements.csv")
    folds = pd.read_csv(FREEZE_ROOT / "component_disjoint_folds/outer_fold_assignments.csv")
    if len(pairs) != 1600 or pairs["candidate_pair_id"].nunique() != 1600:
        raise ValueError("frozen 1600-pair frame is unavailable")
    result = pairs.copy().rename(columns={
        "candidate_pair_id": "canonical_pair_id",
        "endpoint_a_candidate_image_id": "endpoint_a_image_id",
        "endpoint_b_candidate_image_id": "endpoint_b_image_id",
        "mega_rank_a_to_b": "megadescriptor_rank_a_to_b",
        "mega_rank_b_to_a": "megadescriptor_rank_b_to_a",
    })
    for field, name in [
        ("native_pixel_count", "native_pixel"),
        ("sharpness_measure", "sharpness"),
        ("exposure_clipping_fraction", "exposure"),
    ]:
        values = pd.to_numeric(quality[field], errors="raise")
        mapping = dict(zip(quality["candidate_image_id"], values.rank(pct=True, method="average")))
        result[f"endpoint_{name}_quality_percentile_min"] = np.minimum(
            result["endpoint_a_image_id"].map(mapping), result["endpoint_b_image_id"].map(mapping)
        )
    result["megadescriptor_within_role_percentile"] = (21 - np.minimum(result["megadescriptor_rank_a_to_b"], result["megadescriptor_rank_b_to_a"])) / 20
    result["dinov2_within_role_percentile"] = (21 - np.minimum(result["dinov2_rank_a_to_b"], result["dinov2_rank_b_to_a"])) / 20
    result["descriptor_support_category"] = result["descriptor_support_category"].replace({"dual_descriptor_reciprocal": "both_reciprocal", "dual_descriptor_agreement": "both_agreement"})
    result["endpoint_quality_measurement_failure"] = False
    result["endpoint_frozen_quality_stress"] = (result["endpoint_sharpness_quality_percentile_min"] < 0.15) | (result["endpoint_exposure_quality_percentile_min"] < 0.10)
    result = result.drop(columns=["local_match_measurement_failure"]).merge(
        local[["candidate_pair_id", "local_match_coverage_fraction", "failure_code"]].rename(columns={"candidate_pair_id": "canonical_pair_id", "failure_code": "local_match_measurement_failure"}),
        on="canonical_pair_id", validate="one_to_one",
    )
    result["local_match_measurement_failure"] = result["local_match_measurement_failure"].ne("none")
    return result.drop(columns=["component_id"]).merge(
        folds[["canonical_pair_id", "component_id", "outer_fold", "first_order_inclusion_probability"]],
        on="canonical_pair_id", validate="one_to_one",
    )


def fit_ridge(x: np.ndarray, y: np.ndarray, weights: np.ndarray, penalty: float) -> np.ndarray:
    design = np.column_stack([np.ones(len(x)), x])
    prevalence = np.average(y, weights=weights)
    initial = np.zeros(design.shape[1])
    initial[0] = math.log(np.clip(prevalence, EPS, 1 - EPS) / np.clip(1 - prevalence, EPS, 1 - EPS))

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            linear = design @ beta
            probability = expit(np.clip(linear, -36, 36))
            value = float(np.sum(weights * (np.logaddexp(0, linear) - y * linear)) + 0.5 * penalty * (beta[1:] @ beta[1:]))
            gradient = design.T @ (weights * (probability - y))
            gradient[1:] += penalty * beta[1:]
        if not np.isfinite(value) or not np.isfinite(gradient).all():
            return 1e100, np.full_like(beta, 1e50)
        return value, gradient

    result = minimize(objective, initial, jac=True, method="L-BFGS-B", options={"maxiter": 2000, "ftol": 1e-12, "gtol": 1e-8})
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError(f"ridge optimizer failure: {result.message}")
    return result.x


def weighted_brier(y: np.ndarray, p: np.ndarray, weights: np.ndarray) -> float:
    return float(np.average((y - p) ** 2, weights=weights))


def calibration(y: np.ndarray, p: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    logits = np.log(np.clip(p, EPS, 1 - EPS) / np.clip(1 - p, EPS, 1 - EPS))[:, None]
    beta = fit_ridge(logits, y, weights, 0.0)
    return float(beta[0]), float(beta[1])


def load_responses(response_root: Path) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    frames: list[pd.DataFrame] = []
    hashes: dict[str, str] = {}
    timestamp_values: list[str] = []
    for alias in ["reviewer_A", "reviewer_B", "reviewer_C", "reviewer_D"]:
        path = response_root / f"{alias}_completed/raw_responses.csv"
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        if list(frame.columns) != RAW_COLUMNS:
            raise ValueError(f"unexpected response schema: {alias}")
        if len(frame) != 800 or frame["review_packet_id"].duplicated().any() or frame["raw_reviewer_response_id"].duplicated().any():
            raise ValueError(f"invalid response cardinality: {alias}")
        if not set(frame["review_decision"]).issubset(DECISIONS) or set(frame["technical_problem_flag"]) != {"no"}:
            raise ValueError(f"invalid primary response fields: {alias}")
        frame["reviewer_alias"] = alias
        frames.append(frame)
        hashes[str(path)] = sha256(path)
        timestamp_values.extend(frame["submitted_at_utc"].tolist())
    responses = pd.concat(frames, ignore_index=True)
    if responses["review_packet_id"].duplicated().any() or responses["raw_reviewer_response_id"].duplicated().any():
        raise ValueError("response identifiers duplicate across reviewers")
    return responses, hashes, timestamp_values


def qualify(checks: dict[str, Any]) -> bool:
    return (
        checks["analyzable_pair_count"] >= 1200
        and checks["delta_brier_P3_minus_P5"] >= 0.005
        and checks["nonnegative_outer_fold_count"] >= 4
        and abs(checks["p5_calibration_intercept"]) <= 0.20
        and 0.80 <= checks["p5_calibration_slope"] <= 1.20
        and checks["all_probabilities_finite"]
        and checks["all_probabilities_in_unit_interval"]
        and checks["endpoint_leakage_count"] == 0
        and checks["fixed_lambda"] == 100.0
        and checks["p5_incremental_feature_count"] == 5
    )


def analyze(response_root: Path = RESPONSE_ROOT, output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    responses, response_hashes, timestamp_values = load_responses(response_root)
    assignment = pd.read_csv(PACKAGE_ROOT / "restricted/restricted_assignment.csv", dtype=str)
    merged = assignment.merge(responses, on="review_packet_id", how="left", validate="one_to_one")
    expected_alias = merged["reviewer_code"].map({"rv_d4b2afcdbe": "reviewer_A", "rv_a8c265993b": "reviewer_B", "rv_4f12e09812": "reviewer_C", "rv_46f2889126": "reviewer_D"})
    if len(merged) != 3200 or merged["review_decision"].isna().any() or expected_alias.isna().any() or not expected_alias.eq(merged["reviewer_alias"]).all():
        raise ValueError("responses do not exactly match frozen reviewer assignment")

    label_rows = []
    for pair_id, group in merged.groupby("canonical_pair_id", sort=True):
        if len(group) != 2 or group["reviewer_code"].nunique() != 2:
            raise ValueError(f"invalid pair response coverage: {pair_id}")
        group = group.sort_values("reviewer_alias")
        first, second = group.iloc[0], group.iloc[1]
        label_rows.append({
            "canonical_pair_id": pair_id,
            "reviewer_alias_1": first["reviewer_alias"], "decision_1": first["review_decision"],
            "reviewer_alias_2": second["reviewer_alias"], "decision_2": second["review_decision"],
            "exact_agreement": "yes" if first["review_decision"] == second["review_decision"] else "no",
            "not_ready_or_uncertain_label": conservative_outcome(first["review_decision"], second["review_decision"]),
        })
    labels = pd.DataFrame(label_rows)
    data = build_feature_frame().merge(labels, on="canonical_pair_id", validate="one_to_one")
    data["y"] = data["not_ready_or_uncertain_label"].astype(float)
    contract = json.loads(FEATURE_CONTRACT.read_text(encoding="utf-8"))
    p3_predictions: list[dict[str, Any]] = []
    p5_predictions: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    leakage_rows: list[dict[str, Any]] = []
    p3_columns: list[str] | None = None
    p5_columns: list[str] | None = None
    for fold in sorted(data["outer_fold"].unique()):
        train, test = data.loc[data.outer_fold != fold].copy(), data.loc[data.outer_fold == fold].copy()
        overlap = len(set(train.component_id) & set(test.component_id))
        leakage_rows.append({"outer_fold": int(fold), "endpoint_leakage_count": overlap})
        pre3 = fit_fold_preprocessor(train, contract, ["descriptor", "independent_quality"])
        pre5 = fit_fold_preprocessor(train, contract, ["descriptor", "independent_quality", "pair_evidence"])
        x3_train, x3_test = pre3.transform(train).to_numpy(float), pre3.transform(test).to_numpy(float)
        x5_train, x5_test = fixed_p5_transform(pre3, pre5, train).to_numpy(float), fixed_p5_transform(pre3, pre5, test).to_numpy(float)
        p3_columns, p5_columns = list(pre3.output_columns), [*pre3.output_columns, *P5_INCREMENTAL_COLUMNS]
        train_weights = 1.0 / np.sqrt(train.first_order_inclusion_probability.to_numpy(float))
        train_weights /= train_weights.mean()
        beta3 = fit_ridge(x3_train, train.y.to_numpy(float), train_weights, 100.0)
        beta5 = fit_ridge(x5_train, train.y.to_numpy(float), train_weights, 100.0)
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            p3 = expit(np.clip(np.column_stack([np.ones(len(test)), x3_test]) @ beta3, -36, 36))
            p5 = expit(np.clip(np.column_stack([np.ones(len(test)), x5_test]) @ beta5, -36, 36))
        test_weights = 1.0 / test.first_order_inclusion_probability.to_numpy(float)
        test_weights /= test_weights.mean()
        p3_brier, p5_brier = weighted_brier(test.y, p3, test_weights), weighted_brier(test.y, p5, test_weights)
        fold_rows.append({"outer_fold": int(fold), "pair_count": len(test), "p3_weighted_brier": p3_brier, "p5_weighted_brier": p5_brier, "delta_brier_P3_minus_P5": p3_brier - p5_brier})
        p3_predictions.extend({"canonical_pair_id": pair_id, "outer_fold": int(fold), "not_ready_or_uncertain_label": int(y), "probability_not_ready_or_uncertain": float(p)} for pair_id, y, p in zip(test.canonical_pair_id, test.y, p3))
        p5_predictions.extend({"canonical_pair_id": pair_id, "outer_fold": int(fold), "not_ready_or_uncertain_label": int(y), "probability_not_ready_or_uncertain": float(p)} for pair_id, y, p in zip(test.canonical_pair_id, test.y, p5))
    if p3_columns is None or p5_columns is None:
        raise RuntimeError("no folds evaluated")
    incremental = assert_nested_columns(p3_columns, p5_columns)
    p3_frame, p5_frame, folds = pd.DataFrame(p3_predictions), pd.DataFrame(p5_predictions), pd.DataFrame(fold_rows)
    ordered = data[["canonical_pair_id", "first_order_inclusion_probability", "y"]].merge(p3_frame[["canonical_pair_id", "probability_not_ready_or_uncertain"]], on="canonical_pair_id", validate="one_to_one").merge(p5_frame[["canonical_pair_id", "probability_not_ready_or_uncertain"]], on="canonical_pair_id", suffixes=("_p3", "_p5"), validate="one_to_one")
    report_weights = 1.0 / ordered.first_order_inclusion_probability.to_numpy(float)
    report_weights /= report_weights.mean()
    p3_brier = weighted_brier(ordered.y, ordered.probability_not_ready_or_uncertain_p3, report_weights)
    p5_brier = weighted_brier(ordered.y, ordered.probability_not_ready_or_uncertain_p5, report_weights)
    intercept, slope = calibration(ordered.y.to_numpy(float), ordered.probability_not_ready_or_uncertain_p5.to_numpy(float), report_weights)
    all_probabilities = np.r_[p3_frame.probability_not_ready_or_uncertain, p5_frame.probability_not_ready_or_uncertain]
    checks = {
        "analyzable_pair_count": len(labels),
        "component_count": int(data.component_id.nunique()),
        "delta_brier_P3_minus_P5": p3_brier - p5_brier,
        "nonnegative_outer_fold_count": int((folds.delta_brier_P3_minus_P5 >= 0).sum()),
        "p5_calibration_intercept": intercept,
        "p5_calibration_slope": slope,
        "all_probabilities_finite": bool(np.isfinite(all_probabilities).all()),
        "all_probabilities_in_unit_interval": bool(((all_probabilities >= 0) & (all_probabilities <= 1)).all()),
        "endpoint_leakage_count": int(sum(row["endpoint_leakage_count"] for row in leakage_rows)),
        "fixed_lambda": 100.0,
        "p5_incremental_feature_count": incremental,
    }
    passed = qualify(checks)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        merged.to_csv(stage / "accepted_raw_responses.csv", index=False)
        labels.to_csv(stage / "pair_level_outcome_labels.csv", index=False)
        p3_frame.to_csv(stage / "p3_oof_predictions.csv", index=False)
        p5_frame.to_csv(stage / "p5_oof_predictions.csv", index=False)
        folds.to_csv(stage / "fold_level_brier_results.csv", index=False)
        pd.DataFrame(leakage_rows).to_csv(stage / "endpoint_leakage_audit.csv", index=False)
        pd.crosstab(merged.reviewer_alias, merged.review_decision).to_csv(stage / "reviewer_decision_summary.csv")
        report = {
            "status": "PASS_TASK15I_DEVELOPMENT_SCREEN" if passed else "FAIL_TASK15I_DEVELOPMENT_SCREEN",
            "created_at_utc": now(),
            "human_review_provenance": HUMAN_REVIEW_PROVENANCE,
            "time_fields_used": False,
            "uniform_timestamp_value_count": len(set(timestamp_values)),
            "raw_response_sha256": response_hashes,
            "package_metadata_checksum_limitation": "Returned raw CSV and reviewer declaration checksums matched; returned README and completion-audit checksums differed from their package manifests.",
            "reviewer_metric_policy": REVIEWER_ELIGIBILITY_POLICY,
            "label_rule": "review_ready only when both first-pass decisions are review_ready; otherwise not_ready_or_uncertain",
            "p3_weighted_brier": p3_brier,
            "p5_weighted_brier": p5_brier,
            **checks,
            "claim_boundary": "This is a declared-human Task15I development-screen analysis. It is not identity accuracy, pair correctness, calibration-stage approval, confirmation, or project completion.",
        }
        write_json(stage / "task15i_development_screen_report.json", report)
        files = sorted(path for path in stage.iterdir() if path.is_file())
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="utf-8")
        shutil.move(str(stage), str(output))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, default=RESPONSE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(analyze(args.responses, args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
