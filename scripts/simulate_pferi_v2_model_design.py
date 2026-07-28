#!/usr/bin/env python3
"""Run the PF-ERI v2 outcome-free model-design stress simulation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
from scipy.interpolate import BSpline
from scipy.optimize import minimize
from scipy.special import expit


ROOT = Path(__file__).resolve().parents[1]
SIMULATION_VERSION = "pferi_v2_model_design_simulation_v1"
REQUIRED_SCENARIOS = {
    "null_evidence_increment",
    "weak_linear_increment",
    "moderate_linear_increment",
    "smooth_nonlinear_increment",
    "descriptor_evidence_redundancy",
    "mechanism_interaction",
    "quasi_separation",
    "informative_matcher_failure",
    "shared_image_random_effect",
    "sampling_cell_calibration_shift",
}
REQUIRED_MASTER_COLUMNS = {
    "canonical_pair_id",
    "pair_execution_id",
    "analytical_role",
    "endpoint_a_image_id",
    "endpoint_b_image_id",
    "descriptor_support_category",
    "megadescriptor_within_role_percentile",
    "dinov2_within_role_percentile",
    "endpoint_native_pixel_quality_percentile_min",
    "endpoint_sharpness_quality_percentile_min",
    "endpoint_exposure_quality_percentile_min",
    "endpoint_quality_measurement_failure",
    "endpoint_frozen_quality_stress",
    "local_match_coverage_fraction",
    "local_match_measurement_failure",
    "development_sampling_cell_id",
}
REQUIRED_FORMAL_COLUMNS = {
    "formal_sampling_stage",
    "canonical_pair_id",
    "pair_execution_id",
    "source_analytical_role",
    "first_order_inclusion_probability",
}
OUTCOME_TOKENS = ("label", "outcome", "adjudicat", "review_ready", "not_ready")
ACTIVE_CONTINUOUS = [
    "megadescriptor_within_role_percentile",
    "dinov2_within_role_percentile",
    "endpoint_native_pixel_quality_percentile_min",
    "endpoint_sharpness_quality_percentile_min",
    "endpoint_exposure_quality_percentile_min",
]
FULL_CONTINUOUS = ACTIVE_CONTINUOUS + ["local_match_coverage_fraction"]
ACTIVE_CATEGORICAL = [
    "descriptor_support_category",
    "endpoint_quality_measurement_failure",
    "endpoint_frozen_quality_stress",
]
FULL_CATEGORICAL = ACTIVE_CATEGORICAL + ["local_match_measurement_failure"]


@dataclass(frozen=True)
class DesignMatrices:
    train_active: np.ndarray
    population_active: np.ndarray
    train_full: np.ndarray
    population_full: np.ndarray


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_dgp_registry(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "extends" not in raw:
        return raw
    base_path = path.parent / str(raw["extends"])
    if not base_path.exists():
        raise FileNotFoundError(f"extended DGP registry base is missing: {base_path}")
    base = json.loads(base_path.read_text(encoding="utf-8"))
    overrides = raw.get("overrides", {})
    if not isinstance(overrides, dict):
        raise ValueError("DGP registry overrides must be an object")
    base.update(overrides)
    base["registry_version"] = raw["registry_version"]
    base["extended_registry_base"] = base_path.name
    base["extended_registry_base_sha256"] = sha256_file(base_path)
    return base


def _label_like_columns(columns: Sequence[str]) -> list[str]:
    return sorted(
        column for column in columns
        if any(token in column.lower() for token in OUTCOME_TOKENS)
    )


def validate_dgp_registry(registry: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if registry.get("registry_version") not in {
        "pferi_v2_model_design_dgp_registry_v1",
        "pferi_v2_model_design_dgp_registry_v2",
    }:
        issues.append("unexpected DGP registry version")
    if registry.get("real_outcome_policy") != "PROHIBITED":
        issues.append("real outcomes must be prohibited")
    if int(registry.get("replicates_per_scenario", 0)) <= 0:
        issues.append("replicates_per_scenario must be positive")

    scenarios = registry.get("scenarios", [])
    scenario_ids = [str(row.get("scenario_id", "")) for row in scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        issues.append("duplicate scenario_id")
    missing = sorted(REQUIRED_SCENARIOS - set(scenario_ids))
    extra = sorted(set(scenario_ids) - REQUIRED_SCENARIOS)
    if missing:
        issues.append(f"missing required scenarios: {missing}")
    if extra:
        issues.append(f"unregistered scenarios: {extra}")
    for row in scenarios:
        prevalence = float(row.get("target_prevalence", -1))
        if not 0 < prevalence < 1:
            issues.append(f"invalid target prevalence for {row.get('scenario_id')}")
        if float(row.get("shared_image_sd", -1)) < 0:
            issues.append(f"invalid shared-image SD for {row.get('scenario_id')}")

    routes = registry.get("candidate_routes", [])
    route_ids = [str(row.get("route_id", "")) for row in routes]
    if len(route_ids) != len(set(route_ids)):
        issues.append("duplicate route_id")
    allowed_families = {"ridge_logistic", "restricted_spline_logistic"}
    allowed_weights = {"unweighted", "hajek_ipw", "sqrt_ipw"}
    for row in routes:
        if row.get("model_family") not in allowed_families:
            issues.append(f"unsupported model family for {row.get('route_id')}")
        if row.get("training_weight_strategy") not in allowed_weights:
            issues.append(f"unsupported weight strategy for {row.get('route_id')}")

    rule = registry.get("qualification_rule", {})
    selection_pool = set(rule.get("primary_weighting_selection_pool", []))
    if not selection_pool or not selection_pool <= set(route_ids):
        issues.append("invalid primary weighting selection pool")
    by_route = {str(row.get("route_id")): row for row in routes}
    if any(by_route.get(route, {}).get("model_family") != "ridge_logistic" for route in selection_pool):
        issues.append("primary weighting selection pool must contain ridge routes only")
    if rule.get("nonlinear_routes_cannot_replace_the_frozen_primary_family") is not True:
        issues.append("nonlinear routes must not be allowed to replace the frozen primary family")
    if registry.get("registry_version") == "pferi_v2_model_design_dgp_registry_v2":
        if not isinstance(registry.get("three_stage_design"), dict):
            issues.append("v2 DGP registry requires a three-stage design")
        if registry.get("qualification_probability_stage") != "post-independent-synthetic-calibration":
            issues.append("v2 qualification must use post-calibration probabilities")
    return issues


def load_outcome_free_inputs(master_path: Path, formal_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    master_header = pd.read_csv(master_path, nrows=0).columns.tolist()
    formal_header = pd.read_csv(formal_path, nrows=0).columns.tolist()
    contaminated = _label_like_columns(master_header) + _label_like_columns(formal_header)
    if contaminated:
        raise ValueError(f"outcome-like columns found in simulation inputs: {sorted(set(contaminated))}")
    missing_master = sorted(REQUIRED_MASTER_COLUMNS - set(master_header))
    missing_formal = sorted(REQUIRED_FORMAL_COLUMNS - set(formal_header))
    if missing_master or missing_formal:
        raise ValueError(f"missing required columns: master={missing_master} formal={missing_formal}")

    population = pd.read_csv(master_path, usecols=sorted(REQUIRED_MASTER_COLUMNS))
    formal = pd.read_csv(formal_path, usecols=sorted(REQUIRED_FORMAL_COLUMNS))
    population = population.loc[population["analytical_role"].astype(str) == "development"].copy()
    formal = formal.loc[
        (formal["formal_sampling_stage"].astype(str) == "development")
        & (formal["source_analytical_role"].astype(str) == "development")
    ].copy()
    if population["canonical_pair_id"].duplicated().any():
        raise ValueError("duplicate canonical_pair_id in development target population")
    if formal["canonical_pair_id"].duplicated().any():
        raise ValueError("duplicate canonical_pair_id in formal development sample")

    population = population.reset_index(drop=True)
    index_by_pair = dict(zip(population["canonical_pair_id"].astype(str), population.index))
    missing_pairs = sorted(set(formal["canonical_pair_id"].astype(str)) - set(index_by_pair))
    if missing_pairs:
        raise ValueError(f"formal development pairs absent from outcome-free population: {missing_pairs[:5]}")
    sample = formal[["canonical_pair_id", "first_order_inclusion_probability"]].merge(
        population,
        on="canonical_pair_id",
        how="left",
        validate="one_to_one",
        sort=False,
    )
    sample["_population_index"] = sample["canonical_pair_id"].astype(str).map(index_by_pair).astype(int)
    pi = pd.to_numeric(sample["first_order_inclusion_probability"], errors="coerce")
    if pi.isna().any() or (pi <= 0).any() or (pi > 1).any():
        raise ValueError("invalid first-order inclusion probabilities")
    sample["first_order_inclusion_probability"] = pi
    return population, sample


def load_three_stage_outcome_free_inputs(
    master_path: Path,
    formal_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    master_header = pd.read_csv(master_path, nrows=0).columns.tolist()
    formal_header = pd.read_csv(formal_path, nrows=0).columns.tolist()
    contaminated = _label_like_columns(master_header) + _label_like_columns(formal_header)
    if contaminated:
        raise ValueError(f"outcome-like columns found in simulation inputs: {sorted(set(contaminated))}")
    missing_master = sorted(REQUIRED_MASTER_COLUMNS - set(master_header))
    missing_formal = sorted(REQUIRED_FORMAL_COLUMNS - set(formal_header))
    if missing_master or missing_formal:
        raise ValueError(f"missing required columns: master={missing_master} formal={missing_formal}")

    population = pd.read_csv(master_path, usecols=sorted(REQUIRED_MASTER_COLUMNS)).reset_index(drop=True)
    formal = pd.read_csv(formal_path, usecols=sorted(REQUIRED_FORMAL_COLUMNS))
    expected_roles = {"development", "calibration", "confirmation"}
    observed_roles = set(population["analytical_role"].astype(str))
    if observed_roles != expected_roles:
        raise ValueError(f"three-stage master roles mismatch: {sorted(observed_roles)}")
    if population["canonical_pair_id"].duplicated().any():
        raise ValueError("duplicate canonical_pair_id in three-stage outcome-free population")
    index_by_pair = dict(zip(population["canonical_pair_id"].astype(str), population.index))

    def selected_sample(role: str) -> pd.DataFrame:
        selected = formal.loc[
            (formal["formal_sampling_stage"].astype(str) == role)
            & (formal["source_analytical_role"].astype(str) == role)
        ].copy()
        if selected["canonical_pair_id"].duplicated().any():
            raise ValueError(f"duplicate canonical_pair_id in formal {role} sample")
        role_population = population.loc[population["analytical_role"].astype(str) == role]
        missing_pairs = sorted(
            set(selected["canonical_pair_id"].astype(str))
            - set(role_population["canonical_pair_id"].astype(str))
        )
        if missing_pairs:
            raise ValueError(f"formal {role} pairs absent from role population: {missing_pairs[:5]}")
        sample = selected[["canonical_pair_id", "first_order_inclusion_probability"]].merge(
            role_population,
            on="canonical_pair_id",
            how="left",
            validate="one_to_one",
            sort=False,
        )
        sample["_population_index"] = sample["canonical_pair_id"].astype(str).map(index_by_pair).astype(int)
        pi = pd.to_numeric(sample["first_order_inclusion_probability"], errors="coerce")
        if pi.isna().any() or (pi <= 0).any() or (pi > 1).any():
            raise ValueError(f"invalid {role} inclusion probabilities")
        sample["first_order_inclusion_probability"] = pi
        return sample

    development = selected_sample("development")
    calibration = selected_sample("calibration")
    confirmation = population.loc[
        population["analytical_role"].astype(str) == "confirmation"
    ].copy()
    confirmation["_population_index"] = confirmation["canonical_pair_id"].astype(str).map(index_by_pair).astype(int)
    return population, development, calibration, confirmation


def training_weights(inclusion_probability: np.ndarray, strategy: str) -> np.ndarray:
    pi = np.asarray(inclusion_probability, dtype=float)
    if np.any(~np.isfinite(pi)) or np.any(pi <= 0) or np.any(pi > 1):
        raise ValueError("invalid inclusion probabilities")
    if strategy == "unweighted":
        weights = np.ones_like(pi)
    elif strategy == "hajek_ipw":
        weights = 1.0 / pi
    elif strategy == "sqrt_ipw":
        weights = np.sqrt(1.0 / pi)
    else:
        raise ValueError(f"unknown training weight strategy: {strategy}")
    return weights / weights.mean()


def _numeric(frame: pd.DataFrame, column: str, fill: float = 0.5) -> np.ndarray:
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
    if np.all(~np.isfinite(values)):
        return np.full(len(frame), fill, dtype=float)
    median = float(np.nanmedian(values))
    return np.where(np.isfinite(values), values, median)


def _boolean(frame: pd.DataFrame, column: str) -> np.ndarray:
    return frame[column].astype(str).str.lower().isin({"true", "1", "yes"}).to_numpy(dtype=float)


def _center_intercept(eta_without_intercept: np.ndarray, target: float) -> float:
    low, high = -20.0, 20.0
    for _ in range(80):
        mid = (low + high) / 2.0
        if float(expit(eta_without_intercept + mid).mean()) < target:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def synthetic_probability_pair(
    population: pd.DataFrame,
    scenario: dict[str, Any],
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    mega = _numeric(population, "megadescriptor_within_role_percentile")
    dino = _numeric(population, "dinov2_within_role_percentile")
    descriptor = (mega + dino) / 2.0
    quality = np.mean(
        np.column_stack(
            [
                _numeric(population, "endpoint_native_pixel_quality_percentile_min"),
                _numeric(population, "endpoint_sharpness_quality_percentile_min"),
                _numeric(population, "endpoint_exposure_quality_percentile_min"),
            ]
        ),
        axis=1,
    )
    local = _numeric(population, "local_match_coverage_fraction")
    quality_failure = _boolean(population, "endpoint_quality_measurement_failure")
    local_failure = _boolean(population, "local_match_measurement_failure")
    stress = (population["endpoint_frozen_quality_stress"].astype(str).str.lower() != "none").to_numpy(float)
    single_descriptor = (
        population["descriptor_support_category"].astype(str).str.lower() != "both"
    ).to_numpy(float)

    active_eta = (
        1.0 * (descriptor - 0.5)
        + 0.8 * (quality - 0.5)
        - 0.35 * quality_failure
        - 0.2 * stress
        - 0.15 * single_descriptor
    )
    mechanism = str(scenario["mechanism"])
    scale = float(scenario.get("evidence_scale", 0.0))
    evidence_eta = np.zeros(len(population), dtype=float)
    if mechanism == "linear_additive":
        evidence_eta = scale * 1.5 * (local - 0.5)
    elif mechanism == "smooth_nonlinear":
        evidence_eta = scale * (np.tanh(5.0 * (local - 0.5)) + 0.6 * ((local - 0.5) ** 2 - 1 / 12))
    elif mechanism == "redundant_evidence":
        evidence_eta = scale * 1.5 * (local - descriptor)
    elif mechanism == "quality_evidence_interaction":
        evidence_eta = scale * 6.0 * (local - 0.5) * (quality - 0.5)
    elif mechanism == "quasi_separation":
        evidence_eta = 4.5 * (descriptor + quality + local - 1.5)
    elif mechanism == "informative_matcher_failure":
        evidence_eta = scale * 1.5 * (local - 0.5) - 1.4 * local_failure
    elif mechanism == "sampling_cell_shift":
        cells = population["development_sampling_cell_id"].astype(str)
        cell_values = {cell: rng.normal(0.0, 0.8) for cell in sorted(cells.unique())}
        evidence_eta = scale * 1.5 * (local - 0.5) + cells.map(cell_values).to_numpy(float)
    else:
        raise ValueError(f"unknown DGP mechanism: {mechanism}")

    shared_sd = float(scenario.get("shared_image_sd", 0.0))
    shared_eta = np.zeros(len(population), dtype=float)
    if shared_sd > 0:
        image_ids = sorted(
            set(population["endpoint_a_image_id"].astype(str))
            | set(population["endpoint_b_image_id"].astype(str))
        )
        effects = {image_id: rng.normal(0.0, shared_sd) for image_id in image_ids}
        shared_eta = (
            population["endpoint_a_image_id"].astype(str).map(effects).to_numpy(float)
            + population["endpoint_b_image_id"].astype(str).map(effects).to_numpy(float)
        ) / math.sqrt(2.0)

    target = float(scenario["target_prevalence"])
    active_intercept = _center_intercept(active_eta, target)
    active_oracle = expit(active_eta + active_intercept)
    full_eta = active_eta + evidence_eta + shared_eta
    full_intercept = _center_intercept(full_eta, target)
    full_truth = expit(full_eta + full_intercept)
    return np.clip(full_truth, 1e-8, 1 - 1e-8), np.clip(active_oracle, 1e-8, 1 - 1e-8)


def synthetic_probabilities(
    population: pd.DataFrame,
    scenario: dict[str, Any],
    rng: np.random.Generator,
) -> np.ndarray:
    return synthetic_probability_pair(population, scenario, rng)[0]


def _continuous_design(
    train: pd.DataFrame,
    population: pd.DataFrame,
    columns: Sequence[str],
    *,
    spline: bool,
) -> tuple[np.ndarray, np.ndarray]:
    train_parts: list[np.ndarray] = []
    population_parts: list[np.ndarray] = []
    for column in columns:
        train_raw = pd.to_numeric(train[column], errors="coerce").to_numpy(float)
        population_raw = pd.to_numeric(population[column], errors="coerce").to_numpy(float)
        train_missing = (~np.isfinite(train_raw)).astype(float)[:, None]
        population_missing = (~np.isfinite(population_raw)).astype(float)[:, None]
        median = float(np.nanmedian(train_raw)) if np.any(np.isfinite(train_raw)) else 0.0
        train_filled = np.where(np.isfinite(train_raw), train_raw, median)
        population_filled = np.where(np.isfinite(population_raw), population_raw, median)
        if not spline:
            center = float(train_filled.mean())
            scale = float(train_filled.std()) or 1.0
            train_basis = ((train_filled - center) / scale)[:, None]
            population_basis = ((population_filled - center) / scale)[:, None]
        else:
            lower, upper = np.quantile(train_filled, [0.01, 0.99])
            if not np.isfinite(lower) or not np.isfinite(upper) or upper - lower < 1e-8:
                lower, upper = median - 0.5, median + 0.5
            internal = float(np.median(train_filled))
            internal = min(max(internal, lower + 1e-7), upper - 1e-7)
            degree = 2
            knots = np.array([lower] * 3 + [internal] + [upper] * 3, dtype=float)
            train_clip = np.clip(train_filled, lower, upper)
            population_clip = np.clip(population_filled, lower, upper)
            train_basis = BSpline.design_matrix(train_clip, knots, degree).toarray()
            population_basis = BSpline.design_matrix(population_clip, knots, degree).toarray()
            centers = train_basis.mean(axis=0)
            scales = train_basis.std(axis=0)
            scales[scales < 1e-8] = 1.0
            train_basis = (train_basis - centers) / scales
            population_basis = (population_basis - centers) / scales
        train_parts.extend([train_basis, train_missing])
        population_parts.extend([population_basis, population_missing])
    return np.column_stack(train_parts), np.column_stack(population_parts)


def _categorical_design(
    train: pd.DataFrame,
    population: pd.DataFrame,
    columns: Sequence[str],
) -> tuple[np.ndarray, np.ndarray]:
    train_parts: list[np.ndarray] = []
    population_parts: list[np.ndarray] = []
    for column in columns:
        train_values = train[column].fillna("__MISSING__").astype(str)
        population_values = population[column].fillna("__MISSING__").astype(str)
        levels = sorted(train_values.unique())
        reference = levels[0]
        modeled_levels = [level for level in levels if level != reference] + ["__UNKNOWN__"]
        known = set(levels)
        for level in modeled_levels:
            if level == "__UNKNOWN__":
                train_parts.append((~train_values.isin(known)).to_numpy(float)[:, None])
                population_parts.append((~population_values.isin(known)).to_numpy(float)[:, None])
            else:
                train_parts.append((train_values == level).to_numpy(float)[:, None])
                population_parts.append((population_values == level).to_numpy(float)[:, None])
    if not train_parts:
        return np.empty((len(train), 0)), np.empty((len(population), 0))
    return np.column_stack(train_parts), np.column_stack(population_parts)


def build_design_matrices(
    train: pd.DataFrame,
    population: pd.DataFrame,
    family: str,
) -> DesignMatrices:
    spline = family == "restricted_spline_logistic"
    if family not in {"ridge_logistic", "restricted_spline_logistic"}:
        raise ValueError(f"unknown model family: {family}")

    active_cont_train, active_cont_pop = _continuous_design(
        train, population, ACTIVE_CONTINUOUS, spline=spline
    )
    full_cont_train, full_cont_pop = _continuous_design(
        train, population, FULL_CONTINUOUS, spline=spline
    )
    active_cat_train, active_cat_pop = _categorical_design(
        train, population, ACTIVE_CATEGORICAL
    )
    full_cat_train, full_cat_pop = _categorical_design(
        train, population, FULL_CATEGORICAL
    )

    def assemble(continuous: np.ndarray, categorical: np.ndarray) -> np.ndarray:
        return np.column_stack([np.ones(len(continuous)), continuous, categorical])

    return DesignMatrices(
        assemble(active_cont_train, active_cat_train),
        assemble(active_cont_pop, active_cat_pop),
        assemble(full_cont_train, full_cat_train),
        assemble(full_cont_pop, full_cat_pop),
    )


def fit_ridge_logistic(
    design: np.ndarray,
    outcome: np.ndarray,
    weights: np.ndarray,
    *,
    penalty: float = 1.0,
) -> np.ndarray:
    x = np.asarray(design, dtype=float)
    y = np.asarray(outcome, dtype=float)
    w = np.asarray(weights, dtype=float)
    if x.ndim != 2 or len(x) != len(y) or len(y) != len(w):
        raise ValueError("incompatible design, outcome, and weight shapes")
    if len(np.unique(y)) < 2:
        raise ValueError("synthetic training outcome has only one class")

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        linear = x @ beta
        loss = float(np.sum(w * (np.logaddexp(0.0, linear) - y * linear)))
        gradient = x.T @ (w * (expit(linear) - y))
        loss += 0.5 * penalty * float(beta[1:] @ beta[1:])
        gradient[1:] += penalty * beta[1:]
        return loss, gradient

    result = minimize(
        objective,
        np.zeros(x.shape[1], dtype=float),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if not result.success or np.any(~np.isfinite(result.x)):
        raise RuntimeError(f"ridge logistic optimization failed: {result.message}")
    return result.x


def expected_probability_metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    p = np.clip(np.asarray(prediction, dtype=float), 1e-8, 1 - 1e-8)
    q = np.clip(np.asarray(truth, dtype=float), 1e-8, 1 - 1e-8)
    if p.shape != q.shape or np.any(~np.isfinite(p)) or np.any(~np.isfinite(q)):
        raise ValueError("invalid prediction or truth probability")
    brier_regret = float(np.mean((p - q) ** 2))
    log_loss = -np.mean(q * np.log(p) + (1 - q) * np.log(1 - p))
    entropy = -np.mean(q * np.log(q) + (1 - q) * np.log(1 - q))
    x = np.column_stack([np.ones(len(p)), np.log(p / (1 - p))])
    target = np.log(q / (1 - q))
    intercept, slope = np.linalg.lstsq(x, target, rcond=None)[0]
    return {
        "brier_regret": brier_regret,
        "log_loss_regret": float(log_loss - entropy),
        "calibration_intercept": float(intercept),
        "calibration_slope": float(slope),
    }


def fit_logistic_recalibrator(raw_prediction: np.ndarray, outcome: np.ndarray) -> np.ndarray:
    raw = np.clip(np.asarray(raw_prediction, dtype=float), 1e-8, 1 - 1e-8)
    design = np.column_stack([np.ones(len(raw)), np.log(raw / (1 - raw))])
    return fit_ridge_logistic(
        design,
        np.asarray(outcome, dtype=float),
        np.ones(len(raw), dtype=float),
        penalty=0.0,
    )


def apply_logistic_recalibrator(raw_prediction: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    raw = np.clip(np.asarray(raw_prediction, dtype=float), 1e-8, 1 - 1e-8)
    design = np.column_stack([np.ones(len(raw)), np.log(raw / (1 - raw))])
    return expit(design @ np.asarray(coefficients, dtype=float))


def _simulate_replicates(
    population: pd.DataFrame,
    sample: pd.DataFrame,
    registry: dict[str, Any],
    replicates: int,
) -> pd.DataFrame:
    matrices = {
        family: build_design_matrices(sample, population, family)
        for family in {row["model_family"] for row in registry["candidate_routes"]}
    }
    population_indices = sample["_population_index"].to_numpy(int)
    inclusion = sample["first_order_inclusion_probability"].to_numpy(float)
    rows: list[dict[str, Any]] = []
    base_seed = int(registry["simulation_seed"])
    for scenario_index, scenario in enumerate(registry["scenarios"]):
        for replicate in range(replicates):
            rng = np.random.default_rng(base_seed + scenario_index * 100_003 + replicate)
            truth, active_oracle = synthetic_probability_pair(population, scenario, rng)
            outcome = rng.binomial(1, truth[population_indices]).astype(float)
            oracle_increment = float(np.mean((active_oracle - truth) ** 2))
            for route in registry["candidate_routes"]:
                route_id = str(route["route_id"])
                family = str(route["model_family"])
                strategy = str(route["training_weight_strategy"])
                base = {
                    "scenario_id": scenario["scenario_id"],
                    "replicate": replicate,
                    "route_id": route_id,
                    "model_family": family,
                    "training_weight_strategy": strategy,
                    "synthetic_target_prevalence": float(truth.mean()),
                    "dgp_structural_oracle_increment": oracle_increment,
                    "real_outcome_used": False,
                }
                try:
                    weights = training_weights(inclusion, strategy)
                    design = matrices[family]
                    active_beta = fit_ridge_logistic(design.train_active, outcome, weights)
                    full_beta = fit_ridge_logistic(design.train_full, outcome, weights)
                    active_prediction = expit(design.population_active @ active_beta)
                    full_prediction = expit(design.population_full @ full_beta)
                    active_metrics = expected_probability_metrics(active_prediction, truth)
                    full_metrics = expected_probability_metrics(full_prediction, truth)
                    estimated_increment = (
                        active_metrics["brier_regret"] - full_metrics["brier_regret"]
                    )
                    false_promotion = bool(
                        scenario["scenario_id"] == "null_evidence_increment"
                        and estimated_increment
                        > float(registry["qualification_rule"]["false_promotion_threshold_brier"])
                    )
                    rows.append(
                        {
                            **base,
                            "fit_status": "success",
                            "failure_code": "",
                            "active_brier_regret": active_metrics["brier_regret"],
                            "full_brier_regret": full_metrics["brier_regret"],
                            "full_log_loss_regret": full_metrics["log_loss_regret"],
                            "full_calibration_intercept": full_metrics["calibration_intercept"],
                            "full_calibration_slope": full_metrics["calibration_slope"],
                            "estimated_paired_brier_increment": estimated_increment,
                            "false_evidence_promotion": false_promotion,
                        }
                    )
                except Exception as exc:  # per-route failures must not erase other routes
                    rows.append(
                        {
                            **base,
                            "fit_status": "failure",
                            "failure_code": type(exc).__name__,
                            "failure_message": str(exc),
                            "active_brier_regret": np.nan,
                            "full_brier_regret": np.nan,
                            "full_log_loss_regret": np.nan,
                            "full_calibration_intercept": np.nan,
                            "full_calibration_slope": np.nan,
                            "estimated_paired_brier_increment": np.nan,
                            "false_evidence_promotion": False,
                        }
                    )
    return pd.DataFrame(rows)


def _simulate_replicates_three_stage(
    population: pd.DataFrame,
    development_sample: pd.DataFrame,
    calibration_sample: pd.DataFrame,
    confirmation_population: pd.DataFrame,
    registry: dict[str, Any],
    replicates: int,
) -> pd.DataFrame:
    matrices = {
        family: build_design_matrices(development_sample, population, family)
        for family in {row["model_family"] for row in registry["candidate_routes"]}
    }
    development_indices = development_sample["_population_index"].to_numpy(int)
    calibration_indices = calibration_sample["_population_index"].to_numpy(int)
    confirmation_indices = confirmation_population["_population_index"].to_numpy(int)
    inclusion = development_sample["first_order_inclusion_probability"].to_numpy(float)
    rows: list[dict[str, Any]] = []
    base_seed = int(registry["simulation_seed"])
    for scenario_index, scenario in enumerate(registry["scenarios"]):
        for replicate in range(replicates):
            rng = np.random.default_rng(base_seed + scenario_index * 100_003 + replicate)
            truth, active_oracle = synthetic_probability_pair(population, scenario, rng)
            development_outcome = rng.binomial(1, truth[development_indices]).astype(float)
            calibration_outcome = rng.binomial(1, truth[calibration_indices]).astype(float)
            target_truth = truth[confirmation_indices]
            target_active_oracle = active_oracle[confirmation_indices]
            oracle_increment = float(np.mean((target_active_oracle - target_truth) ** 2))
            for route in registry["candidate_routes"]:
                route_id = str(route["route_id"])
                family = str(route["model_family"])
                strategy = str(route["training_weight_strategy"])
                base = {
                    "scenario_id": scenario["scenario_id"],
                    "replicate": replicate,
                    "route_id": route_id,
                    "model_family": family,
                    "training_weight_strategy": strategy,
                    "probability_stage": "post_independent_synthetic_calibration",
                    "synthetic_target_prevalence": float(target_truth.mean()),
                    "dgp_structural_oracle_increment": oracle_increment,
                    "real_outcome_used": False,
                }
                try:
                    weights = training_weights(inclusion, strategy)
                    design = matrices[family]
                    active_beta = fit_ridge_logistic(
                        design.train_active, development_outcome, weights
                    )
                    full_beta = fit_ridge_logistic(
                        design.train_full, development_outcome, weights
                    )
                    active_raw = expit(design.population_active @ active_beta)
                    full_raw = expit(design.population_full @ full_beta)
                    active_calibrator = fit_logistic_recalibrator(
                        active_raw[calibration_indices], calibration_outcome
                    )
                    full_calibrator = fit_logistic_recalibrator(
                        full_raw[calibration_indices], calibration_outcome
                    )
                    active_prediction = apply_logistic_recalibrator(
                        active_raw[confirmation_indices], active_calibrator
                    )
                    full_prediction = apply_logistic_recalibrator(
                        full_raw[confirmation_indices], full_calibrator
                    )
                    active_metrics = expected_probability_metrics(active_prediction, target_truth)
                    full_metrics = expected_probability_metrics(full_prediction, target_truth)
                    estimated_increment = (
                        active_metrics["brier_regret"] - full_metrics["brier_regret"]
                    )
                    false_promotion = bool(
                        scenario["scenario_id"] == "null_evidence_increment"
                        and estimated_increment
                        > float(registry["qualification_rule"]["false_promotion_threshold_brier"])
                    )
                    rows.append(
                        {
                            **base,
                            "fit_status": "success",
                            "failure_code": "",
                            "active_brier_regret": active_metrics["brier_regret"],
                            "full_brier_regret": full_metrics["brier_regret"],
                            "full_log_loss_regret": full_metrics["log_loss_regret"],
                            "full_calibration_intercept": full_metrics["calibration_intercept"],
                            "full_calibration_slope": full_metrics["calibration_slope"],
                            "estimated_paired_brier_increment": estimated_increment,
                            "false_evidence_promotion": false_promotion,
                        }
                    )
                except Exception as exc:
                    rows.append(
                        {
                            **base,
                            "fit_status": "failure",
                            "failure_code": type(exc).__name__,
                            "failure_message": str(exc),
                            "active_brier_regret": np.nan,
                            "full_brier_regret": np.nan,
                            "full_log_loss_regret": np.nan,
                            "full_calibration_intercept": np.nan,
                            "full_calibration_slope": np.nan,
                            "estimated_paired_brier_increment": np.nan,
                            "false_evidence_promotion": False,
                        }
                    )
    return pd.DataFrame(rows)


def summarize_simulation(
    metrics: pd.DataFrame,
    registry: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for (scenario_id, route_id), frame in metrics.groupby(["scenario_id", "route_id"], sort=True):
        success = frame.loc[frame["fit_status"] == "success"]
        summaries.append(
            {
                "scenario_id": scenario_id,
                "route_id": route_id,
                "replicate_count": len(frame),
                "fit_failure_count": int((frame["fit_status"] != "success").sum()),
                "fit_failure_rate": float((frame["fit_status"] != "success").mean()),
                "median_full_brier_regret": float(success["full_brier_regret"].median()) if len(success) else np.nan,
                "p90_full_brier_regret": float(success["full_brier_regret"].quantile(0.9)) if len(success) else np.nan,
                "median_full_log_loss_regret": float(success["full_log_loss_regret"].median()) if len(success) else np.nan,
                "median_calibration_intercept": float(success["full_calibration_intercept"].median()) if len(success) else np.nan,
                "median_calibration_slope": float(success["full_calibration_slope"].median()) if len(success) else np.nan,
                "median_estimated_paired_brier_increment": float(success["estimated_paired_brier_increment"].median()) if len(success) else np.nan,
                "median_dgp_structural_oracle_increment": float(success["dgp_structural_oracle_increment"].median()) if len(success) else np.nan,
                "false_evidence_promotion_rate": float(success["false_evidence_promotion"].mean()) if len(success) else np.nan,
            }
        )
    summary = pd.DataFrame(summaries)

    rule = registry["qualification_rule"]
    route_qualifications: list[dict[str, Any]] = []
    for route_id, frame in summary.groupby("route_id", sort=True):
        raw = metrics.loc[metrics["route_id"] == route_id]
        null_rows = raw.loc[
            (raw["scenario_id"] == "null_evidence_increment")
            & (raw["fit_status"] == "success")
        ]
        failure_rate = float((raw["fit_status"] != "success").mean())
        null_false_rate = float(null_rows["false_evidence_promotion"].mean()) if len(null_rows) else 1.0
        worst_slope_error = float(np.nanmax(np.abs(frame["median_calibration_slope"] - 1.0)))
        worst_brier = float(np.nanmax(frame["median_full_brier_regret"]))
        qualified = bool(
            failure_rate <= float(rule["maximum_fit_failure_rate"])
            and null_false_rate <= float(rule["maximum_null_false_promotion_rate"])
            and worst_slope_error
            <= float(rule["maximum_worst_scenario_median_absolute_calibration_slope_error"])
        )
        route_qualifications.append(
            {
                "route_id": route_id,
                "fit_failure_rate": failure_rate,
                "null_false_promotion_rate": null_false_rate,
                "worst_scenario_median_absolute_calibration_slope_error": worst_slope_error,
                "worst_scenario_median_full_brier_regret": worst_brier,
                "qualified": qualified,
            }
        )

    selection_pool = list(rule["primary_weighting_selection_pool"])
    eligible = [
        row for row in route_qualifications
        if row["route_id"] in selection_pool and row["qualified"]
    ]
    preference = {route_id: index for index, route_id in enumerate(selection_pool)}
    eligible.sort(
        key=lambda row: (
            row["worst_scenario_median_full_brier_regret"],
            preference[row["route_id"]],
        )
    )
    selected = eligible[0] if eligible else None
    routes_by_id = {row["route_id"]: row for row in registry["candidate_routes"]}
    decision = {
        "decision_version": "pferi_v2_model_design_minimax_decision_v1",
        "status": "PRIMARY_WEIGHTING_ROUTE_SELECTED" if selected else "NO_PRIMARY_WEIGHTING_ROUTE_QUALIFIED",
        "recommended_primary_route_id": selected["route_id"] if selected else None,
        "recommended_training_weight_strategy": (
            routes_by_id[selected["route_id"]]["training_weight_strategy"] if selected else None
        ),
        "frozen_primary_family": "ridge_logistic",
        "nonlinear_route_can_replace_primary": False,
        "route_qualifications": route_qualifications,
        "selection_rule": rule,
        "claim_boundary": registry["claim_boundary"],
    }
    return summary, decision


def _write_report(
    path: Path,
    audit: dict[str, Any],
    decision: dict[str, Any],
) -> None:
    selected = decision["recommended_primary_route_id"] or "none"
    if audit.get("synthetic_calibration_performed"):
        design_sentence = (
            f"The simulation used all {audit['master_outcome_free_row_count']:,} outcome-free within-role pairs. "
            f"It trained on {audit['sample_row_count']:,} formally selected development pairs, recalibrated on "
            f"{audit['calibration_sample_row_count']:,} formally selected calibration pairs, and evaluated against "
            f"synthetic truth over all {audit['confirmation_population_row_count']:,} confirmation-role pairs."
        )
    else:
        design_sentence = (
            f"The simulation used {audit['population_row_count']:,} outcome-free development-role pairs as the "
            f"target covariate population and the {audit['sample_row_count']:,} formally selected development pairs "
            "as the synthetic training design."
        )
    lines = [
        "# PF-ERI v2 Outcome-Free Model-Design Simulation",
        "",
        f"Status: **{audit['status']}**",
        "",
        "## Design",
        "",
        design_sentence + " No observed reviewability outcome was read. Synthetic outcomes were regenerated under every registered mechanism and replicate.",
        "",
        "The stress set covered null, weak and moderate increments; smooth nonlinearity; descriptor/evidence redundancy; a mechanism interaction; quasi-separation; informative matcher failure; shared-image random effects; and sampling-cell calibration shift. Routes were required to pass fit-failure, calibration-slope and null false-promotion gates before minimax Brier regret was considered.",
        "",
        "## Decision",
        "",
        f"Primary weighting decision status: `{decision['status']}`. Recommended registered ridge route: `{selected}`.",
        "",
        "The nonlinear spline routes are stress-test challengers only and cannot replace the frozen ridge primary family. This output chooses no fitted PF-ERI model, estimates no real effect, and cannot unlock calibration or confirmation.",
        "",
        "## Critical interpretation",
        "",
        "A PASS means the simulation executed reproducibly and the decision rule was applied as frozen. It does not mean that its synthetic mechanisms are true, that the chosen strategy will win on observed development data, or that PF-ERI is confirmed. Model-route confidence must remain conditional on the scenario registry; the next component-disjoint fold and real-development gates are still required.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_simulation(
    master_path: Path,
    formal_path: Path,
    dgp_registry_path: Path,
    model_registry_path: Path,
    output_dir: Path,
    *,
    replicates_override: int | None = None,
    expected_population_rows: int = 9445,
    expected_sample_rows: int = 445,
    expected_calibration_rows: int = 445,
    expected_confirmation_rows: int = 9417,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to replace existing simulation directory: {output_dir}")
    dgp_registry = load_dgp_registry(dgp_registry_path)
    issues = validate_dgp_registry(dgp_registry)
    if issues:
        raise ValueError("DGP registry validation failed: " + "; ".join(issues))
    model_registry = json.loads(model_registry_path.read_text(encoding="utf-8"))
    if model_registry.get("registry_version") != "pferi_v2_model_route_candidate_registry_v1":
        raise ValueError("unexpected candidate model registry")

    three_stage = dgp_registry.get("registry_version") == "pferi_v2_model_design_dgp_registry_v2"
    if three_stage:
        population, sample, calibration_sample, confirmation_population = (
            load_three_stage_outcome_free_inputs(master_path, formal_path)
        )
        development_population_rows = int(
            (population["analytical_role"].astype(str) == "development").sum()
        )
        calibration_population_rows = int(
            (population["analytical_role"].astype(str) == "calibration").sum()
        )
        observed_counts = {
            "development_population": development_population_rows,
            "development_sample": len(sample),
            "calibration_sample": len(calibration_sample),
            "confirmation_population": len(confirmation_population),
        }
        expected_counts = {
            "development_population": expected_population_rows,
            "development_sample": expected_sample_rows,
            "calibration_sample": expected_calibration_rows,
            "confirmation_population": expected_confirmation_rows,
        }
        if observed_counts != expected_counts:
            raise ValueError(
                f"three-stage simulation input count mismatch: observed={observed_counts} "
                f"expected={expected_counts}"
            )
    else:
        population, sample = load_outcome_free_inputs(master_path, formal_path)
        calibration_sample = pd.DataFrame()
        confirmation_population = pd.DataFrame()
        development_population_rows = len(population)
        calibration_population_rows = 0
        if len(population) != expected_population_rows or len(sample) != expected_sample_rows:
            raise ValueError(
                f"simulation input count mismatch: population={len(population)} sample={len(sample)}"
            )
    replicates = int(replicates_override or dgp_registry["replicates_per_scenario"])
    if replicates <= 0:
        raise ValueError("replicates must be positive")

    if three_stage:
        metrics = _simulate_replicates_three_stage(
            population,
            sample,
            calibration_sample,
            confirmation_population,
            dgp_registry,
            replicates,
        )
    else:
        metrics = _simulate_replicates(population, sample, dgp_registry, replicates)
    summary, decision = summarize_simulation(metrics, dgp_registry)
    expected_metric_rows = len(dgp_registry["scenarios"]) * replicates * len(dgp_registry["candidate_routes"])
    status = "PASS" if len(metrics) == expected_metric_rows else "FAIL"
    output_dir.mkdir(parents=True)
    frozen_dgp = output_dir / "dgp_registry_frozen.json"
    frozen_models = output_dir / "model_route_registry_snapshot.json"
    metrics_path = output_dir / "simulation_replicate_metrics.csv"
    summary_path = output_dir / "dgp_route_summary.csv"
    decision_path = output_dir / "minimax_route_decision.json"
    audit_path = output_dir / "simulation_audit.json"
    report_path = output_dir / "SIMULATION_REPORT.md"
    runner_snapshot = output_dir / "simulation_runner_snapshot.py"
    frozen_dgp.write_text(json.dumps(dgp_registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    frozen_models.write_text(json.dumps(model_registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    decision_path.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    runner_snapshot.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")

    audit = {
        "audit_version": (
            "pferi_v2_model_design_simulation_audit_v2"
            if three_stage
            else "pferi_v2_model_design_simulation_audit_v1"
        ),
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "population_row_count": development_population_rows,
        "master_outcome_free_row_count": len(population),
        "sample_row_count": len(sample),
        "calibration_population_row_count": calibration_population_rows,
        "calibration_sample_row_count": len(calibration_sample),
        "confirmation_population_row_count": len(confirmation_population),
        "synthetic_calibration_performed": three_stage,
        "qualification_probability_stage": dgp_registry.get(
            "qualification_probability_stage", "raw_development_fit"
        ),
        "scenario_count": len(dgp_registry["scenarios"]),
        "route_count": len(dgp_registry["candidate_routes"]),
        "replicates_per_scenario": replicates,
        "replicate_metric_row_count": len(metrics),
        "expected_replicate_metric_row_count": expected_metric_rows,
        "fit_failure_count": int((metrics["fit_status"] != "success").sum()),
        "real_outcomes_used": False,
        "outcome_columns_read": 0,
        "development_label_file_read": False,
        "calibration_or_confirmation_file_read": False,
        "master_input_sha256": sha256_file(master_path),
        "formal_manifest_sha256": sha256_file(formal_path),
        "dgp_registry_source_sha256": sha256_file(dgp_registry_path),
        "dgp_registry_frozen_sha256": sha256_file(frozen_dgp),
        "dgp_registry_base_sha256": dgp_registry.get("extended_registry_base_sha256"),
        "model_registry_sha256": sha256_file(model_registry_path),
        "simulation_script_sha256": sha256_file(Path(__file__)),
        "simulation_runner_snapshot_sha256": sha256_file(runner_snapshot),
        "decision_status": decision["status"],
        "recommended_primary_route_id": decision["recommended_primary_route_id"],
        "claim_boundary": dgp_registry["claim_boundary"],
    }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(report_path, audit, decision)

    checksum_paths = [
        frozen_dgp,
        frozen_models,
        metrics_path,
        summary_path,
        decision_path,
        audit_path,
        report_path,
        runner_snapshot,
    ]
    (output_dir / "CHECKSUMS.sha256").write_text(
        "\n".join(f"{sha256_file(path)}  {path.name}" for path in checksum_paths) + "\n",
        encoding="utf-8",
    )
    if status != "PASS":
        raise RuntimeError("simulation row-count audit failed")
    return audit


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--master-frame",
        type=Path,
        default=ROOT
        / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1"
        / "restricted_outcome_free_master_derivation_frame.csv",
    )
    parser.add_argument(
        "--formal-manifest",
        type=Path,
        default=ROOT
        / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_formal_pair_sampling_v1"
        / "restricted_formal_pair_sampling_manifest.csv",
    )
    parser.add_argument(
        "--dgp-registry",
        type=Path,
        default=ROOT / "schemas/pferi_v2/model_design_dgp_registry_v2.json",
    )
    parser.add_argument(
        "--model-registry",
        type=Path,
        default=ROOT / "schemas/pferi_v2/model_route_candidate_registry_v1.json",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--replicates", type=int)
    parser.add_argument("--expected-population-rows", type=int, default=9445)
    parser.add_argument("--expected-sample-rows", type=int, default=445)
    parser.add_argument("--expected-calibration-rows", type=int, default=445)
    parser.add_argument("--expected-confirmation-rows", type=int, default=9417)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    audit = run_simulation(
        args.master_frame.resolve(),
        args.formal_manifest.resolve(),
        args.dgp_registry.resolve(),
        args.model_registry.resolve(),
        args.output_dir.resolve(),
        replicates_override=args.replicates,
        expected_population_rows=args.expected_population_rows,
        expected_sample_rows=args.expected_sample_rows,
        expected_calibration_rows=args.expected_calibration_rows,
        expected_confirmation_rows=args.expected_confirmation_rows,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
