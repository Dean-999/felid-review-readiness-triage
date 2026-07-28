#!/usr/bin/env python3
"""Verify, independently recalculate, and immutably freeze Task 15F results."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FULL_RUN = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15f_modelscope_full_run_v1"
TASK15E_FREEZE = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_task15e_development_model_comparison_freeze_v1"
DEFAULT_OUTPUT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15f_bayesian_sensitivity_result_freeze_v1"
PREFIX = "PF_ERI_TASK15F_RESULTS/"
MODELS = ("S3", "S4")
FOLDS = tuple(range(5))
EPS = 1e-12

TOP_LEVEL_RESULT_FILES = {
    "CHECKSUMS.sha256",
    "S4_marginalization_audit.json",
    "TASK15F_SENSITIVITY_REPORT.md",
    "bayesian_oof_predictions.csv",
    "bayesian_outer_fold_metrics.csv",
    "bayesian_overall_metrics.csv",
    "execution_audit.json",
    "execution_contract_frozen.json",
    "firth_flic_diagnostic.csv",
    "pair_evidence_posterior_summary.csv",
    "posterior_diagnostics.csv",
    "posterior_parameter_summary.csv",
    "prior_predictive_audit.json",
    "separation_trigger_audit.json",
    "validation_audit.json",
}
EXPECTED_RELATIVE_FILES = set(TOP_LEVEL_RESULT_FILES)
for fold in FOLDS:
    for model_id in MODELS:
        EXPECTED_RELATIVE_FILES.update(
            {
                f"fold_checkpoints/{model_id}_fold{fold}.json",
                f"fold_checkpoints/{model_id}_fold{fold}_parameters.csv",
                f"fold_checkpoints/{model_id}_fold{fold}_predictions.csv",
                f"posterior_samples/{model_id}_fold{fold}_attempt1.nc",
            }
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def parse_declared_sha(path: Path) -> str:
    fields = path.read_text(encoding="utf-8").strip().split()
    if not fields or len(fields[0]) != 64 or any(character not in "0123456789abcdefABCDEF" for character in fields[0]):
        raise ValueError("external SHA256 declaration is invalid")
    return fields[0].lower()


def parse_run_summary(path: Path) -> dict[str, str]:
    summary: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            summary[key.strip()] = value.strip()
    return summary


def verify_run_summary(path: Path, zip_path: Path, zip_hash: str, member_count: int) -> dict[str, str]:
    summary = parse_run_summary(path)
    if summary.get("status") != "COMPLETE":
        raise RuntimeError("run summary does not report COMPLETE")
    if summary.get("final_export_sha256", "").lower() != zip_hash:
        raise RuntimeError("run summary ZIP SHA256 mismatch")
    if int(summary.get("final_export_size_bytes", "-1")) != zip_path.stat().st_size:
        raise RuntimeError("run summary ZIP size mismatch")
    if int(summary.get("final_export_members", "-1")) != member_count:
        raise RuntimeError("run summary member count mismatch")
    return summary


def expected_inventory() -> set[str]:
    return set(EXPECTED_RELATIVE_FILES)


def archive_inventory(archive: zipfile.ZipFile) -> list[str]:
    relative_files: list[str] = []
    for info in archive.infolist():
        if info.is_dir():
            continue
        path = PurePosixPath(info.filename)
        if not info.filename.startswith(PREFIX) or path.is_absolute() or ".." in path.parts:
            raise RuntimeError(f"unsafe or unexpected ZIP member: {info.filename}")
        relative = info.filename[len(PREFIX):]
        if not relative:
            raise RuntimeError("empty result member path")
        relative_files.append(relative)
    expected = expected_inventory()
    observed = set(relative_files)
    if observed != expected or len(relative_files) != len(expected):
        difference = sorted(observed ^ expected)
        raise RuntimeError(f"unexpected result inventory: {difference}; member_count={len(relative_files)}")
    return relative_files


def extract_results(archive: zipfile.ZipFile, result_root: Path, relative_files: Iterable[str]) -> None:
    for relative in relative_files:
        target = result_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(PREFIX + relative))


def verify_internal_checksums(result_root: Path) -> tuple[int, list[str]]:
    manifest = result_root / "CHECKSUMS.sha256"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    failures: list[str] = []
    observed: list[str] = []
    for line in lines:
        fields = line.split("  ", 1)
        if len(fields) != 2:
            raise RuntimeError("malformed internal checksum line")
        expected, relative = fields
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError(f"unsafe internal checksum path: {relative}")
        observed.append(relative)
        target = result_root / relative
        if not target.is_file() or sha256(target) != expected:
            failures.append(relative)
    expected_files = expected_inventory() - {"CHECKSUMS.sha256"}
    if set(observed) != expected_files or len(observed) != len(expected_files):
        failures.append("CHECKSUMS.sha256:inventory")
    return len(lines), failures


def normalized_evaluation_weights(probabilities: np.ndarray) -> np.ndarray:
    values = np.asarray(probabilities, dtype=float)
    if np.any(~np.isfinite(values)) or np.any(values <= 0):
        raise ValueError("invalid evaluation inclusion probability")
    raw = 1.0 / values
    return raw / raw.mean()


def recompute_metric_row(
    rows: Iterable[dict[str, object]], model_id: str, outer_fold: int | None = None
) -> dict[str, object]:
    records = list(rows)
    y = np.asarray([float(row["review_ready_label"]) for row in records], dtype=float)
    probability = np.asarray([float(row["posterior_mean_probability"]) for row in records], dtype=float)
    inclusion = np.asarray([float(row["first_order_inclusion_probability"]) for row in records], dtype=float)
    weights = normalized_evaluation_weights(inclusion)
    clipped = np.clip(probability, EPS, 1.0 - EPS)
    result: dict[str, object] = {"model_id": model_id}
    if outer_fold is not None:
        result["outer_fold"] = outer_fold
    result.update(
        {
            "pair_count": len(records),
            "weighted_brier": float(np.average((y - probability) ** 2, weights=weights)),
            "weighted_log_loss": float(
                np.average(-(y * np.log(clipped) + (1.0 - y) * np.log(1.0 - clipped)), weights=weights)
            ),
            "minimum_probability": float(probability.min()),
            "maximum_probability": float(probability.max()),
        }
    )
    return result


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _metric_close(recomputed: dict[str, object], reported: pd.Series) -> bool:
    return all(
        math.isclose(float(recomputed[field]), float(reported[field]), rel_tol=0.0, abs_tol=1e-12)
        for field in ("weighted_brier", "weighted_log_loss", "minimum_probability", "maximum_probability")
    )


def _parse_image_offset_rhat(value: object) -> float | None:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    parsed = ast.literal_eval(text)
    return float(parsed["max_rhat"])


def verify_task15e_binding(task15e_freeze: Path) -> dict[str, object]:
    audit_path = task15e_freeze / "freeze_audit.json"
    disposition_path = task15e_freeze / "development_disposition.json"
    metrics_path = task15e_freeze / "results/overall_model_metrics.csv"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    disposition = json.loads(disposition_path.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS":
        raise RuntimeError("Task15E freeze audit did not pass")
    if disposition.get("status") != "FROZEN_COMPLETE_WITHOUT_FINAL_MODEL_QUALIFICATION":
        raise RuntimeError("Task15E disposition is not the required frozen state")
    metrics = pd.read_csv(metrics_path).set_index("model_id")
    if "P5" not in metrics.index:
        raise RuntimeError("Task15E P5 metrics are missing")
    return {
        "freeze_audit_sha256": sha256(audit_path),
        "development_disposition_sha256": sha256(disposition_path),
        "overall_model_metrics_sha256": sha256(metrics_path),
        "P5_weighted_brier": float(metrics.loc["P5", "weighted_brier"]),
        "P5_weighted_log_loss": float(metrics.loc["P5", "weighted_log_loss"]),
    }


def independent_analysis(result_root: Path, task15e_freeze: Path) -> dict[str, object]:
    predictions = pd.read_csv(result_root / "bayesian_oof_predictions.csv")
    reported_overall = pd.read_csv(result_root / "bayesian_overall_metrics.csv").set_index("model_id")
    reported_folds = pd.read_csv(result_root / "bayesian_outer_fold_metrics.csv").set_index(["model_id", "outer_fold"])
    diagnostics = pd.read_csv(result_root / "posterior_diagnostics.csv")
    parameters = pd.read_csv(result_root / "posterior_parameter_summary.csv")
    pair_evidence = pd.read_csv(result_root / "pair_evidence_posterior_summary.csv")
    firth = pd.read_csv(result_root / "firth_flic_diagnostic.csv")
    task15e = verify_task15e_binding(task15e_freeze)
    failures: list[str] = []

    required = {
        "canonical_pair_id",
        "pair_execution_id",
        "component_id",
        "outer_fold",
        "model_id",
        "review_ready_label",
        "first_order_inclusion_probability",
        "posterior_mean_probability",
        "brier_loss",
    }
    if not required.issubset(predictions.columns):
        raise RuntimeError("Bayesian OOF prediction schema is incomplete")
    if len(predictions) != 890:
        failures.append("prediction_row_count")
    if predictions.duplicated(["canonical_pair_id", "model_id"]).any():
        failures.append("duplicate_pair_model")
    if predictions["canonical_pair_id"].nunique() != 445:
        failures.append("pair_coverage")
    if predictions["component_id"].nunique() != 116:
        failures.append("component_coverage")
    if set(predictions["model_id"]) != set(MODELS):
        failures.append("model_coverage")
    if set(pd.to_numeric(predictions["outer_fold"], errors="coerce").dropna().astype(int)) != set(FOLDS):
        failures.append("fold_coverage")
    probability = pd.to_numeric(predictions["posterior_mean_probability"], errors="coerce")
    inclusion = pd.to_numeric(predictions["first_order_inclusion_probability"], errors="coerce")
    if probability.isna().any() or not probability.between(0.0, 1.0).all():
        failures.append("invalid_probability")
    if inclusion.isna().any() or (inclusion <= 0).any():
        failures.append("invalid_inclusion_probability")
    computed_loss = (pd.to_numeric(predictions["review_ready_label"]) - probability) ** 2
    if not np.allclose(computed_loss, pd.to_numeric(predictions["brier_loss"]), atol=1e-12, rtol=0.0):
        failures.append("brier_loss_mismatch")
    consistency_columns = ["review_ready_label", "first_order_inclusion_probability", "component_id", "outer_fold"]
    if any(predictions.groupby("canonical_pair_id")[column].nunique().max() != 1 for column in consistency_columns):
        failures.append("pair_metadata_inconsistent_across_models")

    recomputed: dict[str, dict[str, object]] = {}
    fold_rows: list[dict[str, object]] = []
    for model_id in MODELS:
        model_rows = predictions.loc[predictions["model_id"] == model_id].to_dict("records")
        metric = recompute_metric_row(model_rows, model_id)
        recomputed[model_id] = metric
        if model_id not in reported_overall.index or not _metric_close(metric, reported_overall.loc[model_id]):
            failures.append(f"overall_metric_recompute:{model_id}")
        for fold in FOLDS:
            subset = predictions.loc[
                (predictions["model_id"] == model_id) & (predictions["outer_fold"] == fold)
            ].to_dict("records")
            fold_metric = recompute_metric_row(subset, model_id, fold)
            fold_rows.append(fold_metric)
            if (model_id, fold) not in reported_folds.index or not _metric_close(
                fold_metric, reported_folds.loc[(model_id, fold)]
            ):
                failures.append(f"fold_metric_recompute:{model_id}:{fold}")

    folds = {(str(row["model_id"]), int(row["outer_fold"])): row for row in fold_rows}
    fold_deltas = []
    for fold in FOLDS:
        s3 = folds[("S3", fold)]
        s4 = folds[("S4", fold)]
        fold_deltas.append(
            {
                "outer_fold": fold,
                "S3_minus_S4_weighted_brier": float(s3["weighted_brier"]) - float(s4["weighted_brier"]),
                "S3_minus_S4_weighted_log_loss": float(s3["weighted_log_loss"]) - float(s4["weighted_log_loss"]),
            }
        )

    expected_diagnostics = {(model, fold) for model in MODELS for fold in FOLDS}
    observed_diagnostics = {
        (str(row.model_id), int(row.outer_fold)) for row in diagnostics.itertuples(index=False)
    }
    if len(diagnostics) != 10 or observed_diagnostics != expected_diagnostics or set(diagnostics["status"]) != {"PASS"}:
        failures.append("posterior_diagnostic_coverage")
    if int(pd.to_numeric(diagnostics["divergences"]).sum()) != 0:
        failures.append("posterior_divergences")
    if set(pd.to_numeric(diagnostics["accepted_attempt"]).astype(int)) != {1}:
        failures.append("unexpected_posterior_retry")
    image_offset_rhats = [
        parsed
        for parsed in (_parse_image_offset_rhat(value) for value in diagnostics["image_offset_diagnostics"])
        if parsed is not None
    ]

    coverage = pair_evidence.loc[pair_evidence["parameter"] == "local_match_coverage_fraction__z"].copy()
    expected_coverage = {(model, fold) for model in MODELS for fold in FOLDS}
    observed_coverage = {(str(row.model_id), int(row.outer_fold)) for row in coverage.itertuples(index=False)}
    if len(coverage) != 10 or observed_coverage != expected_coverage:
        failures.append("pair_evidence_coverage")
    positive_means = int((pd.to_numeric(coverage["mean"]) > 0).sum())
    crossing_zero = int(
        ((pd.to_numeric(coverage["lower_95"]) <= 0) & (pd.to_numeric(coverage["upper_95"]) >= 0)).sum()
    )

    sigma = parameters.loc[(parameters["model_id"] == "S4") & (parameters["parameter"] == "sigma_image")].copy()
    if len(sigma) != 5 or set(pd.to_numeric(sigma["outer_fold"]).astype(int)) != set(FOLDS):
        failures.append("sigma_image_coverage")

    selection_true = firth["selection_eligible"].astype(str).str.lower().isin({"true", "1", "yes"})
    s5_folds = sorted(pd.to_numeric(firth["outer_fold"], errors="coerce").dropna().astype(int).unique().tolist())
    if firth.empty or s5_folds != [0, 4] or selection_true.any():
        failures.append("S5_role_or_coverage")

    s3_brier = float(recomputed["S3"]["weighted_brier"])
    s4_brier = float(recomputed["S4"]["weighted_brier"])
    s3_log_loss = float(recomputed["S3"]["weighted_log_loss"])
    s4_log_loss = float(recomputed["S4"]["weighted_log_loss"])
    p5_brier = float(task15e["P5_weighted_brier"])
    p5_log_loss = float(task15e["P5_weighted_log_loss"])
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "prediction_rows": len(predictions),
        "unique_pairs": int(predictions["canonical_pair_id"].nunique()),
        "unique_components": int(predictions["component_id"].nunique()),
        "label_counts": {
            str(key): int(value)
            for key, value in predictions.drop_duplicates("canonical_pair_id")["review_ready_label"].value_counts().sort_index().items()
        },
        "recomputed_metrics": recomputed,
        "S3_minus_S4_weighted_brier": s3_brier - s4_brier,
        "S3_minus_S4_relative_brier_percent": 100.0 * (s3_brier - s4_brier) / s3_brier,
        "S3_minus_S4_weighted_log_loss": s3_log_loss - s4_log_loss,
        "S3_vs_P5_relative_brier_improvement_percent": 100.0 * (p5_brier - s3_brier) / p5_brier,
        "S4_vs_P5_relative_brier_improvement_percent": 100.0 * (p5_brier - s4_brier) / p5_brier,
        "S3_vs_P5_relative_log_loss_improvement_percent": 100.0 * (p5_log_loss - s3_log_loss) / p5_log_loss,
        "S4_vs_P5_relative_log_loss_improvement_percent": 100.0 * (p5_log_loss - s4_log_loss) / p5_log_loss,
        "fold_diagnostics": fold_deltas,
        "posterior_diagnostics": {
            "fit_count": len(diagnostics),
            "divergences": int(pd.to_numeric(diagnostics["divergences"]).sum()),
            "accepted_attempts": sorted(pd.to_numeric(diagnostics["accepted_attempt"]).astype(int).unique().tolist()),
            "maximum_fixed_rhat": float(pd.to_numeric(diagnostics["fixed_max_rhat"]).max()),
            "minimum_fixed_bulk_ess": float(pd.to_numeric(diagnostics["fixed_min_bulk_ess"]).min()),
            "minimum_fixed_tail_ess": float(pd.to_numeric(diagnostics["fixed_min_tail_ess"]).min()),
            "maximum_image_offset_rhat": max(image_offset_rhats) if image_offset_rhats else None,
        },
        "pair_evidence": {
            "coverage_parameter_records": len(coverage),
            "positive_posterior_means": positive_means,
            "credible_intervals_crossing_zero": crossing_zero,
            "posterior_probability_gt_zero_minimum": float(pd.to_numeric(coverage["posterior_probability_gt_zero"]).min()),
            "posterior_probability_gt_zero_maximum": float(pd.to_numeric(coverage["posterior_probability_gt_zero"]).max()),
        },
        "shared_image_dependence": {
            "sigma_image_records": len(sigma),
            "posterior_mean_minimum": float(pd.to_numeric(sigma["mean"]).min()),
            "posterior_mean_maximum": float(pd.to_numeric(sigma["mean"]).max()),
            "lower_95_minimum": float(pd.to_numeric(sigma["lower_95"]).min()),
            "lower_95_maximum": float(pd.to_numeric(sigma["lower_95"]).max()),
        },
        "S5_diagnostic": {
            "prediction_rows": len(firth),
            "outer_folds": s5_folds,
            "selection_eligible_rows": int(selection_true.sum()),
        },
        "task15e_binding": task15e,
    }


def validate_upstream_results(result_root: Path) -> None:
    validation = json.loads((result_root / "validation_audit.json").read_text(encoding="utf-8"))
    execution = json.loads((result_root / "execution_audit.json").read_text(encoding="utf-8"))
    prior = json.loads((result_root / "prior_predictive_audit.json").read_text(encoding="utf-8"))
    marginal = json.loads((result_root / "S4_marginalization_audit.json").read_text(encoding="utf-8"))
    contract_path = result_root / "execution_contract_frozen.json"
    if validation.get("status") != "PASS" or validation.get("failures") != []:
        raise RuntimeError("upstream validation did not pass")
    if execution.get("prediction_rows") != 890 or execution.get("posterior_fold_fits") != 10:
        raise RuntimeError("execution audit coverage mismatch")
    if execution.get("locked_stage_outcomes_accessed") is not False:
        raise RuntimeError("locked-stage access audit failure")
    if execution.get("contract_sha256") != sha256(contract_path):
        raise RuntimeError("execution contract hash mismatch")
    if prior.get("status") != "PASS" or len(prior.get("checks", [])) != 10:
        raise RuntimeError("prior-predictive audit did not pass")
    if marginal.get("status") != "PASS" or len(marginal.get("checks", [])) != 5:
        raise RuntimeError("S4 marginalization audit did not pass")


def report_text(analysis: dict[str, object], zip_hash: str) -> str:
    metrics = analysis["recomputed_metrics"]
    s3 = metrics["S3"]
    s4 = metrics["S4"]
    posterior = analysis["posterior_diagnostics"]
    evidence = analysis["pair_evidence"]
    dependence = analysis["shared_image_dependence"]
    s5 = analysis["S5_diagnostic"]
    fold_rows = analysis["fold_diagnostics"]
    s4_brier_folds = sum(float(row["S3_minus_S4_weighted_brier"]) > 0 for row in fold_rows)
    s3_brier_folds = sum(float(row["S3_minus_S4_weighted_brier"]) < 0 for row in fold_rows)
    return f"""# PF-ERI v2 Task 15F Bayesian Sensitivity Result Freeze

