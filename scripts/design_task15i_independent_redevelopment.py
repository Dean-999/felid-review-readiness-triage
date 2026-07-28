#!/usr/bin/env python3
"""Freeze the outcome-free Task15I independent redevelopment design."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.special import expit

from scripts import simulate_pferi_v2_model_design as design_simulation


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
CONTRACT = ROOT / "schemas/pferi_v2/task15i_independent_redevelopment_contract_v1.json"
MODEL_REGISTRY = ROOT / "schemas/pferi_v2/model_route_candidate_registry_v1.json"
DGP_REGISTRY = ROOT / "schemas/pferi_v2/model_design_dgp_registry_v1.json"
MASTER = (
    ROOT
    / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_post_allocation_sampling_preflight_v1"
    / "restricted_outcome_free_master_derivation_frame.csv"
)
FORMAL = (
    ROOT
    / "archive/pferi_v2/task_runs/dual_sample_confirmation/2026-07-20_formal_pair_sampling_v1"
    / "restricted_formal_pair_sampling_manifest.csv"
)
FOLDS = MODEL_ROOT / "2026-07-22_component_disjoint_nested_folds_v1/outer_fold_assignments.csv"
TASK15H = (
    MODEL_ROOT
    / "2026-07-23_task15h_development_model_freeze_v1/development_model_freeze_record.json"
)
OUTPUT = MODEL_ROOT / "2026-07-25_task15i_independent_redevelopment_design_freeze_v1"
OUTCOME_TOKENS = ("label", "outcome", "review_ready", "adjudicat", "identity")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError(f"refusing to write an empty CSV: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_checksum_manifest(directory: Path) -> list[str]:
    manifest = directory / "CHECKSUMS.sha256"
    if not manifest.is_file():
        return ["missing:CHECKSUMS.sha256"]
    failures: list[str] = []
    declared: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        declared.add(relative)
        target = directory / relative
        if not target.is_file():
            failures.append(f"missing:{relative}")
        elif sha256(target) != expected:
            failures.append(f"sha256:{relative}")
    actual = {
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() and path.name != "CHECKSUMS.sha256"
    }
    failures.extend(f"inventory:{name}" for name in sorted(actual ^ declared))
    return failures


def reject_outcome_columns(path: Path) -> None:
    columns = pd.read_csv(path, nrows=0).columns.tolist()
    contaminated = [
        column
        for column in columns
        if any(token in column.lower() for token in OUTCOME_TOKENS)
    ]
    if contaminated:
        raise ValueError(f"outcome-like columns are prohibited: {sorted(contaminated)}")


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("status") != "FROZEN_PRELABEL_REDEVELOPMENT_DESIGN":
        raise RuntimeError("Task15I contract is not a frozen prelabel design")
    if contract["information_boundary"]["locked_outcomes_may_be_read"]:
        raise RuntimeError("Task15I contract permits locked outcomes")
    if contract["information_boundary"]["existing_locked_stages_may_be_reassigned"]:
        raise RuntimeError("Task15I contract permits stage reassignment")
    return contract


def validate_task15h() -> dict[str, Any]:
    record = json.loads(TASK15H.read_text(encoding="utf-8"))
    expected = "VALIDATED_NO_DEVELOPMENT_MODEL_QUALIFIED_CALIBRATION_LOCKED"
    if record.get("status") != expected:
        raise RuntimeError("Task15H is not the required validated nonqualification record")
    if record.get("calibration_authorized") is not False:
        raise RuntimeError("Task15H unexpectedly authorized calibration")
    return record


def load_outcome_free_structure() -> tuple[pd.DataFrame, pd.DataFrame]:
    reject_outcome_columns(MASTER)
    reject_outcome_columns(FORMAL)
    population, sample = design_simulation.load_outcome_free_inputs(MASTER, FORMAL)
    if len(population) != 9445 or len(sample) != 445:
        raise RuntimeError("unexpected frozen outcome-free development structure")
    return population, sample


def select_fixed_lambda(
    population: pd.DataFrame,
    sample: pd.DataFrame,
    registry: dict[str, Any],
    contract: dict[str, Any],
    *,
    replicates_override: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selection = contract["fixed_lambda_selection"]
    candidates = [float(value) for value in selection["candidate_grid"]]
    replicates = int(replicates_override or selection["replicates_per_scenario"])
    if replicates <= 0:
        raise ValueError("lambda simulation replicates must be positive")
    simulator_family = {
        "l2_logistic": "ridge_logistic",
    }.get(selection["model_family"])
    if simulator_family is None:
        raise ValueError("Task15I fixed-lambda simulator supports l2_logistic only")
    matrices = design_simulation.build_design_matrices(
        sample, population, simulator_family
    )
    population_indices = sample["_population_index"].to_numpy(int)
    weights = design_simulation.training_weights(
        sample["first_order_inclusion_probability"].to_numpy(float),
        selection["training_weight_strategy"],
    )
    rows: list[dict[str, Any]] = []
    for scenario_index, scenario in enumerate(registry["scenarios"]):
        for replicate in range(replicates):
            rng = np.random.default_rng(
                int(registry["simulation_seed"]) + scenario_index * 100_003 + replicate
            )
            truth, _ = design_simulation.synthetic_probability_pair(population, scenario, rng)
            outcome = rng.binomial(1, truth[population_indices]).astype(float)
            for penalty in candidates:
                try:
                    active_beta = design_simulation.fit_ridge_logistic(
                        matrices.train_active, outcome, weights, penalty=penalty
                    )
                    full_beta = design_simulation.fit_ridge_logistic(
                        matrices.train_full, outcome, weights, penalty=penalty
                    )
                    active_prediction = expit(matrices.population_active @ active_beta)
                    full_prediction = expit(matrices.population_full @ full_beta)
                    active_brier = float(np.mean((active_prediction - truth) ** 2))
                    full_brier = float(np.mean((full_prediction - truth) ** 2))
                    rows.append(
                        {
                            "scenario_id": scenario["scenario_id"],
                            "replicate": replicate,
                            "lambda": penalty,
                            "fit_status": "success",
                            "active_brier_regret": active_brier,
                            "full_brier_regret": full_brier,
                            "paired_brier_increment": active_brier - full_brier,
                        }
                    )
                except Exception as error:
                    rows.append(
                        {
                            "scenario_id": scenario["scenario_id"],
                            "replicate": replicate,
                            "lambda": penalty,
                            "fit_status": type(error).__name__,
                            "active_brier_regret": math.nan,
                            "full_brier_regret": math.nan,
                            "paired_brier_increment": math.nan,
                        }
                    )
    frame = pd.DataFrame(rows)
    summary: list[dict[str, Any]] = []
    for penalty, group in frame.groupby("lambda", sort=True):
        valid = group.loc[group["fit_status"] == "success"]
        by_scenario = valid.groupby("scenario_id")["full_brier_regret"].median()
        summary.append(
            {
                "lambda": float(penalty),
                "fit_failure_count": int((group["fit_status"] != "success").sum()),
                "worst_scenario_median_full_brier_regret": float(by_scenario.max()),
                "mean_full_brier_regret": float(valid["full_brier_regret"].mean()),
                "median_paired_brier_increment": float(valid["paired_brier_increment"].median()),
            }
        )
    if any(row["fit_failure_count"] for row in summary):
        raise RuntimeError("outcome-free fixed-lambda simulation had fit failures")
    selected = min(
        summary,
        key=lambda row: (
            row["worst_scenario_median_full_brier_regret"],
            -row["lambda"],
        ),
    )
    decision = {
        "status": "FIXED_LAMBDA_SELECTED_OUTCOME_FREE",
        "selected_lambda": selected["lambda"],
        "candidate_grid": candidates,
        "replicates_per_scenario": replicates,
        "selection_rule": selection["selection_rule"],
        "selected_for": ["P3", "P5"],
    }
    return summary, decision


def simulate_component_operating_characteristics(
    *,
    component_counts: tuple[int, ...] | list[int],
    pairs_per_component: int,
    true_increments: tuple[float, ...] | list[float],
    paired_loss_sd: float,
    intracomponent_correlation: float,
    practical_increment: float,
    replicates: int,
    seed: int,
    confidence_level: float = 0.95,
) -> list[dict[str, Any]]:
    if not 0 <= intracomponent_correlation < 1:
        raise ValueError("intracomponent correlation must lie in [0, 1)")
    if pairs_per_component <= 0 or replicates <= 0:
        raise ValueError("pairs_per_component and replicates must be positive")
    z_value = 1.959963984540054 if confidence_level == 0.95 else float(
        __import__("scipy").stats.norm.ppf(0.5 + confidence_level / 2)
    )
    rows: list[dict[str, Any]] = []
    for component_count in component_counts:
        if component_count <= 1:
            raise ValueError("at least two components are required")
        design_effect = 1 + (pairs_per_component - 1) * intracomponent_correlation
        effective_pairs = component_count * pairs_per_component / design_effect
        component_mean_sd = paired_loss_sd * math.sqrt(
            intracomponent_correlation
            + (1 - intracomponent_correlation) / pairs_per_component
        )
        for increment_index, true_increment in enumerate(true_increments):
            rng = np.random.default_rng(
                seed + component_count * 10_007 + increment_index * 1_009
            )
            component_means = rng.normal(
                loc=true_increment,
                scale=component_mean_sd,
                size=(replicates, component_count),
            )
            estimate = component_means.mean(axis=1)
            standard_error = component_means.std(axis=1, ddof=1) / math.sqrt(
                component_count
            )
            lower_bound = estimate - z_value * standard_error
            rows.append(
                {
                    "component_count": int(component_count),
                    "pairs_per_component": int(pairs_per_component),
                    "analyzable_pair_count": int(component_count * pairs_per_component),
                    "paired_loss_difference_sd": float(paired_loss_sd),
                    "intracomponent_correlation": float(intracomponent_correlation),
                    "design_effect": float(design_effect),
                    "effective_pair_count": float(effective_pairs),
                    "practical_brier_increment": float(practical_increment),
                    "synthetic_true_brier_increment": float(true_increment),
                    "replicates": int(replicates),
                    "point_threshold_success_probability": float(
                        np.mean(estimate >= practical_increment)
                    ),
                    "lower_confidence_bound_success_probability": float(
                        np.mean(lower_bound > practical_increment)
                    ),
                }
            )
    return rows


def current_structure_audit() -> dict[str, Any]:
    assignments = pd.read_csv(FOLDS)
    if {"canonical_pair_id", "component_id"} - set(assignments.columns):
        raise RuntimeError("fold assignment lacks component identifiers")
    component_sizes = assignments["component_id"].value_counts()
    formal = pd.read_csv(FORMAL)
    development = formal.loc[formal["formal_sampling_stage"] == "development"]
    endpoint_degree = pd.concat(
        [development["endpoint_a_image_id"], development["endpoint_b_image_id"]]
    ).value_counts()
    return {
        "status": "PASS",
        "existing_development_pair_count": int(len(assignments)),
        "existing_development_component_count": int(component_sizes.size),
        "existing_maximum_component_pair_count": int(component_sizes.max()),
        "existing_median_component_pair_count": float(component_sizes.median()),
        "existing_formal_development_unique_images": int(endpoint_degree.size),
        "existing_formal_development_maximum_endpoint_degree": int(endpoint_degree.max()),
        "interpretation": "The existing component structure is descriptive only and cannot be recycled as the new independent redevelopment sample.",
    }


def report_text(record: dict[str, Any], structure: dict[str, Any]) -> str:
    recommended = record["recommended_design"]
    return f"""# PF-ERI v2 Task 15I Independent Redevelopment Design Freeze

