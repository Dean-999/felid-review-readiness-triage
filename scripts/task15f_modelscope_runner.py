#!/usr/bin/env python3
"""PF-ERI v2 Task 15F Bayesian/Firth ModelScope CPU execution runner."""
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
from typing import Any

import numpy as np
import pandas as pd
from numpy.polynomial.hermite import hermgauss
from scipy.linalg import qr
from scipy.optimize import brentq

try:
    from pferi_v2_fold_preprocessor import fit_fold_preprocessor, load_contract
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pferi_v2_fold_preprocessor import fit_fold_preprocessor, load_contract


MODELS = ["S3", "S4"]
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


def logistic(value: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(np.asarray(value, dtype=float), -36.0, 36.0)))


def training_weights(probability: np.ndarray) -> np.ndarray:
    raw = 1.0 / np.sqrt(np.asarray(probability, dtype=float))
    if np.any(~np.isfinite(raw)) or np.any(raw <= 0): raise ValueError("invalid training inclusion probability")
    return raw / raw.mean()


def evaluation_weights(probability: np.ndarray) -> np.ndarray:
    raw = 1.0 / np.asarray(probability, dtype=float)
    if np.any(~np.isfinite(raw)) or np.any(raw <= 0): raise ValueError("invalid evaluation inclusion probability")
    return raw / raw.mean()


def gauss_hermite_marginal_probability(eta: np.ndarray, sigma_image: np.ndarray, nodes: int = 20) -> np.ndarray:
    """Integrate two unseen N(0,sigma^2) endpoint effects for each draw."""
    eta = np.asarray(eta, dtype=float)
    sigma_image = np.asarray(sigma_image, dtype=float)
    if eta.ndim != 2 or sigma_image.shape != (eta.shape[0],): raise ValueError("invalid Gauss-Hermite input shapes")
    if np.any(sigma_image < 0) or not np.isfinite(eta).all() or not np.isfinite(sigma_image).all(): raise ValueError("invalid Gauss-Hermite values")
    node, weight = hermgauss(nodes)
    # Sum of two N(0,sigma^2) effects has sd sqrt(2)*sigma. Hermite's
    # standard-normal transform contributes another sqrt(2), hence 2*sigma*x.
    shifted = eta[:, :, None] + 2.0 * sigma_image[:, None, None] * node[None, None, :]
    return np.sum(logistic(shifted) * weight[None, None, :], axis=2) / math.sqrt(math.pi)


def _firth_penalized_loglik(design: np.ndarray, outcome: np.ndarray, weights: np.ndarray, beta: np.ndarray) -> float:
    eta = design @ beta; probability = logistic(eta)
    loglik = np.sum(weights * (outcome * np.log(np.clip(probability, EPS, 1)) + (1 - outcome) * np.log(np.clip(1 - probability, EPS, 1))))
    fisher = design.T @ ((weights * probability * (1 - probability))[:, None] * design)
    sign, logdet = np.linalg.slogdet(fisher)
    return float(loglik + 0.5 * logdet) if sign > 0 and np.isfinite(logdet) else -np.inf


def fit_firth_flic(design: np.ndarray, outcome: np.ndarray, weights: np.ndarray, max_iter: int = 500, tolerance: float = 1e-9) -> dict[str, Any]:
    design = np.asarray(design, float); outcome = np.asarray(outcome, float); weights = np.asarray(weights, float)
    if design.ndim != 2 or design.shape[0] != len(outcome) or len(outcome) != len(weights): raise ValueError("invalid Firth shapes")
    if set(np.unique(outcome)) != {0.0, 1.0}: raise RuntimeError("one_class_Firth_training")
    beta = np.zeros(design.shape[1]); converged = False; iteration = 0
    for iteration in range(1, max_iter + 1):
        probability = logistic(design @ beta)
        working = weights * probability * (1 - probability)
        fisher = design.T @ (working[:, None] * design)
        inverse = np.linalg.pinv(fisher, rcond=1e-12)
        leverage = working * np.sum((design @ inverse) * design, axis=1)
        score = design.T @ (weights * (outcome - probability) + leverage * (0.5 - probability))
        step = inverse @ score
        current = _firth_penalized_loglik(design, outcome, weights, beta)
        scale = 1.0
        while scale >= 2 ** -20:
            candidate = beta + scale * step
            if _firth_penalized_loglik(design, outcome, weights, candidate) >= current: break
            scale *= 0.5
        beta = candidate
        if np.max(np.abs(scale * step)) < tolerance:
            converged = True; break
    if not converged or not np.isfinite(beta).all(): raise RuntimeError("Firth_optimizer_nonconvergence")
    slopes = beta[1:].copy(); target = float(np.average(outcome, weights=weights))
    def calibration(intercept: float) -> float:
        return float(np.average(logistic(intercept + design[:, 1:] @ slopes), weights=weights) - target)
    beta[0] = brentq(calibration, -50.0, 50.0)
    return {"success": True, "coef": beta, "iterations": iteration, "weighted_training_prevalence": target}