Status: `FROZEN_COMPLETE_WITHOUT_FINAL_MODEL_SELECTION`

## Scope and integrity

This record freezes the completed Task 15F development-only mathematical sensitivity analysis. The original ModelScope export has SHA256 `{zip_hash}`. Its external declaration, run summary, ZIP CRC, 54 internal checksums, 55-member inventory, 890 out-of-fold predictions, 445 unique development pairs, 116 endpoint-image components, ten posterior fits, five S4 marginalization records, and the triggered S5 diagnostic were independently verified. The analysis used no calibration, deployment-confirmation, or mechanism-confirmation outcome.

## Posterior computation

All ten S3 and S4 fits passed on their first prespecified sampling attempt with zero post-tuning divergences. The maximum fixed-parameter rank-normalized R-hat was {float(posterior['maximum_fixed_rhat']):.6f}; the minimum fixed-parameter bulk and tail effective sample sizes were {float(posterior['minimum_fixed_bulk_ess']):.1f} and {float(posterior['minimum_fixed_tail_ess']):.1f}, respectively. The maximum image-offset R-hat was {float(posterior['maximum_image_offset_rhat']):.6f}. These values pass the frozen computational gates and support interpretation of the retained posterior summaries. They do not establish external predictive validity.

## Predictive sensitivity

