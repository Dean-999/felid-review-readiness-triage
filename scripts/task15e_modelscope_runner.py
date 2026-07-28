#!/usr/bin/env python3
"""PF-ERI v2 Task 15E deterministic nested CPU model runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import sys
import time
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.interpolate import BSpline
from scipy.optimize import minimize

try:
    from pferi_v2_fold_preprocessor import fit_fold_preprocessor, load_contract
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pferi_v2_fold_preprocessor import fit_fold_preprocessor, load_contract


MODEL_ORDER = ["P0", "P1", "P2", "P3", "P4", "P5", "S1", "S2"]
EPS = 1e-12


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


def safe_float(value: Any) -> Any:
    return None if value is None or not np.isfinite(float(value)) else float(value)


def training_weights(pi: np.ndarray) -> np.ndarray:
    raw = 1.0 / np.sqrt(np.asarray(pi, dtype=float))
    if np.any(~np.isfinite(raw)) or np.any(raw <= 0):
        raise ValueError("invalid inclusion probabilities for training weights")
    return raw / raw.mean()


def evaluation_weights(pi: np.ndarray) -> np.ndarray:
    raw = 1.0 / np.asarray(pi, dtype=float)
    if np.any(~np.isfinite(raw)) or np.any(raw <= 0):
        raise ValueError("invalid inclusion probabilities for evaluation weights")
    return raw / raw.mean()


def _objective_gradient(beta: np.ndarray, x1: np.ndarray, y: np.ndarray, w: np.ndarray, lam: float) -> tuple[float, np.ndarray]:
    if not np.isfinite(beta).all() or np.max(np.abs(beta)) > 1e100:
        direction = np.sign(np.nan_to_num(beta, nan=1.0, posinf=1.0, neginf=-1.0))
        direction[direction == 0] = 1.0
        return 1e100, direction * 1e50
    with warnings.catch_warnings(), np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        eta = x1 @ beta
    if not np.isfinite(eta).all():
        # Reject only non-finite line-search proposals; this does not alter the
        # finite penalized-likelihood objective or its solution.
        direction = np.sign(beta)
        direction[direction == 0] = 1.0
        return 1e100, direction * 1e50
    loss = np.sum(w * (np.logaddexp(0.0, eta) - y * eta)) / np.sum(w)
    penalty = 0.5 * lam * float(beta[1:] @ beta[1:])
    p = 1.0 / (1.0 + np.exp(-np.clip(eta, -36.0, 36.0)))
    with warnings.catch_warnings(), np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        grad = x1.T @ (w * (p - y)) / np.sum(w)
    grad[1:] += lam * beta[1:]
    return float(loss + penalty), grad


def fit_penalized_logistic(x: np.ndarray, y: np.ndarray, weights: np.ndarray, lam: float) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if x.ndim != 2 or len(x) != len(y) or len(y) != len(weights):
        raise ValueError("invalid logistic design shapes")
    if set(np.unique(y)) != {0.0, 1.0}:
        raise RuntimeError("one_class_training_fold")
    x1 = np.column_stack([np.ones(len(x)), x])
    initial = np.zeros(x1.shape[1], dtype=float)
    prevalence = np.average(y, weights=weights)
    initial[0] = math.log(np.clip(prevalence, EPS, 1 - EPS) / np.clip(1 - prevalence, EPS, 1 - EPS))
    result = minimize(
        lambda b: _objective_gradient(b, x1, y, weights, lam),
        initial,
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": 2000, "gtol": 1e-8, "ftol": 1e-12, "maxls": 50},
    )
    objective, gradient = _objective_gradient(result.x, x1, y, weights, lam)
    success = bool(result.success and np.isfinite(result.x).all() and np.max(np.abs(result.x)) < 1e6 and np.isfinite(objective))
    if not success:
        raise RuntimeError(f"optimizer_failure:{result.status}:{result.message}")
    return {
        "coef": result.x,
        "success": success,
        "status": int(result.status),
        "message": str(result.message),
        "iterations": int(result.nit),
        "objective": float(objective),
        "gradient_norm": float(np.linalg.norm(gradient)),
    }


def predict_probability(x: np.ndarray, coef: np.ndarray) -> np.ndarray:
    with warnings.catch_warnings(), np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        eta = np.column_stack([np.ones(len(x)), np.asarray(x, dtype=float)]) @ np.asarray(coef, dtype=float)
    if not np.isfinite(eta).all():
        raise RuntimeError("non_finite_prediction_linear_predictor")
    return np.clip(1.0 / (1.0 + np.exp(-np.clip(eta, -36.0, 36.0))), EPS, 1 - EPS)


def select_lambda_one_se(summary: pd.DataFrame) -> float:
    required = {"lambda", "mean_brier", "se_brier"}
    if not required.issubset(summary.columns):
        raise ValueError("lambda summary lacks required columns")
    best = summary.loc[summary["mean_brier"].idxmin()]
    threshold = float(best["mean_brier"] + best["se_brier"])
    eligible = summary.loc[summary["mean_brier"] <= threshold, "lambda"]
    if eligible.empty:
        raise RuntimeError("one-SE rule has no eligible lambda")
    return float(eligible.max())


def _basis_matrix(values: np.ndarray, spec: dict[str, Any]) -> np.ndarray:
    if spec["constant"]:
        return np.zeros((len(values), 4), dtype=float)
    lower, knot, upper = spec["lower"], spec["knot"], spec["upper"]
    knots = np.array([lower, lower, lower, knot, upper, upper, upper], dtype=float)
    clipped = np.clip(values, lower, upper)
    matrix = BSpline.design_matrix(clipped, knots, 2, extrapolate=False).toarray()
    return (matrix - np.asarray(spec["basis_mean"])) / np.asarray(spec["basis_scale"])


def fit_gam_design(base: pd.DataFrame, continuous_columns: Iterable[str]) -> dict[str, Any]:
    continuous = list(continuous_columns)
    specs: list[dict[str, Any]] = []
    for column in continuous:
        zname = f"{column}__z"
        values = base[zname].to_numpy(dtype=float)
        lower, upper = float(values.min()), float(values.max())
        constant = bool(upper - lower < 1e-12)
        spec: dict[str, Any] = {"column": column, "lower": lower, "upper": upper, "knot": float(np.median(values)), "constant": constant}
        if constant:
            raw = np.zeros((len(values), 4), dtype=float)
        else:
            knots = np.array([lower] * 3 + [spec["knot"]] + [upper] * 3, dtype=float)
            raw = BSpline.design_matrix(np.clip(values, lower, upper), knots, 2, extrapolate=False).toarray()
        mean = raw.mean(axis=0)
        scale = raw.std(axis=0, ddof=0)
        scale[~np.isfinite(scale) | (scale < 1e-12)] = 1.0
        spec["basis_mean"] = mean.tolist()
        spec["basis_scale"] = scale.tolist()
        specs.append(spec)
    return {"continuous": specs, "base_columns": list(base.columns)}


def transform_gam_design(base: pd.DataFrame, spec: dict[str, Any]) -> pd.DataFrame:
    by_z = {f"{row['column']}__z": row for row in spec["continuous"]}
    parts: dict[str, np.ndarray] = {}
    for column in base.columns:
        if column in by_z:
            row = by_z[column]
            basis = _basis_matrix(base[column].to_numpy(dtype=float), row)
            for index in range(4):
                parts[f"{row['column']}__spline_{index}"] = basis[:, index]
        else:
            parts[column] = base[column].to_numpy(dtype=float)
    result = pd.DataFrame(parts, index=base.index)
    if not np.isfinite(result.to_numpy(dtype=float)).all():
        raise RuntimeError("non-finite GAM design")
    return result


def _design(train: pd.DataFrame, validation: pd.DataFrame, blocks: list[str], preprocessing_contract: dict[str, Any], family: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    pre = fit_fold_preprocessor(train, preprocessing_contract, blocks)
    x_train, x_validation = pre.transform(train), pre.transform(validation)
    metadata: dict[str, Any] = {"preprocessor_sha256": pre.sha256, "base_columns": list(x_train.columns)}
    if family == "restricted_penalized_logistic_gam":
        continuous = [row["column"] for row in pre.continuous]
        gam = fit_gam_design(x_train, continuous)
        x_train, x_validation = transform_gam_design(x_train, gam), transform_gam_design(x_validation, gam)
        metadata["gam_spec"] = gam
    metadata["design_columns"] = list(x_train.columns)
    return x_train, x_validation, metadata


def weighted_brier(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> float:
    return float(np.average((y - p) ** 2, weights=w))


def weighted_logloss(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> float:
    p = np.clip(p, EPS, 1 - EPS)
    return float(np.average(-(y * np.log(p) + (1 - y) * np.log(1 - p)), weights=w))


def weighted_auc(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> float | None:
    pos, neg = y == 1, y == 0
    if not pos.any() or not neg.any():
        return None
    pp, pn = p[pos][:, None], p[neg][None, :]
    pairs = (pp > pn).astype(float) + 0.5 * (pp == pn)
    weights = w[pos][:, None] * w[neg][None, :]
    return float(np.sum(pairs * weights) / np.sum(weights))


def weighted_auprc(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> float | None:
    if not np.any(y == 1):
        return None
    order = np.argsort(-p, kind="mergesort")
    ys, ws = y[order], w[order]
    tp, fp = np.cumsum(ws * ys), np.cumsum(ws * (1 - ys))
    recall = tp / tp[-1]
    precision = tp / (tp + fp)
    increments = np.diff(np.r_[0.0, recall])
    return float(np.sum(increments * precision))


def calibration_metrics(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> tuple[float | None, float | None]:
    if len(np.unique(y)) < 2:
        return None, None
    logit = np.log(np.clip(p, EPS, 1 - EPS) / np.clip(1 - p, EPS, 1 - EPS))[:, None]
    try:
        fit = fit_penalized_logistic(logit, y, w, 0.0)
        return float(fit["coef"][0]), float(fit["coef"][1])
    except RuntimeError:
        return None, None


def metric_row(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> dict[str, Any]:
    intercept, slope = calibration_metrics(y, p, w)
    return {
        "brier": weighted_brier(y, p, w),
        "log_loss": weighted_logloss(y, p, w),
        "calibration_intercept": intercept,
        "calibration_slope": slope,
        "auroc": weighted_auc(y, p, w),
        "auprc": weighted_auprc(y, p, w),
        "minimum_probability": float(np.min(p)),
        "maximum_probability": float(np.max(p)),
    }


def _load_inputs(root: Path, contract: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    verify_package_manifest(root)
    data = pd.read_csv(root / "inputs/development_modeling_input.csv")
    outer = pd.read_csv(root / "inputs/outer_fold_assignments.csv")
    nested = pd.read_csv(root / "inputs/nested_fold_assignments.csv")
    pre_contract = load_contract(root / "contracts/feature_preprocessing_contract.json")
    expected = int(contract["scope"]["expected_pair_count"])
    if len(data) != expected or data["canonical_pair_id"].nunique() != expected:
        raise RuntimeError("not_exactly_expected_unique_development_pairs")
    if set(data["formal_sampling_stage"].astype(str)) != {"development"}:
        raise RuntimeError("locked_stage_input_detected")
    if set(data["review_ready_label"].dropna().unique()) != {0, 1}:
        raise RuntimeError("invalid_or_one_class_development_outcome")
    merged = data.merge(outer[["canonical_pair_id", "component_id", "outer_fold"]], on="canonical_pair_id", validate="one_to_one")
    if len(merged) != expected or merged[["component_id", "outer_fold"]].isna().any().any():
        raise RuntimeError("outer_fold_assignment_mismatch")
    for component, group in merged.groupby("component_id"):
        if group["outer_fold"].nunique() != 1:
            raise RuntimeError(f"outer_component_leakage:{component}")
    return merged, outer, nested, pre_contract


def verify_package_manifest(root: Path) -> None:
    manifest = root / "PACKAGE_MANIFEST.sha256"
    if not manifest.is_file():
        # Repository-side tests may call the runner before packaging.
        if root.name == "PF_ERI_TASK15E_MODELSCOPE_CPU_PACKAGE":
            raise RuntimeError("missing_package_manifest")
        return
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"package_manifest_hash_mismatch:{relative}")


def run_models(package_root: Path, output_dir: Path, outer_folds: list[int] | None = None, smoke: bool = False) -> dict[str, Any]:
    started = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = json.loads((package_root / "contracts/task15e_execution_contract.json").read_text())
    data, _, nested, preprocessing_contract = _load_inputs(package_root, contract)
    models = contract["models"]
    lambdas = list(map(float, contract["nested_validation"]["lambda_grid"]))
    all_outer = sorted(map(int, data["outer_fold"].unique()))
    selected_outer = all_outer if outer_folds is None else outer_folds
    predictions: list[dict[str, Any]] = []
    tuning_rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    coefficients: list[dict[str, Any]] = []

    for outer_fold in selected_outer:
        outer_train = data.loc[data["outer_fold"] != outer_fold].copy()
        outer_test = data.loc[data["outer_fold"] == outer_fold].copy()
        inner_map = nested.loc[nested["outer_fold_context"] == outer_fold, ["canonical_pair_id", "inner_fold"]]
        outer_train = outer_train.merge(inner_map, on="canonical_pair_id", validate="one_to_one")
        if len(outer_train) + len(outer_test) != len(data):
            raise RuntimeError(f"inner_assignment_mismatch_outer_{outer_fold}")
        for component, group in outer_train.groupby("component_id"):
            if group["inner_fold"].nunique() != 1:
                raise RuntimeError(f"inner_component_leakage:{outer_fold}:{component}")
        for model_id in MODEL_ORDER:
            model = models[model_id]
            family, blocks = model["family"], list(model["feature_blocks"])
            if model_id == "P0":
                y_train = outer_train["review_ready_label"].to_numpy(float)
                fit = fit_penalized_logistic(np.empty((len(outer_train), 0)), y_train, training_weights(outer_train["first_order_inclusion_probability"].to_numpy(float)), 0.0)
                probability = predict_probability(np.empty((len(outer_test), 0)), fit["coef"])
                chosen_lambda, design_columns = 0.0, []
            else:
                fold_scores: list[dict[str, Any]] = []
                for lam in lambdas:
                    for inner_fold in sorted(map(int, outer_train["inner_fold"].unique())):
                        inner_train = outer_train.loc[outer_train["inner_fold"] != inner_fold]
                        inner_valid = outer_train.loc[outer_train["inner_fold"] == inner_fold]
                        xtr, xva, meta = _design(inner_train, inner_valid, blocks, preprocessing_contract, family)
                        fit = fit_penalized_logistic(xtr.to_numpy(), inner_train["review_ready_label"].to_numpy(float), training_weights(inner_train["first_order_inclusion_probability"].to_numpy(float)), lam)
                        pva = predict_probability(xva.to_numpy(), fit["coef"])
                        score = weighted_brier(inner_valid["review_ready_label"].to_numpy(float), pva, evaluation_weights(inner_valid["first_order_inclusion_probability"].to_numpy(float)))
                        row = {"outer_fold": outer_fold, "model_id": model_id, "lambda": lam, "inner_fold": inner_fold, "brier": score, "validation_count": len(inner_valid)}
                        fold_scores.append(row); tuning_rows.append(row)
                fold_frame = pd.DataFrame(fold_scores)
                summary = fold_frame.groupby("lambda")["brier"].agg(["mean", "std", "count"]).reset_index()
                summary["mean_brier"] = summary["mean"]
                summary["se_brier"] = summary["std"].fillna(0.0) / np.sqrt(summary["count"])
                chosen_lambda = select_lambda_one_se(summary)
                xtr, xte, meta = _design(outer_train, outer_test, blocks, preprocessing_contract, family)
                fit = fit_penalized_logistic(xtr.to_numpy(), outer_train["review_ready_label"].to_numpy(float), training_weights(outer_train["first_order_inclusion_probability"].to_numpy(float)), chosen_lambda)
                probability = predict_probability(xte.to_numpy(), fit["coef"])
                design_columns = list(xtr.columns)
                for feature, value in zip(["intercept"] + design_columns, fit["coef"]):
                    coefficients.append({"outer_fold": outer_fold, "model_id": model_id, "lambda": chosen_lambda, "feature": feature, "coefficient": float(value)})
            diagnostics.append({
                "outer_fold": outer_fold, "model_id": model_id, "lambda": chosen_lambda,
                "train_count": len(outer_train), "test_count": len(outer_test), "design_column_count": len(design_columns),
                "optimizer_success": fit["success"], "optimizer_status": fit["status"], "optimizer_message": fit["message"],
                "optimizer_iterations": fit["iterations"], "objective": fit["objective"], "gradient_norm": fit["gradient_norm"]
            })
            for (_, row), prob in zip(outer_test.iterrows(), probability):
                predictions.append({
                    "canonical_pair_id": row["canonical_pair_id"], "pair_execution_id": row["pair_execution_id"],
                    "component_id": row["component_id"], "outer_fold": outer_fold, "model_id": model_id,
                    "review_ready_label": int(row["review_ready_label"]), "first_order_inclusion_probability": float(row["first_order_inclusion_probability"]),
                    "probability": float(prob), "brier_loss": float((row["review_ready_label"] - prob) ** 2)
                })
        # Required nested-model invariant, evaluated on the same outer training data.
        p3tr, _, _ = _design(outer_train, outer_test, list(models["P3"]["feature_blocks"]), preprocessing_contract, models["P3"]["family"])
        p5tr, _, _ = _design(outer_train, outer_test, list(models["P5"]["feature_blocks"]), preprocessing_contract, models["P5"]["family"])
        if list(p5tr.columns[:len(p3tr.columns)]) != list(p3tr.columns):
            raise RuntimeError(f"P3_P5_design_nesting_failure_outer_{outer_fold}")

    pred = pd.DataFrame(predictions)
    pred.to_csv(output_dir / "model_oof_predictions.csv", index=False)
    pd.DataFrame(tuning_rows).to_csv(output_dir / "inner_tuning_trace.csv", index=False)
    pd.DataFrame(diagnostics).to_csv(output_dir / "optimizer_diagnostics.csv", index=False)
    pd.DataFrame(coefficients).to_csv(output_dir / "coefficient_stability.csv", index=False)
    if smoke:
        expected_test_pairs = int((data["outer_fold"] == selected_outer[0]).sum())
        smoke_failures = []
        if len(pred) != expected_test_pairs * len(MODEL_ORDER): smoke_failures.append("smoke_prediction_count_mismatch")
        if pred.duplicated(["canonical_pair_id", "model_id"]).any(): smoke_failures.append("smoke_duplicate_predictions")
        if pred["canonical_pair_id"].nunique() != expected_test_pairs: smoke_failures.append("smoke_pair_coverage_mismatch")
        if set(pred["model_id"]) != set(MODEL_ORDER): smoke_failures.append("smoke_model_coverage_mismatch")
        if not np.isfinite(pred["probability"].to_numpy(float)).all() or not pred["probability"].between(0, 1).all(): smoke_failures.append("smoke_invalid_probability")
        if not all(row["optimizer_success"] for row in diagnostics): smoke_failures.append("smoke_optimizer_failure")
        if smoke_failures: raise RuntimeError(f"smoke_gate_failed:{smoke_failures}")
    else:
        build_summaries(pred, output_dir)
    shutil.copy2(package_root / "contracts/task15e_execution_contract.json", output_dir / "execution_contract_frozen.json")
    audit = {
        "status": "SMOKE_PASS" if smoke else "RUN_COMPLETE_PENDING_VALIDATION",
        "created_at_utc": utc_now(), "runtime_seconds": time.time() - started,
        "outer_folds_executed": selected_outer, "prediction_rows": len(pred),
        "input_sha256": sha256(package_root / "inputs/development_modeling_input.csv"),
        "contract_sha256": sha256(package_root / "contracts/task15e_execution_contract.json"),
        "python_version": sys.version, "platform": platform.platform(), "numpy_version": np.__version__, "pandas_version": pd.__version__,
        "cpu_count": os.cpu_count(), "gpu_used": False
    }
    write_json(output_dir / ("smoke_audit.json" if smoke else "execution_audit.json"), audit)
    return audit


def build_summaries(pred: pd.DataFrame, output_dir: Path) -> None:
    overall, folds = [], []
    for model_id, group in pred.groupby("model_id", sort=False):
        y, p = group["review_ready_label"].to_numpy(float), group["probability"].to_numpy(float)
        weighted = metric_row(y, p, evaluation_weights(group["first_order_inclusion_probability"].to_numpy(float)))
        unweighted = metric_row(y, p, np.ones(len(group)))
        overall.append({"model_id": model_id, **{f"weighted_{k}": v for k, v in weighted.items()}, **{f"unweighted_{k}": v for k, v in unweighted.items()}, "pair_count": len(group)})
        for outer, fold in group.groupby("outer_fold"):
            metrics = metric_row(fold["review_ready_label"].to_numpy(float), fold["probability"].to_numpy(float), evaluation_weights(fold["first_order_inclusion_probability"].to_numpy(float)))
            folds.append({"model_id": model_id, "outer_fold": int(outer), "pair_count": len(fold), **metrics})
    pd.DataFrame(overall).to_csv(output_dir / "overall_model_metrics.csv", index=False)
    pd.DataFrame(folds).to_csv(output_dir / "outer_fold_metrics.csv", index=False)
    wide = pred.pivot(index="canonical_pair_id", columns="model_id", values="brier_loss")
    metadata = pred.drop_duplicates("canonical_pair_id").set_index("canonical_pair_id")
    delta = wide["P3"] - wide["P5"]
    weight = 1.0 / metadata.loc[delta.index, "first_order_inclusion_probability"]
    comparison = {"status": "DESCRIPTIVE_DEVELOPMENT_ONLY", "definition": "Brier(P3)-Brier(P5)", "weighted_delta_brier": float(np.average(delta, weights=weight)), "unweighted_delta_brier": float(delta.mean()), "positive_means_full_P5_better": True}
    write_json(output_dir / "P3_P5_paired_brier_results.json", comparison)
    component = pd.DataFrame({"component_id": metadata.loc[delta.index, "component_id"], "delta_brier": delta, "weight": weight}).groupby("component_id").apply(lambda g: pd.Series({"pair_count": len(g), "weighted_delta_brier": np.average(g.delta_brier, weights=g.weight)}), include_groups=False).reset_index()
    component.to_csv(output_dir / "component_paired_regret.csv", index=False)
    report = "# PF-ERI Task 15E Development Comparison\n\nStatus: `DESCRIPTIVE_DEVELOPMENT_ONLY`\n\nThis run uses only the 445 open development pairs. Calibration, deployment-confirmation, and mechanism-confirmation outcomes remain locked.\n\n## P3 versus P5\n\n- Weighted ΔBrier = Brier(P3) − Brier(P5): `{:.8f}`\n- Positive values favor the full PF-ERI model P5.\n- This is development evidence, not a confirmatory test.\n".format(comparison["weighted_delta_brier"])
    (output_dir / "DEVELOPMENT_COMPARISON_REPORT.md").write_text(report, encoding="utf-8")


def validate_results(results_dir: Path, expected_pairs: int = 445, expected_models: list[str] | None = None, write_audit: bool = True) -> dict[str, Any]:
    models = expected_models or MODEL_ORDER
    failures: list[str] = []
    required = ["model_oof_predictions.csv", "execution_contract_frozen.json", "inner_tuning_trace.csv", "optimizer_diagnostics.csv"]
    for name in required:
        if not (results_dir / name).is_file(): failures.append(f"missing_required_output:{name}")
    path = results_dir / "model_oof_predictions.csv"
    if path.is_file():
        frame = pd.read_csv(path)
        needed = {"canonical_pair_id", "model_id", "probability"}
        if not needed.issubset(frame.columns): failures.append("prediction_schema_invalid")
        else:
            if frame.duplicated(["canonical_pair_id", "model_id"]).any(): failures.append("duplicate_pair_model_prediction")
            if len(frame) != expected_pairs * len(models): failures.append("prediction_row_count_mismatch")
            if frame["canonical_pair_id"].nunique() != expected_pairs: failures.append("pair_coverage_mismatch")
            if set(frame["model_id"]) != set(models): failures.append("model_coverage_mismatch")
            probs = pd.to_numeric(frame["probability"], errors="coerce")
            if probs.isna().any() or (~probs.between(0, 1)).any(): failures.append("invalid_probability")
    audit = {"status": "PASS" if not failures else "FAIL", "validated_at_utc": utc_now(), "expected_pairs": expected_pairs, "expected_models": models, "failures": failures}
    if write_audit: write_json(results_dir / "validation_audit.json", audit)
    return audit


def write_checksums(root: Path) -> None:
    files = [p for p in root.rglob("*") if p.is_file() and p.name not in {"CHECKSUMS.sha256", "PF_ERI_TASK15E_FINAL_EXPORT.zip"}]
    (root / "CHECKSUMS.sha256").write_text("".join(f"{sha256(p)}  {p.relative_to(root)}\n" for p in sorted(files)), encoding="utf-8")


def build_export(results_dir: Path, zip_path: Path) -> dict[str, Any]:
    audit = validate_results(results_dir)
    if audit["status"] != "PASS": raise RuntimeError(f"result_validation_failed:{audit['failures']}")
    write_checksums(results_dir)
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in results_dir.rglob("*") if p.is_file() and p.resolve() != zip_path.resolve()):
            archive.write(path, arcname=f"PF_ERI_TASK15E_RESULTS/{path.relative_to(results_dir)}")
    return {"status": "PASS", "zip": str(zip_path), "zip_sha256": sha256(zip_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ["smoke", "run"]:
        p = sub.add_parser(command); p.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parent); p.add_argument("--output-dir", type=Path, required=True)
    p = sub.add_parser("validate"); p.add_argument("--results-dir", type=Path, required=True)
    p = sub.add_parser("export"); p.add_argument("--results-dir", type=Path, required=True); p.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "smoke": result = run_models(args.package_root.resolve(), args.output_dir.resolve(), outer_folds=[0], smoke=True)
        elif args.command == "run": result = run_models(args.package_root.resolve(), args.output_dir.resolve()); result = validate_results(args.output_dir.resolve())
        elif args.command == "validate": result = validate_results(args.results_dir.resolve())
        else: result = build_export(args.results_dir.resolve(), args.zip.resolve())
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2)); return 1
    print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["status"] in {"PASS", "SMOKE_PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
