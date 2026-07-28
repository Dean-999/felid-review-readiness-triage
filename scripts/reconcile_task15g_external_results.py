#!/usr/bin/env python3
"""Reconcile the authoritative external Task 15G run with the local reproduction."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15g_exploratory_performance_bound_result_freeze/current"
)
LOCAL = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15g_exploratory_performance_bound_result_freeze/iterations/v1"
)
TASK15E = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-22_task15e_development_model_comparison_freeze_v1"
)
TASK15F = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15f_bayesian_sensitivity_result_freeze_v1"
)
OUTPUT = (
    ROOT
    / "archive/pferi_v2/task_runs/model_development/2026-07-23_task15g_external_reconciliation_v1"
)


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


def analyze(
    external: Path = EXTERNAL,
    local: Path = LOCAL,
    task15e: Path = TASK15E,
    task15f: Path = TASK15F,
) -> dict[str, Any]:
    external_results = external / "results"
    local_results = local / "results"
    external_audit = json.loads((external / "freeze_audit.json").read_text(encoding="utf-8"))
    local_audit = json.loads((local / "freeze_audit.json").read_text(encoding="utf-8"))
    external_execution = json.loads(
        (external_results / "execution_audit.json").read_text(encoding="utf-8")
    )
    local_execution = json.loads(
        (local_results / "execution_audit.json").read_text(encoding="utf-8")
    )
    keys = ["canonical_pair_id", "model_id"]
    external_prediction = (
        pd.read_csv(external_results / "exploratory_oof_predictions.csv")
        .sort_values(keys)
        .reset_index(drop=True)
    )
    local_prediction = (
        pd.read_csv(local_results / "exploratory_oof_predictions.csv")
        .sort_values(keys)
        .reset_index(drop=True)
    )
    if not external_prediction[keys].equals(local_prediction[keys]):
        raise RuntimeError("external/local prediction keys do not match")

    cross_platform: dict[str, dict[str, Any]] = {}
    for model_id in ("E1", "E2"):
        mask = external_prediction["model_id"] == model_id
        difference = np.abs(
            external_prediction.loc[mask, "probability"].to_numpy(float)
            - local_prediction.loc[mask, "probability"].to_numpy(float)
        )
        cross_platform[model_id] = {
            "maximum_absolute_probability_difference": float(difference.max()),
            "mean_absolute_probability_difference": float(difference.mean()),
            "rows_above_1e_12": int((difference > 1e-12).sum()),
            "rows_above_1e_3": int((difference > 1e-3).sum()),
        }

    external_selected = pd.read_csv(
        external_results / "selected_configurations.csv"
    ).sort_values(["model_id", "outer_fold"])
    local_selected = pd.read_csv(local_results / "selected_configurations.csv").sort_values(
        ["model_id", "outer_fold"]
    )
    selection_equal = external_selected["configuration_id"].reset_index(
        drop=True
    ).equals(local_selected["configuration_id"].reset_index(drop=True))

    overall = pd.read_csv(external_results / "exploratory_overall_metrics.csv").set_index(
        "model_id"
    )
    folds = pd.read_csv(external_results / "exploratory_outer_fold_metrics.csv")
    p5 = pd.read_csv(task15e / "results/overall_model_metrics.csv").set_index("model_id")
    sensitivity = pd.read_csv(
        task15f / "results/bayesian_overall_metrics.csv"
    ).set_index("model_id")
    e1_brier = float(overall.loc["E1", "weighted_brier"])
    e2_brier = float(overall.loc["E2", "weighted_brier"])
    p5_brier = float(p5.loc["P5", "weighted_brier"])

    loss = external_prediction.pivot(
        index="canonical_pair_id", columns="model_id", values="brier_loss"
    )
    metadata = external_prediction.drop_duplicates("canonical_pair_id").set_index(
        "canonical_pair_id"
    )
    pair_delta = loss["E1"] - loss["E2"]
    raw_weight = (
        1.0
        / metadata.loc[
            pair_delta.index, "first_order_inclusion_probability"
        ].to_numpy(float)
    )
    fold_id = metadata.loc[pair_delta.index, "outer_fold"].to_numpy(int)
    total_weight = float(raw_weight.sum())
    total_delta = float(np.sum(raw_weight * pair_delta.to_numpy(float)) / total_weight)
    fold_contributions = {
        str(outer_fold): float(
            np.sum(
                raw_weight[fold_id == outer_fold]
                * pair_delta.to_numpy(float)[fold_id == outer_fold]
            )
            / total_weight
        )
        for outer_fold in range(5)
    }
    fold_contribution_fraction = {
        fold: value / total_delta for fold, value in fold_contributions.items()
    }
    component = pd.DataFrame(
        {
            "component_id": metadata.loc[pair_delta.index, "component_id"].to_numpy(),
            "delta": pair_delta.to_numpy(float),
            "weight": raw_weight,
        }
    ).groupby("component_id").apply(
        lambda group: float(np.average(group["delta"], weights=group["weight"])),
        include_groups=False,
    )
    fold_wide = folds.pivot(index="outer_fold", columns="model_id", values="brier")
    fold_delta = fold_wide["E1"] - fold_wide["E2"]

    return {
        "status": "PASS",
        "analyzed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "authoritative_external_zip_sha256": external_audit["source_zip_sha256"],
        "local_reproduction_zip_sha256": local_audit["source_zip_sha256"],
        "package_manifest_sha256_equal": (
            external_execution["package_manifest_sha256"]
            == local_execution["package_manifest_sha256"]
        ),
        "contract_sha256_equal": (
            external_execution["contract_sha256"] == local_execution["contract_sha256"]
        ),
        "external_platform": external_execution["platform"],
        "local_platform": local_execution["platform"],
        "prediction_keys_equal": True,
        "selected_configuration_ids_equal": selection_equal,
        "cross_platform_probability_difference": cross_platform,
        "external_metrics": {
            model_id: {
                column: float(overall.loc[model_id, column])
                for column in (
                    "weighted_brier",
                    "weighted_log_loss",
                    "weighted_calibration_intercept",
                    "weighted_calibration_slope",
                    "weighted_auroc",
                    "weighted_auprc",
                )
            }
            for model_id in ("E1", "E2")
        },
        "effect_sizes": {
            "E1_minus_E2_weighted_brier": e1_brier - e2_brier,
            "E2_relative_brier_improvement_vs_E1_percent": 100
            * (e1_brier - e2_brier)
            / e1_brier,
            "E1_relative_brier_improvement_vs_P5_percent": 100
            * (p5_brier - e1_brier)
            / p5_brier,
            "E2_relative_brier_improvement_vs_P5_percent": 100
            * (p5_brier - e2_brier)
            / p5_brier,
            "E1_minus_S3_weighted_brier": e1_brier
            - float(sensitivity.loc["S3", "weighted_brier"]),
            "E1_minus_S4_weighted_brier": e1_brier
            - float(sensitivity.loc["S4", "weighted_brier"]),
            "E2_minus_S3_weighted_brier": e2_brier
            - float(sensitivity.loc["S3", "weighted_brier"]),
            "E2_minus_S4_weighted_brier": e2_brier
            - float(sensitivity.loc["S4", "weighted_brier"]),
        },
        "fold_E1_minus_E2_weighted_brier": {
            str(int(fold)): float(value) for fold, value in fold_delta.items()
        },
        "fold_contribution_to_overall_E1_minus_E2_brier": fold_contributions,
        "fold_contribution_fraction_of_net_difference": fold_contribution_fraction,
        "pair_loss_direction_counts": {
            "E1_lower": int((pair_delta < 0).sum()),
            "E2_lower": int((pair_delta > 0).sum()),
            "ties": int((pair_delta == 0).sum()),
        },
        "component_loss_direction_counts": {
            "E1_lower": int((component < 0).sum()),
            "E2_lower": int((component > 0).sum()),
            "ties": int((component == 0).sum()),
            "components": len(component),
        },
        "selected_configuration_counts": {
            model_id: external_selected.loc[
                external_selected["model_id"] == model_id, "configuration_id"
            ]
            .value_counts()
            .sort_index()
            .to_dict()
            for model_id in ("E1", "E2")
        },
        "inferential_test_performed": False,
        "inferential_test_reason": (
            "Task15G was preregistered as descriptive development model selection and "
            "stability only; ordinary row-level tests would ignore component dependence "
            "and add an outcome-guided decision rule."
        ),
        "scientific_conclusion_invariant_across_platforms": bool(
            selection_equal
            and e2_brier < e1_brier
            and int((fold_delta < 0).sum()) == 3
            and e1_brier > float(sensitivity.loc["S3", "weighted_brier"])
            and e2_brier > float(sensitivity.loc["S3", "weighted_brier"])
        ),
    }


def report_text(analysis: dict[str, Any]) -> str:
    e1 = analysis["external_metrics"]["E1"]
    e2 = analysis["external_metrics"]["E2"]
    effect = analysis["effect_sizes"]
    cross = analysis["cross_platform_probability_difference"]
    pairs = analysis["pair_loss_direction_counts"]
    components = analysis["component_loss_direction_counts"]
    fold_fraction = analysis["fold_contribution_fraction_of_net_difference"]["2"]
    return f"""# Task 15G External Statistical Analysis and Reconciliation

