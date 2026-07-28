#!/usr/bin/env python3
"""Verify and immutably freeze the external PF-ERI Task 15E result delivery."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-22_task15e_development_model_comparison_freeze_v1"
EXPECTED_FILES = {
    "CHECKSUMS.sha256",
    "DEVELOPMENT_COMPARISON_REPORT.md",
    "P3_P5_paired_brier_results.json",
    "coefficient_stability.csv",
    "component_paired_regret.csv",
    "execution_audit.json",
    "execution_contract_frozen.json",
    "inner_tuning_trace.csv",
    "model_oof_predictions.csv",
    "optimizer_diagnostics.csv",
    "outer_fold_metrics.csv",
    "overall_model_metrics.csv",
    "validation_audit.json",
}
MODELS = ["P0", "P1", "P2", "P3", "P4", "P5", "S1", "S2"]


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
    if not fields or len(fields[0]) != 64:
        raise ValueError("external SHA256 declaration is invalid")
    return fields[0].lower()


def verify_internal_checksums(result_root: Path) -> tuple[int, list[str]]:
    failures: list[str] = []
    lines = (result_root / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines()
    for line in lines:
        expected, relative = line.split("  ", 1)
        target = result_root / relative
        if not target.is_file() or sha256(target) != expected:
            failures.append(relative)
    return len(lines), failures


def load_csv(result_root: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(result_root / name)


def independent_analysis(result_root: Path) -> dict[str, object]:
    predictions = load_csv(result_root, "model_oof_predictions.csv")
    diagnostics = load_csv(result_root, "optimizer_diagnostics.csv")
    reported = load_csv(result_root, "overall_model_metrics.csv").set_index("model_id")
    failures: list[str] = []
    required = {
        "canonical_pair_id", "pair_execution_id", "component_id", "outer_fold",
        "model_id", "review_ready_label", "first_order_inclusion_probability",
        "probability", "brier_loss",
    }
    if not required.issubset(predictions.columns):
        raise RuntimeError("OOF prediction schema is incomplete")
    if len(predictions) != 445 * len(MODELS): failures.append("prediction_row_count")
    if predictions.duplicated(["canonical_pair_id", "model_id"]).any(): failures.append("duplicate_pair_model")
    if predictions["canonical_pair_id"].nunique() != 445: failures.append("pair_coverage")
    if set(predictions["model_id"]) != set(MODELS): failures.append("model_coverage")
    probability = pd.to_numeric(predictions["probability"], errors="coerce")
    if probability.isna().any() or not probability.between(0.0, 1.0).all(): failures.append("invalid_probability")
    if len(diagnostics) != 40 or not diagnostics["optimizer_success"].astype(bool).all(): failures.append("optimizer_diagnostic")

    metadata = predictions.drop_duplicates("canonical_pair_id").set_index("canonical_pair_id")
    losses = predictions.pivot(index="canonical_pair_id", columns="model_id", values="brier_loss")
    probabilities = predictions.pivot(index="canonical_pair_id", columns="model_id", values="probability")
    metadata = metadata.loc[losses.index]
    weights = 1.0 / metadata["first_order_inclusion_probability"].to_numpy(float)
    recomputed: dict[str, dict[str, float]] = {}
    for model_id in MODELS:
        group = predictions.loc[predictions["model_id"] == model_id]
        y = group["review_ready_label"].to_numpy(float)
        p = group["probability"].to_numpy(float)
        w = 1.0 / group["first_order_inclusion_probability"].to_numpy(float)
        brier = float(np.average((y - p) ** 2, weights=w))
        log_loss = float(np.average(-(y * np.log(p) + (1 - y) * np.log(1 - p)), weights=w))
        recomputed[model_id] = {"weighted_brier": brier, "weighted_log_loss": log_loss}
        if abs(brier - float(reported.loc[model_id, "weighted_brier"])) > 1e-12: failures.append(f"brier_recompute:{model_id}")
        if abs(log_loss - float(reported.loc[model_id, "weighted_log_loss"])) > 1e-12: failures.append(f"logloss_recompute:{model_id}")

    delta_p3_p5 = (losses["P3"] - losses["P5"]).to_numpy(float)
    delta_s1_s2 = (losses["S1"] - losses["S2"]).to_numpy(float)
    p3_p5 = float(np.average(delta_p3_p5, weights=weights))
    s1_s2 = float(np.average(delta_s1_s2, weights=weights))
    component_rows: list[dict[str, object]] = []
    for component_id, indices in metadata.groupby("component_id").groups.items():
        locations = metadata.index.get_indexer(indices)
        component_weights = weights[locations]
        component_rows.append({
            "component_id": component_id,
            "weight": float(component_weights.sum()),
            "p3_p5_numerator": float(np.sum(component_weights * delta_p3_p5[locations])),
            "s1_s2_numerator": float(np.sum(component_weights * delta_s1_s2[locations])),
            "pair_count": len(locations),
        })
    components = pd.DataFrame(component_rows)
    rng = np.random.default_rng(1501)
    bootstrap_p3_p5 = np.empty(20000)
    bootstrap_s1_s2 = np.empty(20000)
    for index in range(20000):
        counts = np.bincount(rng.integers(0, len(components), len(components)), minlength=len(components))
        denominator = float(np.sum(counts * components["weight"]))
        bootstrap_p3_p5[index] = float(np.sum(counts * components["p3_p5_numerator"]) / denominator)
        bootstrap_s1_s2[index] = float(np.sum(counts * components["s1_s2_numerator"]) / denominator)

    fold_rows: list[dict[str, object]] = []
    total_numerator = float(np.sum(weights * delta_p3_p5))
    for fold, indices in metadata.groupby("outer_fold").groups.items():
        locations = metadata.index.get_indexer(indices)
        fold_weights = weights[locations]
        numerator = float(np.sum(fold_weights * delta_p3_p5[locations]))
        fold_rows.append({
            "outer_fold": int(fold),
            "pair_count": len(locations),
            "p3_minus_p5_weighted_brier": float(numerator / fold_weights.sum()),
            "fraction_of_global_p3_p5_delta": float(numerator / total_numerator),
            "p3_probability_sd": float(probabilities["P3"].to_numpy()[locations].std()),
            "p5_probability_sd": float(probabilities["P5"].to_numpy()[locations].std()),
        })

    lambda_map = diagnostics.loc[diagnostics["model_id"] != "P0"].pivot(index="outer_fold", columns="model_id", values="lambda")
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "prediction_rows": len(predictions),
        "unique_pairs": int(metadata.shape[0]),
        "unique_components": int(metadata["component_id"].nunique()),
        "label_counts": {str(k): int(v) for k, v in metadata["review_ready_label"].value_counts().sort_index().items()},
        "ipw_kish_effective_sample_size": float(weights.sum() ** 2 / np.sum(weights ** 2)),
        "recomputed_metrics": recomputed,
        "p3_minus_p5_weighted_brier": p3_p5,
        "p3_minus_p5_relative_percent": float(100 * p3_p5 / recomputed["P3"]["weighted_brier"]),
        "p3_p5_posthoc_component_bootstrap_95_interval": np.quantile(bootstrap_p3_p5, [0.025, 0.975]).tolist(),
        "s1_minus_s2_weighted_brier": s1_s2,
        "s1_s2_posthoc_component_bootstrap_95_interval": np.quantile(bootstrap_s1_s2, [0.025, 0.975]).tolist(),
        "fold_diagnostics": fold_rows,
        "selected_lambdas": {model: {str(int(fold)): float(value) for fold, value in values.items()} for model, values in lambda_map.to_dict().items()},
    }


def report_text(analysis: dict[str, object], zip_hash: str) -> str:
    metrics = analysis["recomputed_metrics"]
    p3 = metrics["P3"]; p5 = metrics["P5"]; s1 = metrics["S1"]; s2 = metrics["S2"]
    p3_brier = float(p3["weighted_brier"]); p5_brier = float(p5["weighted_brier"])
    s1_brier = float(s1["weighted_brier"]); s2_brier = float(s2["weighted_brier"])
    p3_p5_delta = float(analysis["p3_minus_p5_weighted_brier"])
    p3_p5_relative = float(analysis["p3_minus_p5_relative_percent"])
    s1_s2_delta = float(analysis["s1_minus_s2_weighted_brier"])
    bootstrap_interval = analysis["p3_p5_posthoc_component_bootstrap_95_interval"]
    bootstrap_lower = float(bootstrap_interval[0]); bootstrap_upper = float(bootstrap_interval[1])
    return f"""# PF-ERI v2 Task 15E Development Model Comparison Freeze

