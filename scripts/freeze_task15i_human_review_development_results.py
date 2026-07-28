#!/usr/bin/env python3
"""Independently validate and freeze the Task15I declared-manual-review result."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-27_task15i_human_review_outcome_analysis/current"
OUTPUT = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-27_task15i_human_review_development_result_freeze_v1"
REQUIRED_ANALYSIS_FILES = {
    "accepted_raw_responses.csv",
    "endpoint_leakage_audit.csv",
    "fold_level_brier_results.csv",
    "p3_oof_predictions.csv",
    "p5_oof_predictions.csv",
    "pair_level_outcome_labels.csv",
    "reviewer_decision_summary.csv",
    "task15i_development_screen_report.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def validate_checksums(analysis: Path) -> None:
    checksum_file = analysis / "CHECKSUMS.sha256"
    if not checksum_file.is_file():
        raise FileNotFoundError("analysis checksum manifest is missing")
    declared: dict[str, str] = {}
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        digest, filename = line.split("  ", 1)
        declared[filename] = digest
    if set(declared) != REQUIRED_ANALYSIS_FILES:
        raise ValueError("analysis checksum inventory differs from the frozen v2 inventory")
    failures = [name for name, digest in declared.items() if not (analysis / name).is_file() or sha256(analysis / name) != digest]
    if failures:
        raise ValueError(f"analysis checksum failure: {', '.join(failures)}")


def validate_analysis(analysis: Path) -> dict[str, Any]:
    validate_checksums(analysis)
    report = json.loads((analysis / "task15i_development_screen_report.json").read_text(encoding="utf-8"))
    if report["status"] != "PASS_TASK15I_DEVELOPMENT_SCREEN":
        raise ValueError("development screen did not pass")
    if report["analyzable_pair_count"] != 1600 or report["component_count"] != 400:
        raise ValueError("unexpected analysis coverage")
    if report["time_fields_used"] is not False or report["uniform_timestamp_value_count"] != 1:
        raise ValueError("timestamp policy is inconsistent with declared result")
    if report["delta_brier_P3_minus_P5"] < 0.005 or report["nonnegative_outer_fold_count"] < 4:
        raise ValueError("frozen P3/P5 performance gate did not pass")
    if abs(report["p5_calibration_intercept"]) > 0.20 or not 0.80 <= report["p5_calibration_slope"] <= 1.20:
        raise ValueError("frozen calibration gate did not pass")
    if report["endpoint_leakage_count"] != 0 or not report["all_probabilities_finite"] or not report["all_probabilities_in_unit_interval"]:
        raise ValueError("probability or leakage gate did not pass")

    folds = pd.read_csv(analysis / "fold_level_brier_results.csv")
    if len(folds) != 5 or set(folds["outer_fold"]) != set(range(5)) or not (folds["pair_count"] == 320).all():
        raise ValueError("unexpected outer-fold inventory")
    if not (folds["delta_brier_P3_minus_P5"] >= 0).all():
        raise ValueError("P5 does not improve P3 in every outer fold")
    labels = pd.read_csv(analysis / "pair_level_outcome_labels.csv")
    if len(labels) != 1600 or labels["canonical_pair_id"].nunique() != 1600:
        raise ValueError("unexpected pair-label coverage")
    if int(labels["not_ready_or_uncertain_label"].eq(0).sum()) != 448:
        raise ValueError("unexpected review-ready outcome count")
    if int(labels["not_ready_or_uncertain_label"].eq(1).sum()) != 1152:
        raise ValueError("unexpected not-ready-or-uncertain outcome count")
    return {"report": report, "folds": folds, "labels": labels}


def freeze(analysis: Path = ANALYSIS, output: Path = OUTPUT) -> dict[str, Any]:
    analysis, output = analysis.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    validated = validate_analysis(analysis)
    report, folds, labels = validated["report"], validated["folds"], validated["labels"]
    result = {
        "status": "FROZEN_COMPLETE_TASK15I_DECLARED_MANUAL_REVIEW_DEVELOPMENT_SCREEN_PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_analysis_directory": str(analysis.relative_to(ROOT)),
        "source_analysis_checksum_manifest_sha256": sha256(analysis / "CHECKSUMS.sha256"),
        "source_analysis_status": report["status"],
        "manual_review_provenance": (
            "Study owner declares that each submitted photograph was reviewed manually by a human reviewer. "
            "The AI-assisted classification tool was used only to support the review workflow and did not generate photo-level labels."
        ),
        "attribution_boundary": (
            "The retained evidence establishes package-to-response provenance and a study-owner manual-review declaration. "
            "It does not independently verify a reviewer's physical identity beyond that declaration."
        ),
        "eligibility_policy": (
            "Only frozen assignment coverage, response-schema validity, unique submitted response IDs, and no technical-problem flags are eligibility conditions. "
            "Individual confidence, reason, response time, and reviewer agreement are descriptive and are not pass gates."
        ),
        "outcome_rule": report["label_rule"],
        "pair_count": int(len(labels)),
        "component_count": int(report["component_count"]),
        "review_ready_pair_count": int(labels["not_ready_or_uncertain_label"].eq(0).sum()),
        "not_ready_or_uncertain_pair_count": int(labels["not_ready_or_uncertain_label"].eq(1).sum()),
        "p3_weighted_brier": report["p3_weighted_brier"],
        "p5_weighted_brier": report["p5_weighted_brier"],
        "p3_minus_p5_weighted_brier": report["delta_brier_P3_minus_P5"],
        "outer_fold_deltas": [
            {"outer_fold": int(row.outer_fold), "p3_minus_p5_weighted_brier": float(row.delta_brier_P3_minus_P5)}
            for row in folds.itertuples(index=False)
        ],
        "nonnegative_outer_fold_count": int(report["nonnegative_outer_fold_count"]),
        "p5_calibration_intercept": report["p5_calibration_intercept"],
        "p5_calibration_slope": report["p5_calibration_slope"],
        "endpoint_leakage_count": int(report["endpoint_leakage_count"]),
        "claim_boundary": (
            "This freezes a passed Task15I development screen only. It does not establish identity accuracy, pair correctness, calibration-stage approval, confirmation, deployment performance, or project completion."
        ),
        "supersedes": (
            "Any Task15I human-review outcome analysis with numerical-optimization warnings; "
            "v3 is the provenance-clarified, checksum-verified analysis source for this freeze."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        write_json(stage / "task15i_human_review_development_result_freeze.json", result)
        (stage / "CHECKSUMS.sha256").write_text(
            f"{sha256(stage / 'task15i_human_review_development_result_freeze.json')}  task15i_human_review_development_result_freeze.json\n",
            encoding="utf-8",
        )
        shutil.move(str(stage), str(output))
    return result


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2, sort_keys=True))