def independent_columns(design_frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    varying = design_frame.std(axis=0, ddof=0) >= 1e-12
    reduced = design_frame.loc[:, varying]
    matrix = np.column_stack([np.ones(len(reduced)), reduced.to_numpy(float)])
    _, r, pivots = qr(matrix, mode="economic", pivoting=True)
    rank = int(np.sum(np.abs(np.diag(r)) > np.max(np.abs(np.diag(r))) * 1e-10))
    selected = sorted(int(i) for i in pivots[:rank] if int(i) != 0)
    columns = [reduced.columns[index - 1] for index in selected]
    return reduced.loc[:, columns], columns


def verify_manifest(root: Path) -> None:
    manifest = root / "PACKAGE_MANIFEST.sha256"
    if not manifest.is_file(): raise RuntimeError("missing_package_manifest")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1); target = root / relative
        if not target.is_file() or sha256(target) != expected: raise RuntimeError(f"package_hash_mismatch:{relative}")


def load_inputs(root: Path) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    verify_manifest(root)
    contract_path = root / "contracts/task15f_bayesian_sensitivity_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    paths = {
        "development_modeling_input.csv": root / "inputs/development_modeling_input.csv",
        "outer_fold_assignments.csv": root / "inputs/outer_fold_assignments.csv",
        "feature_preprocessing_contract.json": root / "contracts/feature_preprocessing_contract.json",
        "fold_preprocessor.py": root / "pferi_v2_fold_preprocessor.py",
        "task15e_development_disposition.json": root / "audits/task15e_development_disposition.json",
    }
    failures = [name for name, path in paths.items() if sha256(path) != contract["authoritative_inputs"][name]]
    if failures: raise RuntimeError(f"authoritative_input_hash_mismatch:{failures}")
    data = pd.read_csv(paths["development_modeling_input.csv"])
    folds = pd.read_csv(paths["outer_fold_assignments.csv"])
    frame = data.merge(folds[["canonical_pair_id", "component_id", "outer_fold"]], on="canonical_pair_id", validate="one_to_one")
    if len(frame) != 445 or frame["canonical_pair_id"].nunique() != 445: raise RuntimeError("development_pair_count_mismatch")
    if set(frame["formal_sampling_stage"].astype(str)) != {"development"}: raise RuntimeError("locked_stage_input_detected")
    if frame.groupby("component_id")["outer_fold"].nunique().max() != 1: raise RuntimeError("component_fold_leakage")
    preprocessing = load_contract(paths["feature_preprocessing_contract.json"])
    return frame, contract, preprocessing


def fold_design(frame: pd.DataFrame, preprocessing: dict[str, Any], outer_fold: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Any]:
    train = frame.loc[frame["outer_fold"] != outer_fold].copy(); test = frame.loc[frame["outer_fold"] == outer_fold].copy()
    fitted = fit_fold_preprocessor(train, preprocessing, ["descriptor", "independent_quality", "pair_evidence"])
    x_train, x_test = fitted.transform(train), fitted.transform(test)
    return train, test, x_train, x_test, fitted


def build_pymc_model(model_id: str, train: pd.DataFrame, x_train: pd.DataFrame, contract: dict[str, Any]):
    import pymc as pm
    coords: dict[str, Any] = {"observation": np.arange(len(train)), "predictor": list(x_train.columns)}
    endpoint_index = None
    if model_id == "S4":
        endpoints = sorted(set(train["endpoint_a_image_id"]) | set(train["endpoint_b_image_id"]))
        lookup = {value: index for index, value in enumerate(endpoints)}
        endpoint_index = (train["endpoint_a_image_id"].map(lookup).to_numpy(int), train["endpoint_b_image_id"].map(lookup).to_numpy(int))
        coords["endpoint"] = endpoints
    weights = training_weights(train["first_order_inclusion_probability"].to_numpy(float))
    outcome = train["review_ready_label"].to_numpy(int)
    with pm.Model(coords=coords) as model:
        alpha = pm.StudentT("alpha", nu=3, mu=0, sigma=2.5)
        beta = pm.Normal("beta", mu=0, sigma=0.5, dims="predictor")
        eta = alpha + pm.math.dot(x_train.to_numpy(float), beta)
        if model_id == "S4":
            sigma_image = pm.HalfNormal("sigma_image", sigma=0.5)
            image_offset = pm.Normal("image_offset", mu=0, sigma=1, dims="endpoint")
            eta = eta + sigma_image * image_offset[endpoint_index[0]] + sigma_image * image_offset[endpoint_index[1]]
        pm.Deterministic("p_train", pm.math.sigmoid(eta), dims="observation")
        logp = pm.logp(pm.Bernoulli.dist(logit_p=eta), outcome)
        pm.Potential("weighted_log_likelihood", pm.math.sum(weights * logp))
    return model