S3 obtained a design-weighted Brier score of {float(s3['weighted_brier']):.9f} and weighted log loss of {float(s3['weighted_log_loss']):.9f}. S4 obtained a weighted Brier score of {float(s4['weighted_brier']):.9f} and weighted log loss of {float(s4['weighted_log_loss']):.9f}. The difference defined as S3 minus S4 was {float(analysis['S3_minus_S4_weighted_brier']):.9f} for Brier score and {float(analysis['S3_minus_S4_weighted_log_loss']):.9f} for log loss. S3 had lower Brier loss in {s3_brier_folds} outer folds and S4 in {s4_brier_folds}; the pooled metrics also split direction across the two proper scores. Relative to the frozen Task 15E P5 result, S3 and S4 reduced development Brier descriptively by {float(analysis['S3_vs_P5_relative_brier_improvement_percent']):.3f}% and {float(analysis['S4_vs_P5_relative_brier_improvement_percent']):.3f}%. These comparisons show that regularized Bayesian fitting changes development predictions materially, but the frozen contract prohibits choosing the final model by the lowest Task 15F development loss.

## Pair evidence and endpoint dependence

The standardized local-match coverage coefficient had a positive posterior mean in {int(evidence['positive_posterior_means'])} of {int(evidence['coverage_parameter_records'])} model-by-fold summaries. Its 95% credible interval crossed zero in {int(evidence['credible_intervals_crossing_zero'])} of {int(evidence['coverage_parameter_records'])} summaries, while the posterior probability of a positive coefficient ranged from {float(evidence['posterior_probability_gt_zero_minimum']):.3f} to {float(evidence['posterior_probability_gt_zero_maximum']):.3f}. The direction is therefore coherent, but the development data do not isolate a precise and fold-stable local-match increment.