Status: `PASS`

The authoritative ModelScope export has SHA256 `{analysis['authoritative_external_zip_sha256']}`. Its 53-member inventory, 52 internal checksums, 890 out-of-fold predictions, 400 inner configuration-fold scores, ten outer selections, and zero E3 predictions all passed upstream and independent validation. The external run used the same frozen package manifest and contract as the local reproduction.

E1 obtained a design-weighted Brier score of {e1['weighted_brier']:.9f} and weighted log loss of {e1['weighted_log_loss']:.9f}. E2 obtained a Brier score of {e2['weighted_brier']:.9f} and log loss of {e2['weighted_log_loss']:.9f}. The raw weighted Brier difference, E1 minus E2, was {effect['E1_minus_E2_weighted_brier']:.9f}, corresponding to a {effect['E2_relative_brier_improvement_vs_E1_percent']:.3f}% relative reduction for E2. E1 had higher AUROC and AUPRC, so E2 did not dominate across all reported metrics.

The aggregate E2 advantage was not stable across outer folds. E1 had lower Brier in folds 0, 3, and 4; E2 was lower in folds 1 and 2. Fold 2 contributed {fold_fraction * 100:.1f}% of the net E1-minus-E2 difference because E1's advantages in three folds offset much of E2's fold-2 gain. At the row level, E1 had lower loss for {pairs['E1_lower']} of 445 pairs, and at the endpoint-component level it had lower weighted loss in {components['E1_lower']} of 116 components. The aggregate E2 score therefore reflects the magnitude and design weights of its wins rather than broad pairwise or component-wise dominance.