Status: `{record["status"]}`

## Scope

Task 15I freezes a prospective remedy after Task 15H documented that no development model qualified. The design reads only outcome-free covariates, graph structure, formal sampling metadata, and synthetic outcomes generated inside the simulation. It does not read the existing development labels for selection and does not read, reassign, or expose calibration, deployment-confirmation, or mechanism-confirmation outcomes.

## Structural rationale

The failed development analysis contained {structure["existing_development_pair_count"]} pairs in {structure["existing_development_component_count"]} endpoint-image components, with a largest component of {structure["existing_maximum_component_pair_count"]} pairs. That structure permits a single component to influence an outer fold disproportionately. The new design therefore treats endpoint-image components as the independent replication unit. It requires at least {recommended["component_count"]} components and {recommended["analyzable_pair_count"]} analyzable pairs, with no more than {record["sampling_design"]["maximum_pairs_per_component"]} pairs in one component and no endpoint degree above {record["sampling_design"]["maximum_endpoint_degree"]}.

## Fixed regularization

The prelabel synthetic stress simulation selected lambda {record["fixed_lambda"]:.6g} from the registered grid for both P3 and P5. This lambda is fixed for all future outer and inner folds. The previous result is not used to tune it. Fixing the penalty prevents the 0.1-versus-100 cross-fold swing that blocked the prior route; it does not guarantee that the new model will qualify.