The S4 image-level standard deviation had posterior means from {float(dependence['posterior_mean_minimum']):.3f} to {float(dependence['posterior_mean_maximum']):.3f}, with fold-specific 95% lower bounds from {float(dependence['lower_95_minimum']):.3f} to {float(dependence['lower_95_maximum']):.3f}. This pattern indicates material endpoint-image heterogeneity under the frozen half-normal prior and justifies retaining dependence-aware uncertainty as a scientific limitation. However, honest population-marginal prediction for two unseen endpoints did not produce a stable Brier advantage over S3.

## Separation diagnostic

The prespecified S5 trigger produced {int(s5['prediction_rows'])} Firth/FLIC diagnostic predictions in outer folds 0 and 4. No S5 row was selection-eligible. This diagnostic confirms that classical unpenalized fitting encountered instability in the declared folds, while the weak-prior Bayesian models remained computationally stable. Because the numerical S5 trigger thresholds were recorded after development outcomes opened, S5 cannot participate in final route selection.

## Binding decision

Task 15F is complete and must not be rerun, reprioritized, or selectively replaced in response to these results. S3, S4, and S5 remain mathematical sensitivities and are not confirmation-eligible routes. No final development model is selected by this freeze, and the calibration and confirmation outcomes remain locked. The next authorized task is Task 15G, which applies the already registered E1, E2, and E3 exploratory performance-bound roles under a separately frozen execution contract. Task 15H must subsequently apply qualification before performance and produce the validated development-model freeze record required to open calibration.
"""


def freeze(
    zip_path: Path,
    sha_path: Path,
    summary_path: Path,
    task15e_freeze: Path,
    output_dir: Path,
) -> dict[str, object]:
    zip_path, sha_path, summary_path, task15e_freeze, output_dir = map(
        Path.resolve, [zip_path, sha_path, summary_path, task15e_freeze, output_dir]
    )
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing freeze: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    declared = parse_declared_sha(sha_path)
    actual = sha256(zip_path)
    if declared != actual:
        raise RuntimeError("external ZIP SHA256 mismatch")

    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC failure")
        inventory = archive_inventory(archive)
        verify_run_summary(summary_path, zip_path, actual, len(inventory))
        with tempfile.TemporaryDirectory(dir=output_dir.parent, prefix=".task15f_result_freeze_") as temporary:
            stage = Path(temporary) / output_dir.name
            source = stage / "source_delivery"
            results = stage / "results"
            source.mkdir(parents=True)
            results.mkdir()
            shutil.copy2(zip_path, source / zip_path.name)
            shutil.copy2(sha_path, source / sha_path.name)
            shutil.copy2(summary_path, source / summary_path.name)
            extract_results(archive, results, inventory)

            checksum_count, checksum_failures = verify_internal_checksums(results)
            if checksum_failures:
                raise RuntimeError(f"internal checksum failures: {checksum_failures}")
            validate_upstream_results(results)
            analysis = independent_analysis(results, task15e_freeze)
            if analysis["status"] != "PASS":
                raise RuntimeError(f"independent analysis failed: {analysis['failures']}")
            write_json(stage / "independent_recalculation.json", analysis)

            disposition = {
                "record_version": "pferi_v2_task15f_bayesian_sensitivity_result_freeze_v1",
                "status": "FROZEN_COMPLETE_WITHOUT_FINAL_MODEL_SELECTION",
                "task15f_execution": "PASS",
                "task15f_output_integrity": "PASS",
                "posterior_computation": "PASS",
                "S3_role": "MATHEMATICAL_SENSITIVITY_NOT_CONFIRMATION_ELIGIBLE",
                "S4_role": "MATHEMATICAL_SENSITIVITY_NOT_CONFIRMATION_ELIGIBLE",
                "S5_role": "TRIGGERED_DIAGNOSTIC_ONLY_NOT_SELECTION_ELIGIBLE",
                "pair_evidence_disposition": "POSITIVE_DIRECTION_WITH_FOLD_LEVEL_UNCERTAINTY",
                "shared_image_dependence_disposition": "MATERIAL_HETEROGENEITY_WITHOUT_STABLE_BRIER_ADVANTAGE",
                "final_model_selected": False,
                "locked_stages": ["calibration", "deployment_confirmation", "mechanism_confirmation"],
                "prohibited_after_freeze": [
                    "Task15F rerun for a more favorable result",
                    "prior changes informed by Task15F outcomes",
                    "promotion of S3, S4, or S5 to confirmation eligibility",
                    "access to locked-stage outcomes",
                ],
                "next_authorized_task": "Task15G exploratory performance-bound benchmark",
            }
            write_json(stage / "task15f_disposition.json", disposition)
            (stage / "TASK15F_BAYESIAN_SENSITIVITY_RESULT_FREEZE_REPORT.md").write_text(
                report_text(analysis, actual), encoding="utf-8"
            )
            shutil.copy2(Path(__file__), stage / "freeze_builder_snapshot.py")
            audit = {
                "status": "PASS",
                "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_zip_sha256": actual,
                "source_zip_size_bytes": zip_path.stat().st_size,
                "source_zip_member_count": len(inventory),
                "internal_checksum_count": checksum_count,
                "internal_checksum_failures": checksum_failures,
                "independent_recalculation_status": analysis["status"],
                "prediction_rows": analysis["prediction_rows"],
                "unique_pairs": analysis["unique_pairs"],
                "unique_components": analysis["unique_components"],
                "posterior_fit_count": analysis["posterior_diagnostics"]["fit_count"],
                "locked_stage_outcomes_accessed": False,
                "final_model_selected": False,
                "disposition": disposition["status"],
            }
            write_json(stage / "freeze_audit.json", audit)
            checksum_targets = sorted(
                path for path in stage.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256"
            )
            (stage / "CHECKSUMS.sha256").write_text(
                "".join(f"{sha256(path)}  {path.relative_to(stage)}\n" for path in checksum_targets),
                encoding="utf-8",
            )
            shutil.move(str(stage), output_dir)
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=FULL_RUN / "source_delivery/PF_ERI_TASK15F_FINAL_EXPORT.zip")
    parser.add_argument("--sha256", type=Path, default=FULL_RUN / "source_delivery/PF_ERI_TASK15F_FINAL_EXPORT.sha256")
    parser.add_argument("--summary", type=Path, default=FULL_RUN / "source_delivery/PF_ERI_TASK15F_RUN_SUMMARY.txt")
    parser.add_argument("--task15e-freeze", type=Path, default=TASK15E_FREEZE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        audit = freeze(args.zip, args.sha256, args.summary, args.task15e_freeze, args.output_dir)
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2))
        return 1
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