Status: `FROZEN_COMPLETE_WITHOUT_FINAL_MODEL_QUALIFICATION`

## Scope and integrity

This record freezes the completed Task 15E development-only comparison. The original ModelScope export has SHA256 `{zip_hash}`. Its external checksum, ZIP CRC, twelve internal checksums, five outer folds, 3,560 out-of-fold predictions, 445 unique development pairs, and 40 optimizer records were independently verified. No calibration, deployment-confirmation, or mechanism-confirmation outcome is authorized or represented by this freeze.

## Frozen result

The active-control ridge model P3 obtained a design-weighted Brier score of {p3_brier:.9f}, whereas the full ridge model P5 obtained {p5_brier:.9f}. The frozen paired difference, defined as Brier(P3) minus Brier(P5), is {p3_p5_delta:.9f}, equal to only {p3_p5_relative:.4f}% of the P3 Brier score. The direction favors P5, but the magnitude does not constitute strong incremental development evidence for the pair-evidence block.

The restricted nonlinear control S1 obtained a weighted Brier score of {s1_brier:.9f}, and the nonlinear full model S2 obtained {s2_brier:.9f}. Their paired difference is {s1_s2_delta:.9f}. This pattern supports continued examination of restricted nonlinearity, but it does not isolate a strong or stable local-match contribution.