## Operating characteristics and qualification

The component-level operating-characteristic simulation assumes a paired-loss standard deviation of 0.12 and intracomponent correlation of 0.10. The recommended design is the smallest one satisfying the frozen component and pair requirements and at least 0.80 probability that a development point estimate exceeds 0.005 when the synthetic true Brier increment is 0.01. This is a screening property, not a claim of confirmation power. The future development freeze requires a weighted P3-minus-P5 Brier increment of at least 0.005, nonnegative increment in at least four of five outer folds, a weighted calibration intercept no farther than 0.20 from zero, a weighted calibration slope from 0.80 to 1.20, finite probabilities, no leakage, and the fixed regularization policy.

## Authorization boundary

This artifact does not authorize collection of outcomes, calibration, or confirmation. Before any new label is opened, a new image-disjoint and pair-disjoint sampling manifest, component audit, fold assignment, preprocessing contract, and execution package must be frozen. If the future independent development result fails any qualification rule, the P5 confirmation route stops without accessing a locked-stage outcome.
"""


def freeze(
    output: Path = OUTPUT,
    *,
    lambda_replicates_override: int | None = None,
    operating_characteristic_replicates_override: int | None = None,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing design freeze: {output}")
    contract = load_contract()
    task15h = validate_task15h()
    population, sample = load_outcome_free_structure()
    dgp = design_simulation.load_dgp_registry(DGP_REGISTRY)
    issues = design_simulation.validate_dgp_registry(dgp)
    if issues:
        raise RuntimeError("DGP registry validation failed: " + "; ".join(issues))
    lambda_rows, lambda_decision = select_fixed_lambda(
        population,
        sample,
        dgp,
        contract,
        replicates_override=lambda_replicates_override,
    )
    operating = contract["operating_characteristic_simulation"]
    operating_rows = simulate_component_operating_characteristics(
        component_counts=tuple(operating["component_counts"]),
        pairs_per_component=int(operating["pairs_per_component"]),
        true_increments=tuple(operating["synthetic_true_brier_increments"]),
        paired_loss_sd=float(operating["paired_loss_difference_sd"]),
        intracomponent_correlation=float(operating["intracomponent_correlation"]),
        practical_increment=float(operating["practical_brier_increment"]),
        replicates=int(
            operating_characteristic_replicates_override or operating["replicates"]
        ),
        seed=2026072501,
        confidence_level=float(operating["confidence_level"]),
    )
    qualifying = [
        row
        for row in operating_rows
        if row["component_count"] >= contract["sampling_design"]["minimum_component_count"]
        and row["analyzable_pair_count"] >= contract["sampling_design"]["analyzable_pair_target"]
        and row["synthetic_true_brier_increment"] == 0.01
        and row["point_threshold_success_probability"] >= 0.80
    ]
    if not qualifying:
        raise RuntimeError("no design meets the frozen operating-characteristic rule")
    recommended = min(
        qualifying,
        key=lambda row: (row["analyzable_pair_count"], row["component_count"]),
    )
    structure = current_structure_audit()
    record = {
        "record_version": "pferi_v2_task15i_independent_redevelopment_design_record_v1",
        "status": "FROZEN_OUTCOME_FREE_INDEPENDENT_REDEVELOPMENT_DESIGN",
        "source_task15h_status": task15h["status"],
        "new_development_outcomes_opened": False,
        "calibration_authorized": False,
        "locked_stage_outcomes_accessed": False,
        "fixed_lambda": lambda_decision["selected_lambda"],
        "lambda_selection": lambda_decision,
        "sampling_design": contract["sampling_design"],
        "qualification_policy": contract["qualification_policy"],
        "recommended_design": recommended,
        "next_required_freeze": "New image-disjoint and pair-disjoint redevelopment sampling manifest, component audit, fold assignment, preprocessing contract, and execution package.",
        "prohibited_actions": [
            "reuse of existing development labels for selection",
            "reassignment or reading of locked calibration or confirmation outcomes",
            "outer-fold lambda retuning",
            "automatic P3 fallback if P5 fails",
            "promotion of sensitivity or exploratory routes",
            "calibration before a passing future development freeze",
        ],
        "claim_boundary": contract["claim_boundary"],
        "source_sha256": {
            "contract": sha256(CONTRACT),
            "model_registry": sha256(MODEL_REGISTRY),
            "dgp_registry": sha256(DGP_REGISTRY),
            "outcome_free_master": sha256(MASTER),
            "formal_sampling_manifest": sha256(FORMAL),
            "current_fold_assignment": sha256(FOLDS),
            "task15h_record": sha256(TASK15H),
        },
    }
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        write_json(stage / "task15i_contract_frozen.json", contract)
        write_csv(stage / "fixed_lambda_operating_characteristics.csv", lambda_rows)
        write_json(stage / "fixed_lambda_selection.json", lambda_decision)
        write_csv(stage / "component_operating_characteristics.csv", operating_rows)
        write_json(stage / "current_structure_audit.json", structure)
        write_json(stage / "independent_redevelopment_design_record.json", record)
        (stage / "TASK15I_INDEPENDENT_REDEVELOPMENT_DESIGN_REPORT.md").write_text(
            report_text(record, structure), encoding="utf-8"
        )
        shutil.copy2(Path(__file__), stage / "design_builder_snapshot.py")
        audit = {
            "audit_version": "pferi_v2_task15i_independent_redevelopment_design_audit_v1",
            "status": "PASS",
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "real_outcomes_used": False,
            "locked_stage_outcomes_accessed": False,
            "new_development_outcomes_opened": False,
            "outcome_like_input_columns_detected": [],
            "fixed_lambda": lambda_decision["selected_lambda"],
            "lambda_simulation_rows": len(lambda_rows),
            "recommended_design": recommended,
            "existing_structure": structure,
            "calibration_authorized": False,
        }
        write_json(stage / "design_audit.json", audit)
        targets = sorted(
            path
            for path in stage.rglob("*")
            if path.is_file() and path.name != "CHECKSUMS.sha256"
        )
        (stage / "CHECKSUMS.sha256").write_text(
            "".join(
                f"{sha256(path)}  {path.relative_to(stage)}\n" for path in targets
            ),
            encoding="utf-8",
        )
        shutil.move(str(stage), output)
    return audit


def main() -> int:
    try:
        audit = freeze()
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, indent=2))
        return 1
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
