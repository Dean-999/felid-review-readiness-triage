#!/usr/bin/env python3
"""PF-ERI v2 Task 15G exploratory performance-bound execution runner."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import itertools
import json
import os
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
from scipy.optimize import minimize

sys.dont_write_bytecode = True

try:
    from pferi_v2_fold_preprocessor import fit_fold_preprocessor, load_contract
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pferi_v2_fold_preprocessor import fit_fold_preprocessor, load_contract


MODELS = ("E1", "E2")
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
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def training_weights(probability: np.ndarray) -> np.ndarray:
    raw = 1.0 / np.sqrt(np.asarray(probability, dtype=float))
    if np.any(~np.isfinite(raw)) or np.any(raw <= 0):
        raise ValueError("invalid_training_inclusion_probability")
    return raw / raw.mean()


def evaluation_weights(probability: np.ndarray) -> np.ndarray:
    raw = 1.0 / np.asarray(probability, dtype=float)
    if np.any(~np.isfinite(raw)) or np.any(raw <= 0):
        raise ValueError("invalid_evaluation_inclusion_probability")
    return raw / raw.mean()


def weighted_brier(y: np.ndarray, probability: np.ndarray, weights: np.ndarray) -> float:
    return float(np.average((y - probability) ** 2, weights=weights))


def weighted_log_loss(y: np.ndarray, probability: np.ndarray, weights: np.ndarray) -> float:
    probability = np.clip(probability, EPS, 1.0 - EPS)
    return float(
        np.average(
            -(y * np.log(probability) + (1.0 - y) * np.log(1.0 - probability)),
            weights=weights,
        )
    )


def weighted_auc(y: np.ndarray, probability: np.ndarray, weights: np.ndarray) -> float | None:
    positive, negative = y == 1, y == 0
    if not positive.any() or not negative.any():
        return None
    comparison = (probability[positive][:, None] > probability[negative][None, :]).astype(float)
    comparison += 0.5 * (
        probability[positive][:, None] == probability[negative][None, :]
    )
    pair_weights = weights[positive][:, None] * weights[negative][None, :]
    return float(np.sum(comparison * pair_weights) / np.sum(pair_weights))


def weighted_auprc(y: np.ndarray, probability: np.ndarray, weights: np.ndarray) -> float | None:
    if not np.any(y == 1):
        return None
    order = np.argsort(-probability, kind="mergesort")
    ordered_y, ordered_w = y[order], weights[order]
    true_positive = np.cumsum(ordered_w * ordered_y)
    false_positive = np.cumsum(ordered_w * (1.0 - ordered_y))
    recall = true_positive / true_positive[-1]
    precision = true_positive / (true_positive + false_positive)
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


def _calibration_objective(
    beta: np.ndarray, design: np.ndarray, outcome: np.ndarray, weights: np.ndarray
) -> tuple[float, np.ndarray]:
    eta = design @ beta
    probability = 1.0 / (1.0 + np.exp(-np.clip(eta, -36.0, 36.0)))
    objective = float(
        np.sum(weights * (np.logaddexp(0.0, eta) - outcome * eta)) / np.sum(weights)
    )
    gradient = design.T @ (weights * (probability - outcome)) / np.sum(weights)
    return objective, gradient


def calibration_metrics(
    y: np.ndarray, probability: np.ndarray, weights: np.ndarray
) -> tuple[float | None, float | None]:
    if len(np.unique(y)) < 2:
        return None, None
    clipped = np.clip(probability, EPS, 1.0 - EPS)
    logit = np.log(clipped / (1.0 - clipped))
    design = np.column_stack([np.ones(len(logit)), logit])
    result = minimize(
        lambda beta: _calibration_objective(beta, design, y, weights),
        np.array([0.0, 1.0]),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": 2000, "gtol": 1e-9, "ftol": 1e-12},
    )
    if not result.success or not np.isfinite(result.x).all():
        return None, None
    return float(result.x[0]), float(result.x[1])


def metric_row(y: np.ndarray, probability: np.ndarray, weights: np.ndarray) -> dict[str, Any]:
    intercept, slope = calibration_metrics(y, probability, weights)
    return {
        "brier": weighted_brier(y, probability, weights),
        "log_loss": weighted_log_loss(y, probability, weights),
        "calibration_intercept": intercept,
        "calibration_slope": slope,
        "auroc": weighted_auc(y, probability, weights),
        "auprc": weighted_auprc(y, probability, weights),
        "minimum_probability": float(np.min(probability)),
        "maximum_probability": float(np.max(probability)),
    }


def verify_manifest(root: Path) -> str:
    manifest = root / "PACKAGE_MANIFEST.sha256"
    if not manifest.is_file():
        raise RuntimeError("missing_package_manifest")
    declared: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        declared.add(relative)
        target = root / relative
        if not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"package_hash_mismatch:{relative}")
    actual = {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256"
    }
    if actual != declared:
        raise RuntimeError(
            f"package_inventory_mismatch:missing={sorted(declared - actual)}:"
            f"unexpected={sorted(actual - declared)}"
        )
    return sha256(manifest)


def load_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    verify_manifest(root)
    contract_path = root / "contracts/task15g_exploratory_performance_bound_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    paths = {
        "development_modeling_input.csv": root / "inputs/development_modeling_input.csv",
        "outer_fold_assignments.csv": root / "inputs/outer_fold_assignments.csv",
        "nested_fold_assignments.csv": root / "inputs/nested_fold_assignments.csv",
        "feature_preprocessing_contract.json": root / "contracts/feature_preprocessing_contract.json",
        "fold_preprocessor.py": root / "pferi_v2_fold_preprocessor.py",
        "candidate_model_registry.json": root / "contracts/candidate_model_registry.json",
        "task15f_disposition.json": root / "audits/task15f_disposition.json",
    }
    failures = [
        name
        for name, path in paths.items()
        if not path.is_file() or sha256(path) != contract["authoritative_inputs"][name]
    ]
    if failures:
        raise RuntimeError(f"authoritative_input_hash_mismatch:{failures}")
    data = pd.read_csv(paths["development_modeling_input.csv"])
    outer = pd.read_csv(paths["outer_fold_assignments.csv"])
    nested = pd.read_csv(paths["nested_fold_assignments.csv"])
    frame = data.merge(
        outer[["canonical_pair_id", "component_id", "outer_fold"]],
        on="canonical_pair_id",
        validate="one_to_one",
    )
    if len(frame) != 445 or frame["canonical_pair_id"].nunique() != 445:
        raise RuntimeError("development_pair_count_mismatch")
    if frame["component_id"].nunique() != 116:
        raise RuntimeError("component_count_mismatch")
    if set(frame["formal_sampling_stage"].astype(str)) != {"development"}:
        raise RuntimeError("locked_stage_input_detected")
    if set(frame["review_ready_label"].dropna().astype(int).unique()) != {0, 1}:
        raise RuntimeError("invalid_or_one_class_development_outcome")
    if frame.groupby("component_id")["outer_fold"].nunique().max() != 1:
        raise RuntimeError("outer_component_leakage")
    if len(nested) != 1780:
        raise RuntimeError("nested_assignment_count_mismatch")
    preprocessing = load_contract(paths["feature_preprocessing_contract.json"])
    return frame, nested, contract, preprocessing


def expand_configurations(model: dict[str, Any]) -> list[dict[str, Any]]:
    grid = model["configuration_grid"]
    keys = list(grid)
    configurations = [
        dict(zip(keys, values)) for values in itertools.product(*(grid[key] for key in keys))
    ]
    if len(configurations) != int(model["configuration_count"]):
        raise RuntimeError("configuration_count_mismatch")
    return configurations


def configuration_id(model_id: str, index: int) -> str:
    return f"{model_id}_C{index:02d}"


def tie_key(model_id: str, configuration: dict[str, Any]) -> tuple[Any, ...]:
    if model_id == "E1":
        return (
            int(configuration["max_leaves"]),
            int(configuration["max_bins"]),
            float(configuration["learning_rate"]),
        )
    if model_id == "E2":
        return (
            int(configuration["depth"]),
            -float(configuration["l2_leaf_reg"]),
            float(configuration["learning_rate"]),
        )
    raise ValueError(f"unknown model: {model_id}")


def select_configuration(
    model_id: str, results: pd.DataFrame, tolerance: float
) -> tuple[str, dict[str, Any], float]:
    valid = results.loc[results["status"] == "PASS"].copy()
    counts = valid.groupby("configuration_id")["inner_fold"].nunique()
    complete_ids = counts.loc[counts == 4].index
    valid = valid.loc[valid["configuration_id"].isin(complete_ids)]
    if valid.empty:
        raise RuntimeError(f"no_complete_configuration:{model_id}")
    summary = valid.groupby("configuration_id", as_index=False)["brier"].mean()
    minimum = float(summary["brier"].min())
    eligible_ids = set(
        summary.loc[summary["brier"] <= minimum + tolerance, "configuration_id"]
    )
    candidates: list[tuple[tuple[Any, ...], str, dict[str, Any], float]] = []
    for config_id in eligible_ids:
        first = valid.loc[valid["configuration_id"] == config_id].iloc[0]
        configuration = json.loads(first["configuration_json"])
        score = float(summary.loc[summary["configuration_id"] == config_id, "brier"].iloc[0])
        candidates.append((tie_key(model_id, configuration), config_id, configuration, score))
    _, config_id, configuration, score = min(candidates)
    return config_id, configuration, score


def seed_for(model_id: str, outer_fold: int, inner_fold: int, configuration_index: int) -> int:
    base = 150700 if model_id == "E1" else 150800
    return base + 100 * outer_fold + 10 * inner_fold + configuration_index


def make_estimator(
    model_id: str, model: dict[str, Any], configuration: dict[str, Any], seed: int
) -> Any:
    parameters = {**model["fixed_parameters"], **configuration}
    if model_id == "E1":
        from interpret.glassbox import ExplainableBoostingClassifier

        return ExplainableBoostingClassifier(**parameters, random_state=seed)
    if model_id == "E2":
        from catboost import CatBoostClassifier

        return CatBoostClassifier(**parameters, random_seed=seed)
    raise ValueError(f"unknown model: {model_id}")


def fit_predict(
    model_id: str,
    model: dict[str, Any],
    configuration: dict[str, Any],
    seed: int,
    x_train: pd.DataFrame,
    train: pd.DataFrame,
    x_validation: pd.DataFrame,
) -> np.ndarray:
    estimator = make_estimator(model_id, model, configuration, seed)
    estimator.fit(
        x_train.to_numpy(float),
        train["review_ready_label"].to_numpy(int),
        sample_weight=training_weights(
            train["first_order_inclusion_probability"].to_numpy(float)
        ),
    )
    probability = np.asarray(estimator.predict_proba(x_validation.to_numpy(float)))[:, 1]
    if not np.isfinite(probability).all() or np.any((probability < 0) | (probability > 1)):
        raise RuntimeError("invalid_model_probability")
    return probability


def design(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    preprocessing: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    fitted = fit_fold_preprocessor(
        train, preprocessing, ["descriptor", "independent_quality", "pair_evidence"]
    )
    return fitted.transform(train), fitted.transform(validation), fitted.sha256


def runtime_audit(package_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    packages = {
        "interpret": contract["models"]["E1"]["package"].split("==", 1)[1],
        "catboost": contract["models"]["E2"]["package"].split("==", 1)[1],
    }
    installed: dict[str, str] = {}
    for package, expected in packages.items():
        try:
            installed[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            failures.append(f"missing_package:{package}")
            continue
        if installed[package] != expected:
            failures.append(f"package_version_mismatch:{package}")

    checkpoint = contract["models"]["E3"]["checkpoint"]
    checkpoint_path = package_root / "models" / checkpoint["filename"]
    if not checkpoint_path.is_file():
        failures.append("missing_E3_checkpoint")
    else:
        if checkpoint_path.stat().st_size != checkpoint["size_bytes"]:
            failures.append("E3_checkpoint_size_mismatch")
        if sha256(checkpoint_path) != checkpoint["sha256"]:
            failures.append("E3_checkpoint_sha256_mismatch")
    api_audit = json.loads(
        (package_root / "audits/tabpfn_api_precheck.json").read_text(encoding="utf-8")
    )
    if api_audit.get("fit_signature") != "fit(self, X, y)":
        failures.append("E3_fit_signature_mismatch")
    if api_audit.get("supports_sample_weight") is not False:
        failures.append("E3_weight_support_mismatch")

    for model_id in MODELS:
        configuration = expand_configurations(contract["models"][model_id])[0]
        try:
            estimator = make_estimator(
                model_id, contract["models"][model_id], configuration, seed_for(model_id, 0, 0, 0)
            )
            if "sample_weight" not in inspect.signature(estimator.fit).parameters:
                failures.append(f"missing_sample_weight_api:{model_id}")
        except Exception as error:
            failures.append(f"estimator_construction_failed:{model_id}:{type(error).__name__}")
    return {
        "status": "PASS" if not failures else "FAIL",
        "checked_at_utc": utc_now(),
        "installed_packages": installed,
        "E3_checkpoint_sha256": sha256(checkpoint_path) if checkpoint_path.is_file() else None,
        "E3_disposition": contract["models"]["E3"]["sample_weight_api_precheck"]["disposition"],
        "E3_prediction_rows": 0,
        "failures": failures,
    }


def smoke(package_root: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame, _, contract, preprocessing = load_inputs(package_root)
    availability = runtime_audit(package_root, contract)
    write_json(output_dir / "model_availability_audit.json", availability)
    if availability["status"] != "PASS":
        raise RuntimeError(f"runtime_precheck_failed:{availability['failures']}")
    outer_train = frame.loc[frame["outer_fold"] != 0].copy()
    outer_test = frame.loc[frame["outer_fold"] == 0].head(16).copy()
    x_train, x_test, preprocessor_sha = design(outer_train, outer_test, preprocessing)
    checks: list[dict[str, Any]] = []
    for model_id in MODELS:
        configuration = expand_configurations(contract["models"][model_id])[0]
        probability = fit_predict(
            model_id,
            contract["models"][model_id],
            configuration,
            seed_for(model_id, 0, 9, 0),
            x_train,
            outer_train,
            x_test,
        )
        checks.append(
            {
                "model_id": model_id,
                "rows": len(probability),
                "minimum_probability": float(probability.min()),
                "maximum_probability": float(probability.max()),
                "preprocessor_sha256": preprocessor_sha,
                "status": "PASS",
            }
        )
    audit = {
        "status": "PASS",
        "created_at_utc": utc_now(),
        "package_manifest_sha256": verify_manifest(package_root),
        "contract_sha256": sha256(
            package_root / "contracts/task15g_exploratory_performance_bound_contract.json"
        ),
        "checks": checks,
        "E3_disposition": availability["E3_disposition"],
        "locked_stage_outcomes_accessed": False,
    }
    write_json(output_dir / "smoke_audit.json", audit)
    return audit


def checkpoint_paths(output_dir: Path, model_id: str, outer_fold: int) -> dict[str, Path]:
    root = output_dir / "fold_checkpoints"
    prefix = f"{model_id}_fold{outer_fold}"
    return {
        "checkpoint": root / f"{prefix}.json",
        "predictions": root / f"{prefix}_predictions.csv",
        "inner": root / f"{prefix}_inner_selection.csv",
        "selected": root / f"{prefix}_selected_configuration.json",
    }


def load_checkpoint(
    paths: dict[str, Path], contract_sha: str
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]] | None:
    if not paths["checkpoint"].is_file():
        return None
    saved = json.loads(paths["checkpoint"].read_text(encoding="utf-8"))
    if saved.get("status") != "PASS" or saved.get("contract_sha256") != contract_sha:
        return None
    for key in ("predictions", "inner", "selected"):
        target = paths[key]
        if not target.is_file() or saved.get(f"{key}_sha256") != sha256(target):
            return None
    return (
        pd.read_csv(paths["predictions"]),
        pd.read_csv(paths["inner"]),
        json.loads(paths["selected"].read_text(encoding="utf-8")),
    )


def run_fold_model(
    frame: pd.DataFrame,
    nested: pd.DataFrame,
    contract: dict[str, Any],
    preprocessing: dict[str, Any],
    model_id: str,
    outer_fold: int,
    output_dir: Path,
    contract_sha: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], bool]:
    paths = checkpoint_paths(output_dir, model_id, outer_fold)
    resumed = load_checkpoint(paths, contract_sha)
    if resumed is not None:
        return *resumed, True

    outer_train = frame.loc[frame["outer_fold"] != outer_fold].copy()
    outer_test = frame.loc[frame["outer_fold"] == outer_fold].copy()
    inner_map = nested.loc[
        nested["outer_fold_context"].astype(int) == outer_fold,
        ["canonical_pair_id", "inner_fold"],
    ]
    outer_train = outer_train.merge(inner_map, on="canonical_pair_id", validate="one_to_one")
    if len(outer_train) + len(outer_test) != len(frame):
        raise RuntimeError(f"inner_assignment_mismatch:{outer_fold}")
    if outer_train.groupby("component_id")["inner_fold"].nunique().max() != 1:
        raise RuntimeError(f"inner_component_leakage:{outer_fold}")

    model = contract["models"][model_id]
    configurations = expand_configurations(model)
    rows: list[dict[str, Any]] = []
    for config_index, configuration in enumerate(configurations):
        config_id = configuration_id(model_id, config_index)
        for inner_fold in range(4):
            inner_train = outer_train.loc[outer_train["inner_fold"] != inner_fold]
            inner_valid = outer_train.loc[outer_train["inner_fold"] == inner_fold]
            row: dict[str, Any] = {
                "outer_fold": outer_fold,
                "model_id": model_id,
                "configuration_id": config_id,
                "configuration_json": json.dumps(configuration, sort_keys=True),
                "inner_fold": inner_fold,
                "training_rows": len(inner_train),
                "validation_rows": len(inner_valid),
                "seed": seed_for(model_id, outer_fold, inner_fold, config_index),
            }
            try:
                x_train, x_valid, preprocessor_sha = design(
                    inner_train, inner_valid, preprocessing
                )
                probability = fit_predict(
                    model_id,
                    model,
                    configuration,
                    row["seed"],
                    x_train,
                    inner_train,
                    x_valid,
                )
                row.update(
                    {
                        "status": "PASS",
                        "brier": weighted_brier(
                            inner_valid["review_ready_label"].to_numpy(float),
                            probability,
                            evaluation_weights(
                                inner_valid[
                                    "first_order_inclusion_probability"
                                ].to_numpy(float)
                            ),
                        ),
                        "preprocessor_sha256": preprocessor_sha,
                        "error_type": "",
                        "error": "",
                    }
                )
            except Exception as error:
                row.update(
                    {
                        "status": "FAIL",
                        "brier": None,
                        "preprocessor_sha256": "",
                        "error_type": type(error).__name__,
                        "error": str(error),
                    }
                )
            rows.append(row)
    inner_results = pd.DataFrame(rows)
    selected_id, selected_config, selected_score = select_configuration(
        model_id,
        inner_results,
        float(contract["common_design"]["selection_tie_tolerance"]),
    )
    selected_index = int(selected_id.rsplit("C", 1)[1])
    x_train, x_test, preprocessor_sha = design(outer_train, outer_test, preprocessing)
    probability = fit_predict(
        model_id,
        model,
        selected_config,
        seed_for(model_id, outer_fold, 9, selected_index),
        x_train,
        outer_train,
        x_test,
    )
    predictions = pd.DataFrame(
        {
            "canonical_pair_id": outer_test["canonical_pair_id"].to_numpy(),
            "pair_execution_id": outer_test["pair_execution_id"].to_numpy(),
            "component_id": outer_test["component_id"].to_numpy(),
            "outer_fold": outer_fold,
            "model_id": model_id,
            "review_ready_label": outer_test["review_ready_label"].astype(int).to_numpy(),
            "first_order_inclusion_probability": outer_test[
                "first_order_inclusion_probability"
            ].astype(float).to_numpy(),
            "probability": probability,
            "brier_loss": (
                outer_test["review_ready_label"].to_numpy(float) - probability
            )
            ** 2,
        }
    )
    selected = {
        "status": "PASS",
        "outer_fold": outer_fold,
        "model_id": model_id,
        "configuration_id": selected_id,
        "configuration": selected_config,
        "mean_inner_brier": selected_score,
        "outer_refit_seed": seed_for(model_id, outer_fold, 9, selected_index),
        "outer_train_rows": len(outer_train),
        "outer_test_rows": len(outer_test),
        "preprocessor_sha256": preprocessor_sha,
    }
    paths["checkpoint"].parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(paths["predictions"], index=False)
    inner_results.to_csv(paths["inner"], index=False)
    write_json(paths["selected"], selected)
    write_json(
        paths["checkpoint"],
        {
            "status": "PASS",
            "created_at_utc": utc_now(),
            "contract_sha256": contract_sha,
            "predictions_sha256": sha256(paths["predictions"]),
            "inner_sha256": sha256(paths["inner"]),
            "selected_sha256": sha256(paths["selected"]),
        },
    )
    return predictions, inner_results, selected, False


def build_summaries(
    predictions: pd.DataFrame, selected: pd.DataFrame, output_dir: Path
) -> None:
    overall: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    for model_id, group in predictions.groupby("model_id", sort=True):
        y = group["review_ready_label"].to_numpy(float)
        probability = group["probability"].to_numpy(float)
        weighted = metric_row(
            y,
            probability,
            evaluation_weights(
                group["first_order_inclusion_probability"].to_numpy(float)
            ),
        )
        unweighted = metric_row(y, probability, np.ones(len(group)))
        overall.append(
            {
                "model_id": model_id,
                "pair_count": len(group),
                **{f"weighted_{key}": value for key, value in weighted.items()},
                **{f"unweighted_{key}": value for key, value in unweighted.items()},
            }
        )
        for outer_fold, fold in group.groupby("outer_fold"):
            metrics = metric_row(
                fold["review_ready_label"].to_numpy(float),
                fold["probability"].to_numpy(float),
                evaluation_weights(
                    fold["first_order_inclusion_probability"].to_numpy(float)
                ),
            )
            folds.append(
                {
                    "model_id": model_id,
                    "outer_fold": int(outer_fold),
                    "pair_count": len(fold),
                    **metrics,
                }
            )
    pd.DataFrame(overall).to_csv(
        output_dir / "exploratory_overall_metrics.csv", index=False
    )
    pd.DataFrame(folds).to_csv(
        output_dir / "exploratory_outer_fold_metrics.csv", index=False
    )

    losses = predictions.pivot(
        index="canonical_pair_id", columns="model_id", values="brier_loss"
    )
    metadata = predictions.drop_duplicates("canonical_pair_id").set_index(
        "canonical_pair_id"
    )
    best = losses.min(axis=1)
    regret_rows: list[dict[str, Any]] = []
    for model_id in MODELS:
        regret = losses[model_id] - best
        frame = pd.DataFrame(
            {
                "component_id": metadata.loc[regret.index, "component_id"],
                "regret": regret,
                "weight": 1.0
                / metadata.loc[
                    regret.index, "first_order_inclusion_probability"
                ].astype(float),
            }
        )
        for component_id, group in frame.groupby("component_id"):
            regret_rows.append(
                {
                    "model_id": model_id,
                    "component_id": component_id,
                    "pair_count": len(group),
                    "weighted_brier_regret_to_pairwise_exploratory_oracle": float(
                        np.average(group["regret"], weights=group["weight"])
                    ),
                }
            )
    pd.DataFrame(regret_rows).to_csv(
        output_dir / "component_paired_brier_regret.csv", index=False
    )

    stability: list[dict[str, Any]] = []
    for model_id, group in selected.groupby("model_id"):
        counts = group["configuration_id"].value_counts()
        for config_id, count in counts.items():
            stability.append(
                {
                    "model_id": model_id,
                    "configuration_id": config_id,
                    "outer_folds_selected": int(count),
                    "selection_fraction": float(count / 5.0),
                }
            )
    pd.DataFrame(stability).to_csv(
        output_dir / "configuration_stability.csv", index=False
    )


def run(package_root: Path, output_dir: Path, smoke_audit_path: Path) -> dict[str, Any]:
    started = time.time()
    smoke_audit = json.loads(smoke_audit_path.read_text(encoding="utf-8"))
    manifest_sha = verify_manifest(package_root)
    if smoke_audit.get("status") != "PASS":
        raise RuntimeError("smoke_gate_not_passed")
    if smoke_audit.get("package_manifest_sha256") != manifest_sha:
        raise RuntimeError("smoke_gate_package_mismatch")
    frame, nested, contract, preprocessing = load_inputs(package_root)
    availability = runtime_audit(package_root, contract)
    if availability["status"] != "PASS":
        raise RuntimeError(f"runtime_precheck_failed:{availability['failures']}")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "model_availability_audit.json", availability)
    contract_path = package_root / "contracts/task15g_exploratory_performance_bound_contract.json"
    contract_sha = sha256(contract_path)
    predictions: list[pd.DataFrame] = []
    inner_results: list[pd.DataFrame] = []
    selections: list[dict[str, Any]] = []
    resumed: list[str] = []
    for outer_fold in range(5):
        for model_id in MODELS:
            pred, inner, selected, was_resumed = run_fold_model(
                frame,
                nested,
                contract,
                preprocessing,
                model_id,
                outer_fold,
                output_dir,
                contract_sha,
            )
            predictions.append(pred)
            inner_results.append(inner)
            selections.append(selected)
            if was_resumed:
                resumed.append(f"{model_id}_fold{outer_fold}")
    prediction_frame = pd.concat(predictions, ignore_index=True)
    inner_frame = pd.concat(inner_results, ignore_index=True)
    selected_frame = pd.DataFrame(selections)
    prediction_frame.to_csv(output_dir / "exploratory_oof_predictions.csv", index=False)
    inner_frame.to_csv(output_dir / "inner_selection_results.csv", index=False)
    selected_frame.to_csv(output_dir / "selected_configurations.csv", index=False)
    build_summaries(prediction_frame, selected_frame, output_dir)
    shutil.copy2(contract_path, output_dir / "execution_contract_frozen.json")
    report = """# PF-ERI Task 15G Exploratory Performance-Bound Benchmark

