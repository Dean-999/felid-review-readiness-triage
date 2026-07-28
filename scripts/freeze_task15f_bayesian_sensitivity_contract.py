#!/usr/bin/env python3
"""Freeze Task 15F Bayesian contract and run its prespecified S5 trigger audit."""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize

from pferi_v2_fold_preprocessor import fit_fold_preprocessor, load_contract


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "schemas/pferi_v2/task15f_bayesian_sensitivity_contract_v1.json"
DATA = ROOT / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-22_stage_isolated_analysis_inputs_v1/development_open/development_modeling_input.csv"
FOLDS = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_component_disjoint_nested_folds_v1/outer_fold_assignments.csv"
PREPROCESSING = ROOT / "schemas/pferi_v2/feature_preprocessing_contract_v1.json"
PREPROCESSOR = ROOT / "scripts/pferi_v2_fold_preprocessor.py"
TASK15E_DISPOSITION = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_task15e_development_model_comparison_freeze_v1/development_disposition.json"
OUTPUT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_task15f_bayesian_sensitivity_contract_freeze_v1"
BLOCKS = ["descriptor", "independent_quality", "pair_evidence"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def logistic_objective(beta: np.ndarray, design: np.ndarray, outcome: np.ndarray) -> tuple[float, np.ndarray]:
    if not np.isfinite(beta).all() or np.max(np.abs(beta)) > 1e100:
        direction = np.sign(np.nan_to_num(beta, nan=1.0, posinf=1.0, neginf=-1.0))
        direction[direction == 0] = 1.0
        return 1e100, direction * 1e50
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        eta = design @ beta
    if not np.isfinite(eta).all():
        direction = np.sign(beta); direction[direction == 0] = 1.0
        return 1e100, direction * 1e50
    objective = float(np.mean(np.logaddexp(0.0, eta) - outcome * eta))
    probability = 1.0 / (1.0 + np.exp(-np.clip(eta, -36, 36)))
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        gradient = design.T @ (probability - outcome) / len(outcome)
    return objective, gradient


def complete_separation_feasible(design: np.ndarray, outcome: np.ndarray) -> bool:
    signed = 2.0 * outcome - 1.0
    result = linprog(
        np.zeros(design.shape[1]),
        A_ub=-(signed[:, None] * design),
        b_ub=-np.ones(len(outcome)),
        bounds=[(None, None)] * design.shape[1],
        method="highs",
    )
    return bool(result.success)


def separation_audit(frame: pd.DataFrame, contract: dict[str, Any]) -> dict[str, Any]:
    preprocessing = load_contract(PREPROCESSING)
    rows: list[dict[str, Any]] = []
    for outer_fold in range(5):
        train = frame.loc[frame["outer_fold"] != outer_fold].copy()
        fitted = fit_fold_preprocessor(train, preprocessing, BLOCKS)
        transformed = fitted.transform(train)
        varying = transformed.std(axis=0, ddof=0) >= 1e-12
        reduced = transformed.loc[:, varying]
        design = np.column_stack([np.ones(len(reduced)), reduced.to_numpy(float)])
        outcome = train["review_ready_label"].to_numpy(float)
        rank = int(np.linalg.matrix_rank(design))
        complete = complete_separation_feasible(design, outcome)
        result = minimize(
            lambda beta: logistic_objective(beta, design, outcome),
            np.zeros(design.shape[1]), jac=True, method="L-BFGS-B",
            options={"maxiter": 5000, "gtol": 1e-9, "ftol": 1e-12, "maxls": 50},
        )
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            eta = design @ result.x
        probability = 1.0 / (1.0 + np.exp(-np.clip(eta, -36, 36)))
        max_abs = float(np.max(np.abs(result.x[1:]))) if design.shape[1] > 1 else 0.0
        triggers = []
        if complete: triggers.append("complete_separation_lp")
        if not result.success or not np.isfinite(result.x).all(): triggers.append("unpenalized_optimizer_nonconvergence")
        if max_abs > 10.0: triggers.append("absolute_nonintercept_coefficient_gt_10")
        if float(probability.min()) < 1e-6 or float(probability.max()) > 0.999999: triggers.append("extreme_training_probability")
        hessian_weight = probability * (1.0 - probability)
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            fisher = design.T @ (hessian_weight[:, None] * design) / len(design)
        rows.append({
            "outer_fold": outer_fold,
            "training_rows": len(train),
            "positive_rows": int(outcome.sum()),
            "negative_rows": int(len(outcome) - outcome.sum()),
            "original_columns": transformed.shape[1],
            "nonconstant_columns": reduced.shape[1],
            "design_rank": rank,
            "design_columns_with_intercept": design.shape[1],
            "complete_separation_lp": complete,
            "optimizer_success": bool(result.success),
            "optimizer_status": int(result.status),
            "optimizer_message": str(result.message),
            "maximum_absolute_nonintercept_coefficient": max_abs,
            "minimum_training_probability": float(probability.min()),
            "maximum_training_probability": float(probability.max()),
            "fisher_condition_number": float(np.linalg.cond(fisher)),
            "trigger_reasons": triggers,
            "triggered": bool(triggers),
        })
    triggered = any(row["triggered"] for row in rows)
    return {
        "audit_version": "pferi_v2_task15f_S5_separation_trigger_audit_v1",
        "status": "PASS",
        "S5_trigger_status": "TRIGGERED_DIAGNOSTIC_ONLY" if triggered else "NOT_TRIGGERED",
        "selection_eligible": False,
        "threshold_timing_limitation": contract["models"]["S5"]["trigger_timing_limitation"],
        "folds": rows,
    }


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("contract_version") != "pferi_v2_task15f_bayesian_sensitivity_contract_v1": raise ValueError("contract version mismatch")
    if contract["scope"]["expected_pair_count"] != 445 or contract["scope"]["locked_stages"] != ["calibration", "deployment_confirmation", "mechanism_confirmation"]: raise ValueError("scope mismatch")
    if set(contract["models"]) != {"S3", "S4", "S5"}: raise ValueError("model registry mismatch")
    if contract["models"]["S4"]["outer_test_prediction"].find("20-node Gauss-Hermite") < 0: raise ValueError("S4 marginalization not frozen")
    if contract["mcmc"]["pymc"] != "6.0.1" or contract["mcmc"]["chains"] != 4: raise ValueError("MCMC runtime mismatch")


def build() -> dict[str, Any]:
    if OUTPUT.exists(): raise FileExistsError(f"refusing to overwrite {OUTPUT}")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8")); validate_contract(contract)
    source_map = {
        "development_modeling_input.csv": DATA,
        "outer_fold_assignments.csv": FOLDS,
        "feature_preprocessing_contract.json": PREPROCESSING,
        "fold_preprocessor.py": PREPROCESSOR,
        "task15e_development_disposition.json": TASK15E_DISPOSITION,
    }
    failures = [name for name, path in source_map.items() if sha256(path) != contract["authoritative_inputs"][name]]
    if failures: raise RuntimeError(f"authoritative input hash mismatch: {failures}")
    data = pd.read_csv(DATA); folds = pd.read_csv(FOLDS)
    frame = data.merge(folds[["canonical_pair_id", "component_id", "outer_fold"]], on="canonical_pair_id", validate="one_to_one")
    if len(frame) != 445 or frame["canonical_pair_id"].nunique() != 445: raise RuntimeError("development row mismatch")
    if set(frame["formal_sampling_stage"].astype(str)) != {"development"}: raise RuntimeError("locked stage detected")
    if frame.groupby("component_id")["outer_fold"].nunique().max() != 1: raise RuntimeError("component leakage")
    trigger = separation_audit(frame, contract)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUTPUT.parent, prefix=".task15f_contract_") as temporary:
        stage = Path(temporary) / OUTPUT.name; stage.mkdir()
        shutil.copy2(CONTRACT, stage / "task15f_bayesian_sensitivity_contract_frozen.json")
        write_json(stage / "separation_trigger_audit.json", trigger)
        shutil.copy2(Path(__file__), stage / "contract_freeze_builder_snapshot.py")
        report = f"""# PF-ERI v2 Task 15F Bayesian Sensitivity Contract Freeze

Status: `PASS`

This freeze fixes the S3 weak-prior Bayesian logistic model, the S4 crossed-endpoint-image random-intercept model, and the S5 separation diagnostic before any Task 15F posterior is sampled. It preserves the 445-pair development boundary, the five endpoint-component-disjoint outer folds, square-root inverse-probability pseudo-likelihood weights, and the frozen P5 feature design. Calibration and confirmation outcomes remain locked.

S4 predictions for an outer-test pair integrate the combined uncertainty of two previously unseen endpoint effects through fixed 20-node Gauss–Hermite quadrature. Conditioning on training image effects or setting new-image variance to zero is prohibited. Sampling is pinned to Python 3.12, PyMC 6.0.1, four-chain nutpie NUTS, and explicit convergence gates.

The deterministic S5 audit returned `{trigger['S5_trigger_status']}`. Because its numeric trigger thresholds were necessarily recorded after development outcomes had already been opened, S5 is never selection-eligible. If triggered, Firth/FLIC is a labelled diagnostic only; if not triggered, it is not fitted.

The next authorized action is to build the Task 15F ModelScope CPU execution package from this exact contract. Priors, quadrature, convergence gates, folds, and retry rules must not be altered after posterior sampling begins.
"""
        (stage / "TASK15F_CONTRACT_FREEZE_REPORT.md").write_text(report, encoding="utf-8")
        audit = {
            "status": "PASS", "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "contract_sha256": sha256(CONTRACT), "development_rows": len(frame),
            "component_count": int(frame["component_id"].nunique()), "outer_fold_count": int(frame["outer_fold"].nunique()),
            "authoritative_input_hash_failures": failures, "locked_stage_outcomes_accessed": False,
            "S5_trigger_status": trigger["S5_trigger_status"], "next_authorized_action": "build Task15F ModelScope CPU execution package",
        }
        write_json(stage / "contract_freeze_audit.json", audit)
        targets = sorted(path for path in stage.iterdir() if path.is_file() and path.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in targets), encoding="utf-8")
        shutil.move(str(stage), OUTPUT)
    return audit


if __name__ == "__main__":
    try: result = build()
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2)); raise SystemExit(1)
    print(json.dumps(result, indent=2, sort_keys=True))