def prior_predictive_check(model: Any, model_id: str, fold: int, draws: int, seed: int) -> dict[str, Any]:
    import pymc as pm
    with model:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            prior = pm.sample_prior_predictive(draws=draws, var_names=["p_train"], random_seed=seed)
    values = np.asarray(prior.prior["p_train"]).reshape(-1, prior.prior["p_train"].shape[-1])
    failures = []
    if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)): failures.append("invalid_prior_probability")
    if not np.any(values < 0.5) or not np.any(values > 0.5): failures.append("prior_predictive_does_not_support_both_classes")
    return {"model_id": model_id, "outer_fold": fold, "draws": draws, "minimum_probability": float(values.min()), "maximum_probability": float(values.max()), "fraction_below_half": float(np.mean(values < 0.5)), "fraction_above_half": float(np.mean(values > 0.5)), "failures": failures, "status": "PASS" if not failures else "FAIL"}


def posterior_arrays(idata: Any, model_id: str) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    posterior = idata.posterior
    alpha = posterior["alpha"].stack(sample=("chain", "draw")).transpose("sample").values
    beta = posterior["beta"].stack(sample=("chain", "draw")).transpose("sample", "predictor").values
    sigma = None
    if model_id == "S4": sigma = posterior["sigma_image"].stack(sample=("chain", "draw")).transpose("sample").values
    return np.asarray(alpha), np.asarray(beta), None if sigma is None else np.asarray(sigma)


def diagnose_posterior(idata: Any, model_id: str, contract: dict[str, Any]) -> tuple[dict[str, Any], pd.DataFrame]:
    import arviz as az
    main_variables = ["alpha", "beta"] + (["sigma_image"] if model_id == "S4" else [])
    summary = az.summary(idata, var_names=main_variables, kind="all", round_to="none").reset_index(names="parameter")
    divergences = int(np.asarray(idata.sample_stats["diverging"]).sum())
    gate = contract["convergence_gates"]; failures = []
    if divergences != gate["post_tuning_divergences"]: failures.append("divergences")
    if float(summary["r_hat"].max()) > gate["fixed_effect_and_sigma_max_rank_normalized_rhat"]: failures.append("fixed_parameter_rhat")
    if float(summary["ess_bulk"].min()) < gate["fixed_effect_and_sigma_min_bulk_ess"]: failures.append("fixed_parameter_bulk_ess")
    if float(summary["ess_tail"].min()) < gate["fixed_effect_and_sigma_min_tail_ess"]: failures.append("fixed_parameter_tail_ess")
    offset_diagnostics = None
    if model_id == "S4":
        offsets = az.summary(idata, var_names=["image_offset"], kind="diagnostics", round_to="none")
        offset_diagnostics = {"max_rhat": float(offsets["r_hat"].max()), "p01_bulk_ess": float(offsets["ess_bulk"].quantile(0.01)), "p01_tail_ess": float(offsets["ess_tail"].quantile(0.01))}
        if offset_diagnostics["max_rhat"] > gate["S4_image_offset_max_rhat"]: failures.append("image_offset_rhat")
        if offset_diagnostics["p01_bulk_ess"] < gate["S4_image_offset_first_percentile_bulk_ess"]: failures.append("image_offset_bulk_ess")
        if offset_diagnostics["p01_tail_ess"] < gate["S4_image_offset_first_percentile_tail_ess"]: failures.append("image_offset_tail_ess")
    result = {"status": "PASS" if not failures else "FAIL", "model_id": model_id, "divergences": divergences, "failures": failures, "fixed_max_rhat": float(summary["r_hat"].max()), "fixed_min_bulk_ess": float(summary["ess_bulk"].min()), "fixed_min_tail_ess": float(summary["ess_tail"].min()), "image_offset_diagnostics": offset_diagnostics}
    return result, summary