Status: `RUN_COMPLETE_PENDING_VALIDATION`

This run uses only the 445 open development pairs and the frozen endpoint-component-disjoint nested folds. E1 and E2 use fold-training preprocessing, square-root inverse-probability fitting weights, and design-weighted validation. E3 emits no prediction because its frozen API cannot consume the required fitting weights.

The resulting metrics estimate a bounded exploratory development performance ceiling. They do not select a final model, confer confirmation eligibility, or authorize opening calibration. Task 15H must apply qualification before performance after this export is independently validated and frozen.
"""
    (output_dir / "TASK15G_EXPLORATORY_PERFORMANCE_BOUND_REPORT.md").write_text(
        report, encoding="utf-8"
    )
    audit = {
        "status": "RUN_COMPLETE_PENDING_VALIDATION",
        "created_at_utc": utc_now(),
        "runtime_seconds": time.time() - started,
        "prediction_rows": len(prediction_frame),
        "inner_selection_rows": len(inner_frame),
        "selected_configuration_rows": len(selected_frame),
        "outer_folds_executed": list(range(5)),
        "eligible_models_executed": list(MODELS),
        "E3_prediction_rows": 0,
        "resumed_fold_models": resumed,
        "contract_sha256": contract_sha,
        "package_manifest_sha256": manifest_sha,
        "locked_stage_outcomes_accessed": False,
        "final_model_selected": False,
        "python_version": sys.version,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "interpret_version": importlib.metadata.version("interpret"),
        "catboost_version": importlib.metadata.version("catboost"),
    }
    write_json(output_dir / "execution_audit.json", audit)
    return audit


def validate_results(results_dir: Path, write: bool = True) -> dict[str, Any]:
    failures: list[str] = []
    required = [
        "execution_contract_frozen.json",
        "model_availability_audit.json",
        "inner_selection_results.csv",
        "selected_configurations.csv",
        "exploratory_oof_predictions.csv",
        "exploratory_outer_fold_metrics.csv",
        "exploratory_overall_metrics.csv",
        "component_paired_brier_regret.csv",
        "configuration_stability.csv",
        "execution_audit.json",
        "TASK15G_EXPLORATORY_PERFORMANCE_BOUND_REPORT.md",
    ]
    for name in required:
        if not (results_dir / name).is_file():
            failures.append(f"missing_required_output:{name}")
    prediction_path = results_dir / "exploratory_oof_predictions.csv"
    if prediction_path.is_file():
        prediction = pd.read_csv(prediction_path)
        needed = {"canonical_pair_id", "model_id", "outer_fold", "probability"}
        if not needed.issubset(prediction.columns):
            failures.append("prediction_schema_invalid")
        else:
            if len(prediction) != 890:
                failures.append("prediction_row_count_mismatch")
            if prediction["canonical_pair_id"].nunique() != 445:
                failures.append("prediction_pair_coverage_mismatch")
            if set(prediction["model_id"]) != set(MODELS):
                failures.append("prediction_model_coverage_mismatch")
            if prediction.duplicated(["canonical_pair_id", "model_id"]).any():
                failures.append("duplicate_pair_model_prediction")
            probability = pd.to_numeric(prediction["probability"], errors="coerce")
            if probability.isna().any() or (~probability.between(0, 1)).any():
                failures.append("invalid_probability")
    inner_path = results_dir / "inner_selection_results.csv"
    if inner_path.is_file():
        inner = pd.read_csv(inner_path)
        if len(inner) != 400:
            failures.append("inner_selection_row_count_mismatch")
        if set(inner.get("model_id", [])) != set(MODELS):
            failures.append("inner_selection_model_coverage_mismatch")
    selected_path = results_dir / "selected_configurations.csv"
    if selected_path.is_file():
        selected = pd.read_csv(selected_path)
        if len(selected) != 10:
            failures.append("selected_configuration_row_count_mismatch")
        if selected.duplicated(["model_id", "outer_fold"]).any():
            failures.append("duplicate_selected_configuration")
    availability_path = results_dir / "model_availability_audit.json"
    if availability_path.is_file():
        availability = json.loads(availability_path.read_text(encoding="utf-8"))
        if availability.get("status") != "PASS":
            failures.append("model_availability_not_pass")
        if availability.get("E3_prediction_rows") != 0:
            failures.append("E3_prediction_policy_violation")
    execution_path = results_dir / "execution_audit.json"
    contract_path = results_dir / "execution_contract_frozen.json"
    if execution_path.is_file() and contract_path.is_file():
        execution = json.loads(execution_path.read_text(encoding="utf-8"))
        if execution.get("contract_sha256") != sha256(contract_path):
            failures.append("execution_contract_hash_mismatch")
        if execution.get("locked_stage_outcomes_accessed") is not False:
            failures.append("locked_stage_access_audit_failure")
        if execution.get("final_model_selected") is not False:
            failures.append("final_model_selection_policy_violation")
    checkpoint_dir = results_dir / "fold_checkpoints"
    for outer_fold in range(5):
        for model_id in MODELS:
            checkpoint = checkpoint_dir / f"{model_id}_fold{outer_fold}.json"
            if not checkpoint.is_file():
                failures.append(f"missing_fold_checkpoint:{model_id}:{outer_fold}")
                continue
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            for suffix, key in (
                ("predictions.csv", "predictions_sha256"),
                ("inner_selection.csv", "inner_sha256"),
                ("selected_configuration.json", "selected_sha256"),
            ):
                target = checkpoint_dir / f"{model_id}_fold{outer_fold}_{suffix}"
                if not target.is_file() or saved.get(key) != sha256(target):
                    failures.append(f"invalid_fold_checkpoint:{model_id}:{outer_fold}:{suffix}")
    audit = {
        "status": "PASS" if not failures else "FAIL",
        "validated_at_utc": utc_now(),
        "failures": failures,
        "expected_pairs": 445,
        "expected_models": list(MODELS),
        "expected_prediction_rows": 890,
        "expected_inner_selection_rows": 400,
        "expected_selected_configuration_rows": 10,
        "E3_expected_prediction_rows": 0,
    }
    if write:
        write_json(results_dir / "validation_audit.json", audit)
    return audit


def write_checksums(root: Path) -> None:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"CHECKSUMS.sha256", "PF_ERI_TASK15G_FINAL_EXPORT.zip"}
    )
    (root / "CHECKSUMS.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files),
        encoding="utf-8",
    )


def export_results(results_dir: Path, zip_path: Path) -> dict[str, Any]:
    validation = validate_results(results_dir)
    if validation["status"] != "PASS":
        raise RuntimeError(f"validation_failed:{validation['failures']}")
    write_checksums(results_dir)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in results_dir.rglob("*") if item.is_file()):
            archive.write(
                path,
                arcname=f"PF_ERI_TASK15G_RESULTS/{path.relative_to(results_dir)}",
            )
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"bad_export_member:{bad}")
        member_count = len(archive.namelist())
    summary_path = zip_path.with_name("PF_ERI_TASK15G_RUN_SUMMARY.txt")
    summary_path.write_text(
        "status=COMPLETE\n"
        f"final_export_sha256={sha256(zip_path)}\n"
        f"final_export_size_bytes={zip_path.stat().st_size}\n"
        f"final_export_members={member_count}\n",
        encoding="utf-8",
    )
    return {
        "status": "PASS",
        "zip": str(zip_path),
        "zip_sha256": sha256(zip_path),
        "member_count": member_count,
        "run_summary": str(summary_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument(
        "--package-root", type=Path, default=Path(__file__).resolve().parent
    )
    smoke_parser.add_argument("--output-dir", type=Path, required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument(
        "--package-root", type=Path, default=Path(__file__).resolve().parent
    )
    run_parser.add_argument("--output-dir", type=Path, required=True)
    run_parser.add_argument("--smoke-audit", type=Path, required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--results-dir", type=Path, required=True)
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--results-dir", type=Path, required=True)
    export_parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "smoke":
            result = smoke(args.package_root.resolve(), args.output_dir.resolve())
        elif args.command == "run":
            result = run(
                args.package_root.resolve(),
                args.output_dir.resolve(),
                args.smoke_audit.resolve(),
            )
        elif args.command == "validate":
            result = validate_results(args.results_dir.resolve())
        else:
            result = export_results(args.results_dir.resolve(), args.zip.resolve())
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
                indent=2,
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS", "RUN_COMPLETE_PENDING_VALIDATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
