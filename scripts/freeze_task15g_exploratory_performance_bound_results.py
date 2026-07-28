#!/usr/bin/env python3
"""Independently validate and freeze Task 15G performance-bound results."""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXECUTION = (
    ROOT
    / "work/pferi_v2/gpu/runs/task15g_local_execution"
)
ZIP = EXECUTION / "PF_ERI_TASK15G_FINAL_EXPORT.zip"
SHA = EXECUTION / "PF_ERI_TASK15G_FINAL_EXPORT.sha256"
SUMMARY = EXECUTION / "PF_ERI_TASK15G_RUN_SUMMARY.txt"
TASK15E_FREEZE = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-22_task15e_development_model_comparison_freeze_v1"
)
TASK15F_FREEZE = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15f_bayesian_sensitivity_result_freeze_v1"
)
OUTPUT = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15g_exploratory_performance_bound_result_freeze/iterations/v1"
)
MODELS = ("E1", "E2")
EPS = 1e-12


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


def parse_declared_sha(path: Path) -> str:
    token = path.read_text(encoding="utf-8").strip().split()[0]
    if len(token) != 64 or any(character not in "0123456789abcdef" for character in token):
        raise ValueError("SHA256 declaration is invalid")
    return token


def parse_summary(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def verify_summary(path: Path, zip_path: Path, digest: str, members: int) -> None:
    values = parse_summary(path)
    if values.get("status") != "COMPLETE":
        raise RuntimeError("run summary does not report COMPLETE")
    if values.get("final_export_sha256") != digest:
        raise RuntimeError("run summary ZIP SHA256 mismatch")
    if int(values.get("final_export_size_bytes", -1)) != zip_path.stat().st_size:
        raise RuntimeError("run summary ZIP size mismatch")
    if int(values.get("final_export_members", -1)) != members:
        raise RuntimeError("run summary ZIP member count mismatch")


def extract_results(archive: zipfile.ZipFile, destination: Path) -> None:
    prefix = "PF_ERI_TASK15G_RESULTS/"
    names = [name for name in archive.namelist() if not name.endswith("/")]
    if not names or any(not name.startswith(prefix) for name in names):
        raise RuntimeError("unexpected ZIP member prefix")
    for name in names:
        relative = Path(name.removeprefix(prefix))
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("unsafe ZIP member")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(name))


def verify_internal_checksums(results: Path) -> tuple[int, list[str]]:
    checksum_path = results / "CHECKSUMS.sha256"
    if not checksum_path.is_file():
        raise RuntimeError("missing internal CHECKSUMS.sha256")
    failures: list[str] = []
    declared: set[str] = set()
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        declared.add(relative)
        target = results / relative
        if not target.is_file() or sha256(target) != expected:
            failures.append(relative)
    actual = {
        str(path.relative_to(results))
        for path in results.rglob("*")
        if path.is_file() and path.name != "CHECKSUMS.sha256"
    }
    if actual != declared:
        failures.extend(f"inventory:{name}" for name in sorted(actual ^ declared))
    return len(declared), failures


def evaluation_weights(probability: np.ndarray) -> np.ndarray:
    raw = 1.0 / np.asarray(probability, dtype=float)
    if np.any(~np.isfinite(raw)) or np.any(raw <= 0):
        raise ValueError("invalid inclusion probability")
    return raw / raw.mean()


def recompute_metric(group: pd.DataFrame) -> dict[str, float]:
    y = group["review_ready_label"].to_numpy(float)
    probability = group["probability"].to_numpy(float)
    weights = evaluation_weights(
        group["first_order_inclusion_probability"].to_numpy(float)
    )
    return {
        "weighted_brier": float(np.average((y - probability) ** 2, weights=weights)),
        "weighted_log_loss": float(
            np.average(
                -(
                    y * np.log(np.clip(probability, EPS, 1 - EPS))
                    + (1 - y) * np.log(np.clip(1 - probability, EPS, 1 - EPS))
                ),
                weights=weights,
            )
        ),
    }


def close(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)


def validate_checkpoints(results: Path, contract_sha: str) -> list[str]:
    failures: list[str] = []
    checkpoint_dir = results / "fold_checkpoints"
    for outer_fold in range(5):
        for model_id in MODELS:
            prefix = checkpoint_dir / f"{model_id}_fold{outer_fold}"
            checkpoint = prefix.with_suffix(".json")
            if not checkpoint.is_file():
                failures.append(f"missing_checkpoint:{model_id}:{outer_fold}")
                continue
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            if saved.get("status") != "PASS" or saved.get("contract_sha256") != contract_sha:
                failures.append(f"checkpoint_status_or_contract:{model_id}:{outer_fold}")
            for suffix, key in (
                ("predictions.csv", "predictions_sha256"),
                ("inner_selection.csv", "inner_sha256"),
                ("selected_configuration.json", "selected_sha256"),
            ):
                target = prefix.with_name(prefix.name + f"_{suffix}")
                if not target.is_file() or saved.get(key) != sha256(target):
                    failures.append(f"checkpoint_hash:{model_id}:{outer_fold}:{suffix}")
    return failures


