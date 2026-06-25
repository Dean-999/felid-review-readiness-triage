#!/usr/bin/env python3
"""Audit local readiness for staged Phase 10-Lite Plus Colab execution."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase10_lite"
COLAB_DIR = PROJECT_ROOT / "colab/phase10_lite_metric_learning"
AUDIT_CSV = OUT_DIR / "phase10_lite_plus_colab_readiness_audit.csv"
UPLOAD_MANIFEST = OUT_DIR / "phase10_lite_plus_colab_upload_manifest.csv"
PLUS_MANIFEST = OUT_DIR / "phase10_lite_plus_matched_training_manifest_k3.csv"
PLUS_MANIFEST_AUDIT = OUT_DIR / "phase10_lite_plus_manifest_audit.csv"
PLUS_PACKAGE_AUDIT = OUT_DIR / "phase10_lite_plus_training_package_audit.csv"
RUNBOOK = PROJECT_ROOT / "docs/phase10_lite/phase10_lite_plus_colab_runbook.md"

CONFIGS = [
    "config_plus_k3_random_matched.yaml",
    "config_plus_k3_quality_proxy_matched.yaml",
    "config_plus_k3_pf_eri_matched.yaml",
    "config_plus_k3_pf_eri_quality_hybrid.yaml",
    "config_plus_e4_pf_eri_weighted_all_train.yaml",
]
SCRIPTS = [
    "train_phase10_lite_plus_metric_learning.py",
    "evaluate_phase10_lite_plus_retrieval.py",
    "run_phase10_lite_plus_k3_training.py",
    "plan_phase10_lite_plus_colab_runs.py",
    "patch_phase10_lite_plus_colab_configs.py",
    "summarize_phase10_lite_plus_results.py",
]
TRAINING_OUTPUT_NAMES = {
    "projection_head.pt",
    "phase10_lite_plus_training_metrics.csv",
    "phase10_lite_plus_retrieval_metrics.csv",
    "phase10_lite_plus_failure_cases.csv",
    "training_manifest_used.csv",
    "config_used.json",
}


def add(rows: list[dict[str, object]], check: str, status: str, detail: str, path: Path | str = "") -> None:
    rows.append({"check_name": check, "status": status, "detail": detail, "path": str(path)})


def audit_pass_csv(path: Path, rows: list[dict[str, object]], check: str) -> None:
    if not path.exists():
        add(rows, check, "FAIL", "missing", path)
        return
    frame = pd.read_csv(path)
    if "status" not in frame.columns:
        add(rows, check, "FAIL", "missing status column", path)
        return
    fail_count = int((frame["status"] != "PASS").sum())
    add(rows, check, "PASS" if fail_count == 0 else "FAIL", f"rows={len(frame)} non_pass={fail_count}", path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    if PLUS_MANIFEST.exists():
        manifest = pd.read_csv(PLUS_MANIFEST)
        groups = set(manifest["phase10_lite_plus_group"].astype(str)) if "phase10_lite_plus_group" in manifest else set()
        add(rows, "plus_manifest_exists", "PASS", f"rows={len(manifest)}", PLUS_MANIFEST)
        add(rows, "plus_manifest_expected_rows", "PASS" if len(manifest) == 6000 else "FAIL", f"rows={len(manifest)}", PLUS_MANIFEST)
        add(rows, "plus_manifest_expected_groups", "PASS" if len(groups) == 5 else "FAIL", f"groups={sorted(groups)}", PLUS_MANIFEST)
    else:
        add(rows, "plus_manifest_exists", "FAIL", "missing", PLUS_MANIFEST)

    audit_pass_csv(PLUS_MANIFEST_AUDIT, rows, "plus_manifest_audit_all_pass")
    audit_pass_csv(PLUS_PACKAGE_AUDIT, rows, "plus_package_audit_all_pass")

    add(rows, "colab_package_dir_exists", "PASS" if COLAB_DIR.exists() else "FAIL", "exists" if COLAB_DIR.exists() else "missing", COLAB_DIR)
    for name in SCRIPTS:
        path = COLAB_DIR / name
        add(rows, f"script_exists_{name}", "PASS" if path.exists() else "FAIL", "exists" if path.exists() else "missing", path)
    for name in CONFIGS:
        path = COLAB_DIR / name
        add(rows, f"config_exists_{name}", "PASS" if path.exists() else "FAIL", "exists" if path.exists() else "missing", path)
    req = COLAB_DIR / "requirements_colab.txt"
    add(rows, "requirements_colab_exists", "PASS" if req.exists() else "FAIL", "exists" if req.exists() else "missing", req)

    pycache = list(COLAB_DIR.rglob("__pycache__")) if COLAB_DIR.exists() else []
    add(rows, "no_pycache_under_colab_package", "PASS" if not pycache else "FAIL", f"pycache_count={len(pycache)}", COLAB_DIR)
    checkpoint_like = []
    if COLAB_DIR.exists():
        checkpoint_like = [p for p in COLAB_DIR.rglob("*") if p.is_file() and (p.suffix == ".pt" or "checkpoint" in p.name.lower())]
    add(rows, "no_checkpoint_files_under_colab_package", "PASS" if not checkpoint_like else "FAIL", f"files={len(checkpoint_like)}", COLAB_DIR)
    output_dirs = [p for p in [COLAB_DIR / "smoke_outputs", COLAB_DIR / "full_pilot_outputs", COLAB_DIR / "metric_learning_plus_results"] if p.exists()]
    add(rows, "no_training_output_dirs_under_colab_package", "PASS" if not output_dirs else "FAIL", f"dirs={len(output_dirs)}", COLAB_DIR)

    add(rows, "runbook_exists", "PASS" if RUNBOOK.exists() else "FAIL", "exists" if RUNBOOK.exists() else "missing", RUNBOOK)
    add(rows, "upload_manifest_exists", "PASS" if UPLOAD_MANIFEST.exists() else "FAIL", "exists" if UPLOAD_MANIFEST.exists() else "missing", UPLOAD_MANIFEST)
    if UPLOAD_MANIFEST.exists():
        upload = pd.read_csv(UPLOAD_MANIFEST)
        include_rows = upload[upload["include_for_upload"].astype(str).str.lower() == "true"]
        missing_include = include_rows[include_rows["exists"].astype(str).str.lower() != "true"]
        forbidden_rows = upload[upload["include_for_upload"].astype(str).str.lower() == "false"]
        delayed_rows = forbidden_rows[
            forbidden_rows["local_path"].astype(str).str.contains("second-review|mapping", case=False, regex=True)
        ]
        add(rows, "upload_manifest_has_required_rows", "PASS" if len(include_rows) >= 20 else "FAIL", f"include_rows={len(include_rows)}", UPLOAD_MANIFEST)
        add(rows, "upload_manifest_required_files_exist", "PASS" if missing_include.empty else "FAIL", f"missing_include_rows={len(missing_include)}", UPLOAD_MANIFEST)
        add(rows, "upload_manifest_marks_forbidden_material", "PASS" if len(forbidden_rows) >= 8 and len(delayed_rows) >= 2 else "FAIL", f"forbidden_rows={len(forbidden_rows)} delayed_or_mapping_rows={len(delayed_rows)}", UPLOAD_MANIFEST)

    training_outputs = []
    for path in OUT_DIR.rglob("*"):
        if path.is_file() and path.name in TRAINING_OUTPUT_NAMES:
            training_outputs.append(path)
    add(rows, "no_training_outputs_under_phase10_lite_outputs", "PASS" if not training_outputs else "FAIL", f"files={len(training_outputs)}", OUT_DIR)

    audit = pd.DataFrame(rows, columns=["check_name", "status", "detail", "path"])
    audit.to_csv(AUDIT_CSV, index=False)
    fail_count = int((audit["status"] == "FAIL").sum())
    print(f"{'PASS' if fail_count == 0 else 'FAIL'} audit_phase10_lite_plus_colab_readiness")
    print(f"pass_count={int((audit['status'] == 'PASS').sum())}")
    print(f"fail_count={fail_count}")
    print(f"audit_csv={AUDIT_CSV}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