def sample_fold(model: Any, model_id: str, fold: int, contract: dict[str, Any], retry: bool = False):
    import pymc as pm
    spec = contract["mcmc"]; model_index = MODELS.index(model_id) + 1
    seeds = [150100 + 100 * fold + 10 * model_index + chain for chain in range(spec["chains"])]
    tune = 3000 if retry else spec["tune_draws_per_chain"]; target = 0.99 if retry else spec["target_accept"]
    with model:
        idata = pm.sample(
            draws=spec["posterior_draws_per_chain"], tune=tune, chains=spec["chains"], cores=min(spec["chains"], os.cpu_count() or 1),
            random_seed=seeds, target_accept=target, nuts_sampler="nutpie", nuts={"max_treedepth": spec["maximum_tree_depth"]},
            progressbar=True, compute_convergence_checks=False,
        )
    return idata


def prediction_rows(idata: Any, model_id: str, fold: int, test: pd.DataFrame, x_test: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    alpha, beta, sigma = posterior_arrays(idata, model_id)
    eta = alpha[:, None] + beta @ x_test.to_numpy(float).T
    marginal_audit = None
    if model_id == "S4":
        draws = gauss_hermite_marginal_probability(eta, sigma, nodes=20)
        marginal_audit = {"model_id": model_id, "outer_fold": fold, "quadrature_nodes": 20, "posterior_draws": len(alpha), "two_unseen_endpoint_variance_rule": "2*sigma_image^2", "minimum_draw_probability": float(draws.min()), "maximum_draw_probability": float(draws.max()), "status": "PASS"}
    else: draws = logistic(eta)
    mean = draws.mean(axis=0); lower, upper = np.quantile(draws, [0.025, 0.975], axis=0)
    rows = []
    for (_, row), value, lo, hi in zip(test.iterrows(), mean, lower, upper):
        rows.append({"canonical_pair_id": row["canonical_pair_id"], "pair_execution_id": row["pair_execution_id"], "component_id": row["component_id"], "outer_fold": fold, "model_id": model_id, "review_ready_label": int(row["review_ready_label"]), "first_order_inclusion_probability": float(row["first_order_inclusion_probability"]), "posterior_mean_probability": float(value), "posterior_probability_lower_95": float(lo), "posterior_probability_upper_95": float(hi), "brier_loss": float((row["review_ready_label"] - value) ** 2)})
    return rows, marginal_audit


def parameter_rows(idata: Any, model_id: str, fold: int, feature_names: list[str]) -> list[dict[str, Any]]:
    alpha, beta, sigma = posterior_arrays(idata, model_id); rows = []
    def add(name: str, values: np.ndarray):
        rows.append({"model_id": model_id, "outer_fold": fold, "parameter": name, "mean": float(np.mean(values)), "sd": float(np.std(values, ddof=1)), "lower_95": float(np.quantile(values, 0.025)), "upper_95": float(np.quantile(values, 0.975)), "posterior_probability_gt_zero": float(np.mean(values > 0))})
    add("alpha", alpha)
    for index, name in enumerate(feature_names): add(name, beta[:, index])
    if sigma is not None: add("sigma_image", sigma)
    return rows


def metric_row(frame: pd.DataFrame) -> dict[str, Any]:
    y = frame["review_ready_label"].to_numpy(float); p = frame["posterior_mean_probability"].to_numpy(float); w = evaluation_weights(frame["first_order_inclusion_probability"].to_numpy(float))
    return {"pair_count": len(frame), "weighted_brier": float(np.average((y - p) ** 2, weights=w)), "weighted_log_loss": float(np.average(-(y * np.log(np.clip(p, EPS, 1)) + (1 - y) * np.log(np.clip(1 - p, EPS, 1))), weights=w)), "minimum_probability": float(p.min()), "maximum_probability": float(p.max())}


def run_firth_diagnostic(frame: pd.DataFrame, preprocessing: dict[str, Any], trigger_audit: dict[str, Any]) -> pd.DataFrame:
    rows = []
    triggered = {int(row["outer_fold"]) for row in trigger_audit["folds"] if row["triggered"]}
    for fold in sorted(triggered):
        train, test, x_train, x_test, _ = fold_design(frame, preprocessing, fold)
        reduced_train, columns = independent_columns(x_train); reduced_test = x_test.loc[:, columns]
        design_train = np.column_stack([np.ones(len(train)), reduced_train.to_numpy(float)])
        fit = fit_firth_flic(design_train, train["review_ready_label"].to_numpy(float), training_weights(train["first_order_inclusion_probability"].to_numpy(float)))
        probability = logistic(np.column_stack([np.ones(len(test)), reduced_test.to_numpy(float)]) @ fit["coef"])
        for (_, row), value in zip(test.iterrows(), probability):
            rows.append({"canonical_pair_id": row["canonical_pair_id"], "outer_fold": fold, "model_id": "S5_FLIC_DIAGNOSTIC_ONLY", "posterior_or_prediction_probability": float(value), "review_ready_label": int(row["review_ready_label"]), "selection_eligible": False, "fit_iterations": fit["iterations"], "retained_design_columns": len(columns)})
    return pd.DataFrame(rows)


def smoke(package_root: Path, output_dir: Path) -> dict[str, Any]:
    started = time.time(); output_dir.mkdir(parents=True, exist_ok=True)
    frame, contract, preprocessing = load_inputs(package_root)
    runtime = import_runtime_versions(contract)
    checks = []
    train, _, x_train, _, _ = fold_design(frame, preprocessing, 0)
    for index, model_id in enumerate(MODELS):
        model = build_pymc_model(model_id, train, x_train, contract)
        checks.append(prior_predictive_check(model, model_id, 0, contract["prior_predictive_gate"]["draws"], contract["prior_predictive_gate"]["seed"] + index))
    gh = gauss_hermite_marginal_probability(np.zeros((2, 3)), np.array([0.0, 1.0]), 20)
    failures = [f"prior:{row['model_id']}" for row in checks if row["status"] != "PASS"]
    if not np.allclose(gh, 0.5, atol=1e-12): failures.append("gauss_hermite_identity")
    audit = {"status": "PASS" if not failures else "FAIL", "created_at_utc": utc_now(), "runtime_seconds": time.time() - started, "runtime": runtime, "prior_predictive_checks": checks, "gauss_hermite_zero_logit_check": gh.tolist(), "failures": failures, "package_manifest_sha256": sha256(package_root / "PACKAGE_MANIFEST.sha256")}
    write_json(output_dir / "smoke_audit.json", audit); return audit


def import_runtime_versions(contract: dict[str, Any]) -> dict[str, Any]:
    if sys.version_info[:2] != (3, 12): raise RuntimeError(f"Python 3.12 required, found {sys.version.split()[0]}")
    import arviz as az, h5netcdf, pymc as pm, nutpie
    if pm.__version__ != contract["mcmc"]["pymc"]: raise RuntimeError(f"PyMC version mismatch:{pm.__version__}")
    return {"python": sys.version, "pymc": pm.__version__, "arviz": az.__version__, "nutpie": getattr(nutpie, "__version__", "unknown"), "h5netcdf": h5netcdf.__version__, "numpy": np.__version__, "pandas": pd.__version__, "platform": platform.platform(), "cpu_count": os.cpu_count()}


def run(package_root: Path, output_dir: Path, smoke_audit_path: Path) -> dict[str, Any]:
    smoke_audit = json.loads(smoke_audit_path.read_text(encoding="utf-8"))
    if smoke_audit.get("status") != "PASS": raise RuntimeError("mandatory_smoke_gate_not_passed")
    started = time.time(); output_dir.mkdir(parents=True, exist_ok=True)
    frame, contract, preprocessing = load_inputs(package_root); runtime = import_runtime_versions(contract)
    if smoke_audit.get("package_manifest_sha256") != sha256(package_root / "PACKAGE_MANIFEST.sha256"): raise RuntimeError("smoke_package_hash_mismatch")
    posterior_dir = output_dir / "posterior_samples"; checkpoint_dir = output_dir / "fold_checkpoints"; posterior_dir.mkdir(exist_ok=True); checkpoint_dir.mkdir(exist_ok=True)
    prediction_records: list[dict[str, Any]] = []; parameter_records: list[dict[str, Any]] = []; diagnostic_records: list[dict[str, Any]] = []; prior_records: list[dict[str, Any]] = []; marginal_records: list[dict[str, Any]] = []
    import arviz as az
    for fold in range(5):
        train, test, x_train, x_test, fitted = fold_design(frame, preprocessing, fold)
        for model_id in MODELS:
            checkpoint = checkpoint_dir / f"{model_id}_fold{fold}.json"; predictions_csv = checkpoint_dir / f"{model_id}_fold{fold}_predictions.csv"; parameters_csv = checkpoint_dir / f"{model_id}_fold{fold}_parameters.csv"
            if checkpoint.is_file() and predictions_csv.is_file() and parameters_csv.is_file():
                saved = json.loads(checkpoint.read_text());
                accepted_posterior = output_dir / saved.get("accepted_posterior_file", "")
                valid_checkpoint = (
                    saved.get("checkpoint_version") == "pferi_v2_task15f_fold_checkpoint_v1"
                    and saved.get("status") == "PASS"
                    and saved.get("contract_sha256") == sha256(package_root / "contracts/task15f_bayesian_sensitivity_contract.json")
                    and saved.get("preprocessor_sha256") == fitted.sha256
                    and saved.get("predictions_sha256") == sha256(predictions_csv)
                    and saved.get("parameters_sha256") == sha256(parameters_csv)
                    and accepted_posterior.is_file()
                    and saved.get("accepted_posterior_sha256") == sha256(accepted_posterior)
                )
                if not valid_checkpoint: raise RuntimeError(f"invalid_checkpoint:{model_id}:{fold}")
                prediction_records.extend(pd.read_csv(predictions_csv).to_dict("records")); parameter_records.extend(pd.read_csv(parameters_csv).to_dict("records")); diagnostic_records.append(saved["diagnostics"]); prior_records.append(saved["prior_predictive"])
                if saved.get("marginalization"): marginal_records.append(saved["marginalization"])
                continue
            model = build_pymc_model(model_id, train, x_train, contract)
            prior = prior_predictive_check(model, model_id, fold, contract["prior_predictive_gate"]["draws"], contract["prior_predictive_gate"]["seed"] + 10 * fold + MODELS.index(model_id))
            if prior["status"] != "PASS": raise RuntimeError(f"prior_predictive_gate_failed:{model_id}:{fold}")
            idata = sample_fold(model, model_id, fold, contract, retry=False); diagnostics, summary = diagnose_posterior(idata, model_id, contract)
            attempt1 = posterior_dir / f"{model_id}_fold{fold}_attempt1.nc"; idata.to_netcdf(attempt1)
            accepted_attempt = 1
            if diagnostics["status"] != "PASS":
                idata = sample_fold(model, model_id, fold, contract, retry=True); diagnostics, summary = diagnose_posterior(idata, model_id, contract); accepted_attempt = 2
                idata.to_netcdf(posterior_dir / f"{model_id}_fold{fold}_attempt2.nc")
            if diagnostics["status"] != "PASS": raise RuntimeError(f"posterior_convergence_failure:{model_id}:{fold}:{diagnostics['failures']}")
            rows, marginal = prediction_rows(idata, model_id, fold, test, x_test); params = parameter_rows(idata, model_id, fold, list(x_train.columns))
            pd.DataFrame(rows).to_csv(predictions_csv, index=False); pd.DataFrame(params).to_csv(parameters_csv, index=False)
            accepted_posterior = posterior_dir / f"{model_id}_fold{fold}_attempt{accepted_attempt}.nc"
            record = {"checkpoint_version": "pferi_v2_task15f_fold_checkpoint_v1", "status": "PASS", "model_id": model_id, "outer_fold": fold, "accepted_attempt": accepted_attempt, "contract_sha256": sha256(package_root / "contracts/task15f_bayesian_sensitivity_contract.json"), "preprocessor_sha256": fitted.sha256, "predictions_sha256": sha256(predictions_csv), "parameters_sha256": sha256(parameters_csv), "accepted_posterior_file": str(accepted_posterior.relative_to(output_dir)), "accepted_posterior_sha256": sha256(accepted_posterior), "diagnostics": {**diagnostics, "outer_fold": fold, "accepted_attempt": accepted_attempt}, "prior_predictive": prior, "marginalization": marginal}
            write_json(checkpoint, record)
            prediction_records.extend(rows); parameter_records.extend(params); diagnostic_records.append(record["diagnostics"]); prior_records.append(prior)
            if marginal: marginal_records.append(marginal)
    predictions = pd.DataFrame(prediction_records); parameters = pd.DataFrame(parameter_records); diagnostics = pd.DataFrame(diagnostic_records)
    predictions.to_csv(output_dir / "bayesian_oof_predictions.csv", index=False); parameters.to_csv(output_dir / "posterior_parameter_summary.csv", index=False); diagnostics.to_csv(output_dir / "posterior_diagnostics.csv", index=False)
    pair_evidence = parameters[parameters["parameter"].astype(str).str.startswith("local_match")].copy(); pair_evidence.to_csv(output_dir / "pair_evidence_posterior_summary.csv", index=False)
    write_json(output_dir / "prior_predictive_audit.json", {"status": "PASS", "checks": prior_records}); write_json(output_dir / "S4_marginalization_audit.json", {"status": "PASS", "checks": marginal_records})
    shutil.copy2(package_root / "audits/separation_trigger_audit.json", output_dir / "separation_trigger_audit.json")
    trigger = json.loads((package_root / "audits/separation_trigger_audit.json").read_text()); run_firth_diagnostic(frame, preprocessing, trigger).to_csv(output_dir / "firth_flic_diagnostic.csv", index=False)
    outer_rows=[]; overall_rows=[]
    for (model_id, fold), group in predictions.groupby(["model_id", "outer_fold"]): outer_rows.append({"model_id": model_id, "outer_fold": int(fold), **metric_row(group)})
    for model_id, group in predictions.groupby("model_id"): overall_rows.append({"model_id": model_id, **metric_row(group)})
    pd.DataFrame(outer_rows).to_csv(output_dir / "bayesian_outer_fold_metrics.csv", index=False); pd.DataFrame(overall_rows).to_csv(output_dir / "bayesian_overall_metrics.csv", index=False)
    report = "# PF-ERI Task 15F Bayesian Sensitivity\n\nThis development-only sensitivity run evaluates S3 weak-prior fixed effects and S4 crossed endpoint-image dependence. It does not select the final model and does not access locked-stage outcomes.\n"
    (output_dir / "TASK15F_SENSITIVITY_REPORT.md").write_text(report, encoding="utf-8")
    audit = {"status": "RUN_COMPLETE_PENDING_VALIDATION", "created_at_utc": utc_now(), "runtime_seconds": time.time() - started, "runtime": runtime, "prediction_rows": len(predictions), "posterior_fold_fits": len(diagnostics), "S5_status": trigger["S5_trigger_status"], "locked_stage_outcomes_accessed": False, "contract_sha256": sha256(package_root / "contracts/task15f_bayesian_sensitivity_contract.json")}
    write_json(output_dir / "execution_audit.json", audit); shutil.copy2(package_root / "contracts/task15f_bayesian_sensitivity_contract.json", output_dir / "execution_contract_frozen.json")
    return validate_results(output_dir)


def validate_results(results_dir: Path, write: bool = True) -> dict[str, Any]:
    failures=[]; required=["prior_predictive_audit.json","separation_trigger_audit.json","posterior_diagnostics.csv","posterior_parameter_summary.csv","bayesian_oof_predictions.csv","bayesian_outer_fold_metrics.csv","bayesian_overall_metrics.csv","pair_evidence_posterior_summary.csv","S4_marginalization_audit.json","firth_flic_diagnostic.csv","execution_audit.json","execution_contract_frozen.json","TASK15F_SENSITIVITY_REPORT.md"]
    for name in required:
        if not (results_dir/name).is_file(): failures.append(f"missing_required_output:{name}")
    path=results_dir/"bayesian_oof_predictions.csv"
    if path.is_file():
        frame=pd.read_csv(path); needed={"canonical_pair_id","model_id","posterior_mean_probability"}
        if not needed.issubset(frame.columns): failures.append("bayesian_prediction_schema_invalid")
        else:
            if len(frame)!=890: failures.append("bayesian_prediction_row_count_mismatch")
            if frame.duplicated(["canonical_pair_id","model_id"]).any(): failures.append("duplicate_bayesian_prediction")
            if frame["canonical_pair_id"].nunique()!=445: failures.append("bayesian_pair_coverage_mismatch")
            if set(frame["model_id"])!=set(MODELS): failures.append("bayesian_model_coverage_mismatch")
            p=pd.to_numeric(frame["posterior_mean_probability"],errors="coerce")
            if p.isna().any() or not p.between(0,1).all(): failures.append("invalid_bayesian_probability")
    diagnostics=results_dir/"posterior_diagnostics.csv"
    if diagnostics.is_file():
        d=pd.read_csv(diagnostics)
        if len(d)!=10 or set(d["status"])!={"PASS"}: failures.append("posterior_diagnostic_gate_failure")
    prior_path=results_dir/"prior_predictive_audit.json"
    if prior_path.is_file():
        prior=json.loads(prior_path.read_text(encoding="utf-8")); checks=prior.get("checks",[])
        if prior.get("status")!="PASS" or len(checks)!=10 or any(row.get("status")!="PASS" for row in checks): failures.append("prior_predictive_gate_failure")
    marginal_path=results_dir/"S4_marginalization_audit.json"
    if marginal_path.is_file():
        marginal=json.loads(marginal_path.read_text(encoding="utf-8")); checks=marginal.get("checks",[])
        if marginal.get("status")!="PASS" or len(checks)!=5 or any(row.get("quadrature_nodes")!=20 or row.get("status")!="PASS" for row in checks): failures.append("S4_marginalization_gate_failure")
    trigger_path=results_dir/"separation_trigger_audit.json"; firth_path=results_dir/"firth_flic_diagnostic.csv"
    if trigger_path.is_file() and firth_path.is_file():
        trigger=json.loads(trigger_path.read_text(encoding="utf-8")); expected={int(row["outer_fold"]) for row in trigger.get("folds",[]) if row.get("triggered")}
        firth=pd.read_csv(firth_path)
        if expected:
            found=set(pd.to_numeric(firth.get("outer_fold",pd.Series(dtype=float)),errors="coerce").dropna().astype(int))
            if found!=expected or firth.empty: failures.append("Firth_FLIC_triggered_fold_coverage_mismatch")
            if "selection_eligible" not in firth or firth["selection_eligible"].astype(str).str.lower().isin(["true","1"]).any(): failures.append("Firth_FLIC_selection_role_violation")
    contract_path=results_dir/"execution_contract_frozen.json"; execution_path=results_dir/"execution_audit.json"
    if contract_path.is_file() and execution_path.is_file():
        execution=json.loads(execution_path.read_text(encoding="utf-8"))
        if execution.get("contract_sha256")!=sha256(contract_path): failures.append("execution_contract_hash_mismatch")
        if execution.get("locked_stage_outcomes_accessed") is not False: failures.append("locked_stage_access_audit_failure")
    checkpoint_dir=results_dir/"fold_checkpoints"; posterior_dir=results_dir/"posterior_samples"
    for fold in range(5):
        for model_id in MODELS:
            checkpoint=checkpoint_dir/f"{model_id}_fold{fold}.json"
            if not checkpoint.is_file():
                failures.append(f"missing_fold_checkpoint:{model_id}:{fold}"); continue
            saved=json.loads(checkpoint.read_text(encoding="utf-8")); posterior=results_dir/saved.get("accepted_posterior_file","")
            predictions=checkpoint_dir/f"{model_id}_fold{fold}_predictions.csv"; parameters=checkpoint_dir/f"{model_id}_fold{fold}_parameters.csv"
            if saved.get("status")!="PASS" or not posterior.is_file() or saved.get("accepted_posterior_sha256")!=sha256(posterior): failures.append(f"invalid_accepted_posterior:{model_id}:{fold}")
            if not predictions.is_file() or saved.get("predictions_sha256")!=sha256(predictions): failures.append(f"invalid_checkpoint_predictions:{model_id}:{fold}")
            if not parameters.is_file() or saved.get("parameters_sha256")!=sha256(parameters): failures.append(f"invalid_checkpoint_parameters:{model_id}:{fold}")
    audit={"status":"PASS" if not failures else "FAIL","validated_at_utc":utc_now(),"failures":failures,"expected_pairs":445,"expected_models":MODELS,"expected_prediction_rows":890}
    if write: write_json(results_dir/"validation_audit.json",audit)
    return audit


def write_checksums(root: Path) -> None:
    files=sorted(p for p in root.rglob("*") if p.is_file() and p.name not in {"CHECKSUMS.sha256","PF_ERI_TASK15F_FINAL_EXPORT.zip"})
    (root/"CHECKSUMS.sha256").write_text("".join(f"{sha256(p)}  {p.relative_to(root)}\n" for p in files),encoding="utf-8")


def export_results(results_dir: Path, zip_path: Path) -> dict[str, Any]:
    validation=validate_results(results_dir)
    if validation["status"]!="PASS": raise RuntimeError(f"validation_failed:{validation['failures']}")
    write_checksums(results_dir)
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in results_dir.rglob("*") if p.is_file()): archive.write(path,arcname=f"PF_ERI_TASK15F_RESULTS/{path.relative_to(results_dir)}")
    return {"status":"PASS","zip":str(zip_path),"zip_sha256":sha256(zip_path),"member_count":len(zipfile.ZipFile(zip_path).namelist())}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("smoke");p.add_argument("--package-root",type=Path,default=Path(__file__).resolve().parent);p.add_argument("--output-dir",type=Path,required=True)
    p=sub.add_parser("run");p.add_argument("--package-root",type=Path,default=Path(__file__).resolve().parent);p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--smoke-audit",type=Path,required=True)
    p=sub.add_parser("validate");p.add_argument("--results-dir",type=Path,required=True)
    p=sub.add_parser("export");p.add_argument("--results-dir",type=Path,required=True);p.add_argument("--zip",type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.command=="smoke": result=smoke(args.package_root.resolve(),args.output_dir.resolve())
        elif args.command=="run": result=run(args.package_root.resolve(),args.output_dir.resolve(),args.smoke_audit.resolve())
        elif args.command=="validate": result=validate_results(args.results_dir.resolve())
        else: result=export_results(args.results_dir.resolve(),args.zip.resolve())
    except Exception as error:
        print(json.dumps({"status":"FAIL","error_type":type(error).__name__,"error":str(error)},indent=2));return 1
    print(json.dumps(result,indent=2,sort_keys=True));return 0 if result["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