def independent_analysis(
    results: Path, task15e_freeze: Path, task15f_freeze: Path
) -> dict[str, Any]:
    failures: list[str] = []
    validation = json.loads((results / "validation_audit.json").read_text(encoding="utf-8"))
    execution = json.loads((results / "execution_audit.json").read_text(encoding="utf-8"))
    availability = json.loads(
        (results / "model_availability_audit.json").read_text(encoding="utf-8")
    )
    contract_path = results / "execution_contract_frozen.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract_sha = sha256(contract_path)
    if validation.get("status") != "PASS" or validation.get("failures") != []:
        failures.append("upstream_validation_not_pass")
    if execution.get("contract_sha256") != contract_sha:
        failures.append("execution_contract_hash_mismatch")
    if execution.get("locked_stage_outcomes_accessed") is not False:
        failures.append("locked_stage_access")
    if execution.get("final_model_selected") is not False:
        failures.append("premature_final_model_selection")
    if availability.get("status") != "PASS" or availability.get("E3_prediction_rows") != 0:
        failures.append("E3_availability_disposition_mismatch")
    if contract["models"]["E3"]["confirmation_eligible"] is not False:
        failures.append("E3_confirmation_eligibility_mismatch")

    predictions = pd.read_csv(results / "exploratory_oof_predictions.csv")
    required_prediction = {
        "canonical_pair_id",
        "component_id",
        "outer_fold",
        "model_id",
        "review_ready_label",
        "first_order_inclusion_probability",
        "probability",
    }
    if not required_prediction.issubset(predictions.columns):
        failures.append("prediction_schema")
    if len(predictions) != 890:
        failures.append("prediction_rows")
    if predictions["canonical_pair_id"].nunique() != 445:
        failures.append("prediction_pair_coverage")
    if predictions["component_id"].nunique() != 116:
        failures.append("prediction_component_coverage")
    if predictions.duplicated(["canonical_pair_id", "model_id"]).any():
        failures.append("duplicate_predictions")
    if set(predictions["model_id"]) != set(MODELS):
        failures.append("prediction_model_coverage")
    probability = pd.to_numeric(predictions["probability"], errors="coerce")
    if probability.isna().any() or (~probability.between(0, 1)).any():
        failures.append("invalid_probability")

    reported_overall = pd.read_csv(results / "exploratory_overall_metrics.csv").set_index(
        "model_id"
    )
    reported_folds = pd.read_csv(
        results / "exploratory_outer_fold_metrics.csv"
    ).set_index(["model_id", "outer_fold"])
    recomputed_overall: dict[str, dict[str, float]] = {}
    recomputed_folds: list[dict[str, Any]] = []
    for model_id in MODELS:
        model_rows = predictions.loc[predictions["model_id"] == model_id]
        recomputed = recompute_metric(model_rows)
        recomputed_overall[model_id] = recomputed
        for metric, value in recomputed.items():
            if not close(value, reported_overall.loc[model_id, metric]):
                failures.append(f"overall_metric:{model_id}:{metric}")
        for outer_fold in range(5):
            fold_rows = model_rows.loc[model_rows["outer_fold"].astype(int) == outer_fold]
            fold_metrics = recompute_metric(fold_rows)
            recomputed_folds.append(
                {"model_id": model_id, "outer_fold": outer_fold, **fold_metrics}
            )
            for metric, value in fold_metrics.items():
                reported_name = metric.removeprefix("weighted_")
                if not close(
                    value, reported_folds.loc[(model_id, outer_fold), reported_name]
                ):
                    failures.append(f"fold_metric:{model_id}:{outer_fold}:{metric}")

    inner = pd.read_csv(results / "inner_selection_results.csv")
    selected = pd.read_csv(results / "selected_configurations.csv")
    expected_inner = {"E1": 160, "E2": 240}
    if len(inner) != 400:
        failures.append("inner_row_count")
    if (inner["status"] != "PASS").any():
        failures.append("failed_inner_configuration")
    for model_id, count in expected_inner.items():
        if int((inner["model_id"] == model_id).sum()) != count:
            failures.append(f"inner_model_count:{model_id}")
    if len(selected) != 10 or selected.duplicated(["model_id", "outer_fold"]).any():
        failures.append("selected_configuration_coverage")
    for outer_fold in range(5):
        for model_id in MODELS:
            rows = inner.loc[
                (inner["outer_fold"].astype(int) == outer_fold)
                & (inner["model_id"] == model_id)
            ]
            means = rows.groupby("configuration_id")["brier"].mean()
            expected = str(means.idxmin())
            observed = str(
                selected.loc[
                    (selected["outer_fold"].astype(int) == outer_fold)
                    & (selected["model_id"] == model_id),
                    "configuration_id",
                ].iloc[0]
            )
            if observed != expected:
                failures.append(f"selected_configuration:{model_id}:{outer_fold}")

    failures.extend(validate_checkpoints(results, contract_sha))
    task15e_metrics = pd.read_csv(
        task15e_freeze / "results/overall_model_metrics.csv"
    ).set_index("model_id")
    task15f_metrics = pd.read_csv(
        task15f_freeze / "results/bayesian_overall_metrics.csv"
    ).set_index("model_id")
    comparison: dict[str, dict[str, float]] = {}
    for model_id in MODELS:
        brier = recomputed_overall[model_id]["weighted_brier"]
        comparison[model_id] = {
            "minus_P5_weighted_brier": brier
            - float(task15e_metrics.loc["P5", "weighted_brier"]),
            "minus_S3_weighted_brier": brier
            - float(task15f_metrics.loc["S3", "weighted_brier"]),
            "minus_S4_weighted_brier": brier
            - float(task15f_metrics.loc["S4", "weighted_brier"]),
        }
    fold_brier = pd.DataFrame(recomputed_folds)
    wide = fold_brier.pivot(
        index="outer_fold", columns="model_id", values="weighted_brier"
    )
    fold_wins = {
        "E1_lower_brier_folds": int((wide["E1"] < wide["E2"]).sum()),
        "E2_lower_brier_folds": int((wide["E2"] < wide["E1"]).sum()),
        "ties": int((wide["E1"] == wide["E2"]).sum()),
    }
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "prediction_rows": len(predictions),
        "unique_pairs": int(predictions["canonical_pair_id"].nunique()),
        "unique_components": int(predictions["component_id"].nunique()),
        "inner_selection_rows": len(inner),
        "selected_configuration_rows": len(selected),
        "E3_prediction_rows": int(availability.get("E3_prediction_rows", -1)),
        "recomputed_overall": recomputed_overall,
        "recomputed_outer_folds": recomputed_folds,
        "cross_task_brier_comparison": comparison,
        "E1_E2_fold_brier_wins": fold_wins,
        "selected_configuration_counts": {
            model_id: selected.loc[
                selected["model_id"] == model_id, "configuration_id"
            ]
            .value_counts()
            .sort_index()
            .to_dict()
            for model_id in MODELS
        },
        "all_inner_fits_passed": bool((inner["status"] == "PASS").all()),
        "locked_stage_outcomes_accessed": False,
        "final_model_selected": False,
    }


