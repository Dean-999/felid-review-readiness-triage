#!/usr/bin/env python3
"""Freeze the returned Task15L calibration responses and their limited analysis."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "archive/pferi_v2/task_runs/model_development"
INPUT = MODEL_ROOT / "2026-07-27_task15l_calibration_final_v1/Task15L_CALIBRATION_FINAL"
OUTPUT = ROOT / "outputs/pferi_v2/models/calibration/analysis"
RUNNER = ROOT / "scripts/run_task15l_calibration_collection.py"
REVIEWERS = ("reviewer_A", "reviewer_B", "reviewer_C", "reviewer_D")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_checksums(directory: Path) -> None:
    files = sorted(path for path in directory.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    (directory / "CHECKSUMS.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(directory)}\n" for path in files), encoding="utf-8"
    )


def load_runner():
    spec = importlib.util.spec_from_file_location("task15l_frozen_analysis_runner", RUNNER)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load Task15L analysis runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules["task15l_frozen_analysis_runner"] = module
    spec.loader.exec_module(module)
    return module


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_record(outcome: dict[str, Any], source_hashes: dict[str, str]) -> dict[str, Any]:
    overall = "PASS" if all(outcome[layer]["status"] == "PASS" for layer in ("collection", "calibratability", "calibration")) else "FAIL"
    return {
        "record_version": "pferi_v2_task15l_calibration_analysis_freeze_v1",
        "frozen_at_utc": utc_now(),
        "status": overall,
        "source_response_sha256": source_hashes,
        "source_submission_assertion": "The project owner confirmed that the review decisions in this submission were entered by the assigned reviewers.",
        "timestamp_policy": "submitted_at_utc is descriptive only and was not used for eligibility or statistical analysis.",
        "hard_eligibility_conditions": [
            "assignment coverage",
            "exact response schema",
            "unique response ID",
            "technical_problem_flag=no",
        ],
        "descriptive_only_fields": ["reason_codes", "confidence", "submitted_at_utc", "reviewer agreement"],
        "collection": outcome["collection"],
        "calibratability": outcome["calibratability"],
        "calibration": outcome["calibration"],
        "claim_boundary": "PASS establishes returned-response eligibility and apparent intercept/slope calibration of the frozen P3/P5 probabilities only. It does not establish pair correctness, identity accuracy, independent performance confirmation, deployment utility, P5 superiority, or project completion.",
        "next_authorized_action": "Freeze the apparent calibration result; retain independent confirmation as a separate future stage.",
    }


def write_report(stage: Path, record: dict[str, Any]) -> None:
    calibration = record["calibration"]
    collection = record["collection"]
    balance = record["calibratability"]
    (stage / "TASK15L_CALIBRATION_ANALYSIS_FREEZE_REPORT.md").write_text(
        "# Task15L Calibration Analysis Freeze\n\n"
        f"Status: **{record['status']}**\n\n"
        f"The returned-response eligibility audit passed: {collection['valid_responses']} valid responses, "
        f"{collection['complete_double_review_pairs']} complete double-review pairs, "
        f"{collection['unique_response_ids']} unique response IDs, and "
        f"{collection['technical_problem_count']} technical problems.\n\n"
        f"The conservative label rule produced `y=0` for {balance['count_y0']} pairs and `y=1` for "
        f"{balance['count_y1']} pairs. P3 intercept/slope: {calibration['p3_intercept']} / "
        f"{calibration['p3_slope']}. P5 intercept/slope: {calibration['p5_intercept']} / "
        f"{calibration['p5_slope']}. The endpoint-component bootstrap completed "
        f"{calibration['bootstrap_replicates_completed']} of {calibration['bootstrap_replicates_requested']} replicates.\n\n"
        "Timestamps, confidence, reasons, and reviewer agreement are descriptive only. No original "
        "model coefficient, feature, preprocessing rule, lambda, model selection, or action threshold was changed. "
        "This is apparent calibration only; independent confirmation remains a separate future stage.\n",
        encoding="utf-8",
    )


def run(output: Path) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    source = INPUT.resolve()
    source_paths = {alias: source / f"{alias}_completed/raw_responses.csv" for alias in REVIEWERS}
    if any(not path.is_file() for path in source_paths.values()):
        raise FileNotFoundError("one or more Task15L response CSV files are missing")
    output.parent.mkdir(parents=True, exist_ok=True)
    runner = load_runner()
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as temporary:
        stage = Path(temporary) / output.name
        stage.mkdir()
        (stage / "merged_analysis").mkdir()
        source_hashes = {alias: sha256(path) for alias, path in source_paths.items()}
        for alias, path in source_paths.items():
            target = stage / f"{alias}_completed"
            target.mkdir()
            shutil.copy2(path, target / "raw_responses.csv")
        outcome = runner.aggregate_and_analyze(stage)
        record = build_record(outcome, source_hashes)
        write_json(stage / "task15l_calibration_analysis_freeze_record.json", record)
        write_report(stage, record)
        write_checksums(stage / "merged_analysis")
        write_checksums(stage)
        shutil.move(str(stage), str(output))
    archive = output.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                bundle.write(path, Path(output.name) / path.relative_to(output))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.output), indent=2, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