## Stability disposition

P3 and P5 selected lambda 100 in four of five outer folds and lambda 0.1 in the remaining fold. The resulting one-thousand-fold regularization swing violates the intended stable-regularization qualification. Approximately 94.7% of the global P3-minus-P5 improvement arose from outer fold 1, while the other folds were close to intercept-like predictions. The pooled calibration values therefore must not be used to hide fold-level degeneracy.

The post hoc endpoint-component bootstrap interval for P3 minus P5 was [{bootstrap_lower:.9f}, {bootstrap_upper:.9f}]. This interval is an explicitly descriptive influence analysis created after development outcomes were open; it is not the preregistered deployment-confirmation interval and cannot be used for a confirmatory pass decision.

## Binding decision

Task 15E is complete and must not be rerun, retuned, or selectively replaced in response to these outcomes. Engineering validity and output completeness pass. P5 is not qualified as the final route because its incremental pair-evidence advantage is negligible and regularization is unstable. S2 is not promoted directly to the final route because its calibration and incremental S1 comparison remain insufficient. Final model selection stays open for the previously registered Task 15F mathematical sensitivities, Task 15G exploratory performance-bound challenge, and Task 15H qualification-before-performance freeze.
"""


def freeze(zip_path: Path, sha_path: Path, summary_path: Path, output_dir: Path) -> dict[str, object]:
    zip_path, sha_path, summary_path, output_dir = map(Path.resolve, [zip_path, sha_path, summary_path, output_dir])
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing freeze: {output_dir}")
    declared = parse_declared_sha(sha_path)
    actual = sha256(zip_path)
    if declared != actual:
        raise RuntimeError("external ZIP SHA256 mismatch")
    with tempfile.TemporaryDirectory(dir=output_dir.parent, prefix=".task15e_freeze_") as temporary:
        stage = Path(temporary) / output_dir.name
        stage.mkdir(parents=True)
        source = stage / "source_delivery"; results = stage / "results"
        source.mkdir(); results.mkdir()
        shutil.copy2(zip_path, source / zip_path.name)
        shutil.copy2(sha_path, source / sha_path.name)
        shutil.copy2(summary_path, source / summary_path.name)
        with zipfile.ZipFile(zip_path) as archive:
            if archive.testzip() is not None: raise RuntimeError("ZIP CRC failure")
            names = archive.namelist()
            prefix = "PF_ERI_TASK15E_RESULTS/"
            members = {Path(name).name for name in names if name.startswith(prefix) and not name.endswith("/")}
            if members != EXPECTED_FILES: raise RuntimeError(f"unexpected result inventory: {sorted(members ^ EXPECTED_FILES)}")
            for name in names:
                if name.startswith(prefix) and not name.endswith("/"):
                    target = results / Path(name).name
                    target.write_bytes(archive.read(name))
        checksum_count, checksum_failures = verify_internal_checksums(results)
        if checksum_failures: raise RuntimeError(f"internal checksum failures: {checksum_failures}")
        validation = json.loads((results / "validation_audit.json").read_text())
        execution = json.loads((results / "execution_audit.json").read_text())
        if validation.get("status") != "PASS" or validation.get("failures") != []: raise RuntimeError("upstream validation did not pass")
        if execution.get("prediction_rows") != 3560 or execution.get("outer_folds_executed") != [0, 1, 2, 3, 4]: raise RuntimeError("execution audit coverage mismatch")
        analysis = independent_analysis(results)
        if analysis["status"] != "PASS": raise RuntimeError(f"independent analysis failed: {analysis['failures']}")
        write_json(stage / "independent_recalculation.json", analysis)
        disposition = {
            "record_version": "pferi_v2_task15e_development_model_comparison_freeze_v1",
            "status": "FROZEN_COMPLETE_WITHOUT_FINAL_MODEL_QUALIFICATION",
            "task15e_execution": "PASS",
            "task15e_output_integrity": "PASS",
            "P5_strong_incremental_development_evidence": "NOT_SUPPORTED",
            "P5_final_route_qualification": "NOT_QUALIFIED",
            "S2_final_route_qualification": "NOT_QUALIFIED",
            "restricted_nonlinearity_signal": "CONTINUE_TO_REGISTERED_SENSITIVITY_STEPS",
            "prohibited_after_freeze": ["Task15E rerun for a prettier result", "lambda-grid retuning from observed outcomes", "promotion to confirmation claim", "access to locked-stage outcomes"],
            "next_authorized_task": "Task15F Bayesian/Firth mathematical sensitivity",
        }
        write_json(stage / "development_disposition.json", disposition)
        (stage / "TASK15E_DEVELOPMENT_MODEL_COMPARISON_FREEZE_REPORT.md").write_text(report_text(analysis, actual), encoding="utf-8")
        shutil.copy2(Path(__file__), stage / "freeze_builder_snapshot.py")
        audit = {
            "status": "PASS",
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_zip_sha256": actual,
            "source_zip_size_bytes": zip_path.stat().st_size,
            "source_zip_member_count": len(EXPECTED_FILES),
            "internal_checksum_count": checksum_count,
            "internal_checksum_failures": checksum_failures,
            "independent_recalculation_status": analysis["status"],
            "prediction_rows": analysis["prediction_rows"],
            "unique_pairs": analysis["unique_pairs"],
            "unique_components": analysis["unique_components"],
            "locked_stage_outcomes_accessed": False,
            "disposition": disposition["status"],
        }
        write_json(stage / "freeze_audit.json", audit)
        checksum_targets = sorted(p for p in stage.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
        (stage / "CHECKSUMS.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(stage)}\n" for path in checksum_targets), encoding="utf-8")
        shutil.move(str(stage), output_dir)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=Path("/Users/dshen/Desktop/PF_ERI_TASK15E_FINAL_EXPORT.zip"))
    parser.add_argument("--sha256", type=Path, default=Path("/Users/dshen/Desktop/PF_ERI_TASK15E_FINAL_EXPORT.sha256"))
    parser.add_argument("--summary", type=Path, default=Path("/Users/dshen/Desktop/PF_ERI_TASK15E_RUN_SUMMARY.txt"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        audit = freeze(args.zip, args.sha256, args.summary, args.output_dir)
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2)); return 1
    print(json.dumps(audit, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