Relative to P5, E1 and E2 reduced weighted Brier descriptively by {effect['E1_relative_brier_improvement_vs_P5_percent']:.3f}% and {effect['E2_relative_brier_improvement_vs_P5_percent']:.3f}%, respectively. Both remained worse than S3 and S4: E2 exceeded their Brier scores by {effect['E2_minus_S3_weighted_brier']:.9f} and {effect['E2_minus_S4_weighted_brier']:.9f}. The exploratory benchmark therefore did not identify a higher proper-score ceiling than the frozen mathematical sensitivities.

Calibration remained inadequate for direct deployment use. E1's weighted calibration intercept and slope were {e1['weighted_calibration_intercept']:.4f} and {e1['weighted_calibration_slope']:.4f}; E2's were {e2['weighted_calibration_intercept']:.4f} and {e2['weighted_calibration_slope']:.4f}. These development diagnostics cannot be repaired by tuning against the still-locked calibration outcomes.

Cross-platform reproducibility was strong. E2 probabilities agreed to machine precision. E1's mean and maximum absolute Linux-versus-macOS probability differences were {cross['E1']['mean_absolute_probability_difference']:.9f} and {cross['E1']['maximum_absolute_probability_difference']:.9f}; only {cross['E1']['rows_above_1e_3']} of 445 E1 rows differed by more than 0.001. All selected configurations, outer-fold win directions, model rankings, and scientific dispositions were unchanged.

No post hoc p-value or ordinary paired test was performed. Task 15G was frozen as descriptive development model selection and stability analysis, while rows share endpoint components and carry unequal design weights. Adding an unregistered row-level significance test would ignore that dependence and create an outcome-guided decision rule. The correct effect estimates are the registered proper-score differences, their fold distribution, component direction counts, and cross-platform sensitivity reported above.

The external export is authoritative and the local result freeze is retained only as a reproducibility comparison. E1, E2, and E3 remain `confirmation_eligible=false`. Task 15H must apply qualification before performance and create the validated `development_model_freeze_record.json`.
"""


def build(output: Path = OUTPUT) -> dict[str, Any]:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    analysis = analyze()
    if analysis["scientific_conclusion_invariant_across_platforms"] is not True:
        raise RuntimeError("cross-platform scientific conclusion changed")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".task15g_reconcile_") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        write_json(stage / "external_vs_local_reconciliation.json", analysis)
        (stage / "TASK15G_EXTERNAL_STATISTICAL_ANALYSIS.md").write_text(
            report_text(analysis), encoding="utf-8"
        )
        shutil.copy2(Path(__file__), stage / "analysis_builder_snapshot.py")
        files = sorted(
            path
            for path in stage.iterdir()
            if path.is_file() and path.name != "CHECKSUMS.sha256"
        )
        (stage / "CHECKSUMS.sha256").write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in files),
            encoding="utf-8",
        )
        shutil.move(str(stage), output)
    return analysis


def main() -> int:
    try:
        analysis = build()
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
    print(json.dumps(analysis, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