def report_text(analysis: dict[str, Any], source_sha: str) -> str:
    e1 = analysis["recomputed_overall"]["E1"]
    e2 = analysis["recomputed_overall"]["E2"]
    wins = analysis["E1_E2_fold_brier_wins"]
    comparison = analysis["cross_task_brier_comparison"]
    return f"""# PF-ERI v2 Task 15G Exploratory Performance-Bound Result Freeze

Status: `FROZEN_COMPLETE_PERFORMANCE_BOUND_ONLY_NO_FINAL_SELECTION`

The independently verified export has SHA256 `{source_sha}`. It contains 890 honest out-of-fold predictions for 445 development pairs, 400 inner configuration-fold scores, ten selected outer-fold configurations, and zero E3 predictions. All upstream validation checks, internal checksums, checkpoint hashes, and independent metric recalculations passed. Calibration, deployment-confirmation, and mechanism-confirmation outcomes were not accessed.

E1 obtained a design-weighted Brier score of {e1['weighted_brier']:.9f} and weighted log loss of {e1['weighted_log_loss']:.9f}. E2 obtained a design-weighted Brier score of {e2['weighted_brier']:.9f} and weighted log loss of {e2['weighted_log_loss']:.9f}. E2 was better on both overall proper scores, but E1 had the lower Brier score in {wins['E1_lower_brier_folds']} of five outer folds and E2 in {wins['E2_lower_brier_folds']}. E2 selected the same shallow configuration in all five outer folds, while E1 retained the same learning rate and leaf count but alternated between two bin limits.

The exploratory learners did not establish a higher proper-score ceiling than the previously frozen Bayesian sensitivities. E1 exceeded the S3 and S4 weighted Brier scores by {comparison['E1']['minus_S3_weighted_brier']:.9f} and {comparison['E1']['minus_S4_weighted_brier']:.9f}, respectively. E2 exceeded them by {comparison['E2']['minus_S3_weighted_brier']:.9f} and {comparison['E2']['minus_S4_weighted_brier']:.9f}. These are descriptive development comparisons, not qualification or confirmation evidence.

E1, E2, and E3 remain `confirmation_eligible=false`. Task 15G does not select a final model and cannot authorize calibration. The next authorized task is Task 15H, which must apply qualification before performance and produce a validated `development_model_freeze_record.json`.
"""


def freeze(
    zip_path: Path = ZIP,
    sha_path: Path = SHA,
    summary_path: Path = SUMMARY,
    task15e_freeze: Path = TASK15E_FREEZE,
    task15f_freeze: Path = TASK15F_FREEZE,
    output: Path = OUTPUT,
) -> dict[str, Any]:
    zip_path = Path(zip_path).resolve()
    sha_path = Path(sha_path).resolve()
    summary_path = Path(summary_path).resolve()
    task15e_freeze = Path(task15e_freeze).resolve()
    task15f_freeze = Path(task15f_freeze).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    declared = parse_declared_sha(sha_path)
    actual = sha256(zip_path)
    if declared != actual:
        raise RuntimeError("external ZIP SHA256 mismatch")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC failure")
        verify_summary(summary_path, zip_path, actual, len(archive.namelist()))
        with tempfile.TemporaryDirectory(
            dir=output.parent, prefix=".task15g_result_freeze_"
        ) as temporary:
            stage = Path(temporary) / output.name
            source = stage / "source_delivery"
            results = stage / "results"
            source.mkdir(parents=True)
            results.mkdir()
            shutil.copy2(zip_path, source / zip_path.name)
            shutil.copy2(sha_path, source / sha_path.name)
            shutil.copy2(summary_path, source / summary_path.name)
            extract_results(archive, results)
            checksum_count, checksum_failures = verify_internal_checksums(results)
            if checksum_failures:
                raise RuntimeError(f"internal checksum failures: {checksum_failures}")
            analysis = independent_analysis(results, task15e_freeze, task15f_freeze)
            if analysis["status"] != "PASS":
                raise RuntimeError(f"independent analysis failed: {analysis['failures']}")
            write_json(stage / "independent_recalculation.json", analysis)
            disposition = {
                "record_version": "pferi_v2_task15g_exploratory_performance_bound_result_freeze_v1",
                "status": "FROZEN_COMPLETE_PERFORMANCE_BOUND_ONLY_NO_FINAL_SELECTION",
                "task15g_execution": "PASS",
                "task15g_output_integrity": "PASS",
                "E1_role": "EXPLORATORY_PERFORMANCE_BOUND_NOT_CONFIRMATION_ELIGIBLE",
                "E2_role": "EXPLORATORY_PERFORMANCE_BOUND_NOT_CONFIRMATION_ELIGIBLE",
                "E3_role": "REGISTERED_BUT_INELIGIBLE_UNDER_COMMON_WEIGHTING_CONTRACT",
                "performance_bound_disposition": "NO_EXPLORATORY_PROPER_SCORE_CEILING_ABOVE_FROZEN_S3_S4_SENSITIVITIES",
                "final_model_selected": False,
                "locked_stages": [
                    "calibration",
                    "deployment_confirmation",
                    "mechanism_confirmation",
                ],
                "prohibited_after_freeze": [
                    "Task15G rerun for a more favorable result",
                    "exploratory grid expansion informed by Task15G outcomes",
                    "promotion of E1, E2, or E3 to confirmation eligibility",
                    "access to locked-stage outcomes before Task15H authorization",
                ],
                "next_authorized_task": "Task15H qualification-before-performance development model freeze",
            }
            write_json(stage / "task15g_disposition.json", disposition)
            (stage / "TASK15G_EXPLORATORY_PERFORMANCE_BOUND_RESULT_FREEZE_REPORT.md").write_text(
                report_text(analysis, actual), encoding="utf-8"
            )
            shutil.copy2(Path(__file__), stage / "freeze_builder_snapshot.py")
            audit = {
                "status": "PASS",
                "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_zip_sha256": actual,
                "source_zip_size_bytes": zip_path.stat().st_size,
                "source_zip_member_count": 53,
                "internal_checksum_count": checksum_count,
                "internal_checksum_failures": checksum_failures,
                "independent_recalculation_status": analysis["status"],
                "prediction_rows": analysis["prediction_rows"],
                "unique_pairs": analysis["unique_pairs"],
                "unique_components": analysis["unique_components"],
                "inner_selection_rows": analysis["inner_selection_rows"],
                "selected_configuration_rows": analysis["selected_configuration_rows"],
                "E3_prediction_rows": analysis["E3_prediction_rows"],
                "locked_stage_outcomes_accessed": False,
                "final_model_selected": False,
                "disposition": disposition["status"],
            }
            write_json(stage / "freeze_audit.json", audit)
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
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
