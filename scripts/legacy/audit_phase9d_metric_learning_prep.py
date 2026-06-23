#!/usr/bin/env python3
"""Audit Phase 9D metric-learning preparation outputs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/czechlynx/phase9/pf_eri_metric_learning_prep"
QC = ROOT / "outputs/czechlynx/qc"
DOC = ROOT / "docs/phase9/phase9d_pferi_weighted_metric_learning_colab_prep.md"
COLAB = ROOT / "colab/phase9d_metric_learning"
SUMMARY = QC / "phase9d_metric_learning_prep_audit_summary.txt"
REPORT = QC / "phase9d_metric_learning_prep_audit_report.csv"

REQUIRED_OUTPUTS = [
    "phase9d_input_inventory.csv",
    "phase9d_image_training_manifest_internal.csv",
    "phase9d_split_design_internal.csv",
    "phase9d_identity_distribution_summary.csv",
    "phase9d_quality_distribution_summary.csv",
    "phase9d_training_group_plan.csv",
    "phase9d_loss_design_plan.csv",
    "phase9d_baseline_control_plan.csv",
    "phase9d_colab_file_manifest.csv",
    "phase9d_evaluation_plan.csv",
    "phase9d_data_expansion_recommendation.csv",
    "phase9d_feasibility_decision.csv",
]

REQUIRED_COLAB = [
    "README.md",
    "phase9d_colab_training_template.ipynb",
    "train_metric_learning.py",
    "evaluate_reid_retrieval.py",
    "requirements_colab.txt",
    "config_baseline_all_images.yaml",
    "config_random_same_size.yaml",
    "config_quality_only.yaml",
    "config_pf_eri_selected.yaml",
    "config_pf_eri_weighted.yaml",
]

REQUIRED_GROUPS = {
    "A_all_images_baseline",
    "B_random_same_size_baseline",
    "C_quality_only_selected_baseline",
    "D_pf_eri_selected_training",
    "E_pf_eri_weighted_training",
    "F_pf_eri_reranking_without_training_reference",
}

FORBIDDEN_PUBLIC_PATTERNS = [
    re.compile(r"/Users/", re.IGNORECASE),
    re.compile(r"data/raw", re.IGNORECASE),
    re.compile(r"working_individual_id", re.IGNORECASE),
    re.compile(r"unique_name", re.IGNORECASE),
    re.compile(r"latitude|longitude|trap_id|cell_code|camera_id", re.IGNORECASE),
]

FORBIDDEN_CLAIMS = [
    "PF-ERI improves Re-ID learning",
    "PF-ERI is a new Re-ID descriptor",
    "PF-ERI identifies true individual animals",
    "PF-ERI is validated on Mainland Clouded Leopard",
    "PF-ERI is validated on Marbled Cat",
    "PF-ERI is field-deployment ready",
    "PF-ERI estimates population size",
]


def add(report: list[dict[str, str]], severity: str, issue_type: str, file: str, message: str) -> None:
    report.append({"severity": severity, "issue_type": issue_type, "file": file, "message": message})


def audit(_: argparse.Namespace) -> int:
    report: list[dict[str, str]] = []
    for name in REQUIRED_OUTPUTS:
        if not (OUT / name).exists():
            add(report, "ERROR", "missing_output", str(OUT / name), "required output missing")
    for name in REQUIRED_COLAB:
        if not (COLAB / name).exists():
            add(report, "ERROR", "missing_colab_file", str(COLAB / name), "required Colab file missing")
    if not DOC.exists():
        add(report, "ERROR", "missing_doc", str(DOC), "required documentation missing")

    if report:
        QC.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(report).to_csv(REPORT, index=False)
        SUMMARY.write_text("FAIL\nmissing required files\n", encoding="utf-8")
        print("FAIL")
        return 1

    manifest = pd.read_csv(OUT / "phase9d_image_training_manifest_internal.csv")
    required_manifest_cols = {
        "image_path_internal",
        "image_id",
        "identity_label_internal",
        "pf_eri_image_score",
        "visual_penalty",
        "quality_bucket",
        "source_phase",
        "split_id",
        "train_val_test_role",
        "near_duplicate_group_if_available",
    }
    missing_cols = required_manifest_cols - set(manifest.columns)
    for col in sorted(missing_cols):
        add(report, "ERROR", "missing_manifest_column", str(OUT / "phase9d_image_training_manifest_internal.csv"), col)
    if manifest["split_id"].nunique() < 1:
        add(report, "ERROR", "split_design_empty", str(OUT / "phase9d_image_training_manifest_internal.csv"), "no splits found")
    for split_id, group in manifest.groupby("split_id"):
        roles = set(group["train_val_test_role"])
        if not roles.issuperset({"train", "val", "test"}):
            add(report, "ERROR", "missing_split_role", str(OUT / "phase9d_image_training_manifest_internal.csv"), f"split {split_id} lacks train/val/test")
        role_ids = {role: set(part["identity_label_internal"]) for role, part in group.groupby("train_val_test_role")}
        if role_ids.get("train", set()) & role_ids.get("val", set()) or role_ids.get("train", set()) & role_ids.get("test", set()) or role_ids.get("val", set()) & role_ids.get("test", set()):
            add(report, "ERROR", "identity_leakage", str(OUT / "phase9d_image_training_manifest_internal.csv"), f"identity overlap in split {split_id}")

    groups = set(pd.read_csv(OUT / "phase9d_training_group_plan.csv")["training_group"])
    for group in sorted(REQUIRED_GROUPS - groups):
        add(report, "ERROR", "missing_training_group", str(OUT / "phase9d_training_group_plan.csv"), group)

    baseline_text = (OUT / "phase9d_baseline_control_plan.csv").read_text(encoding="utf-8")
    for required in ["random_same_size", "quality_only", "all_images", "reranking_without_training"]:
        if required not in baseline_text:
            add(report, "ERROR", "missing_baseline_control", str(OUT / "phase9d_baseline_control_plan.csv"), required)

    doc_text = DOC.read_text(encoding="utf-8")
    public_texts = [(DOC, doc_text), (COLAB / "README.md", (COLAB / "README.md").read_text(encoding="utf-8"))]
    for path, text in public_texts:
        for pattern in FORBIDDEN_PUBLIC_PATTERNS:
            if pattern.search(text):
                add(report, "ERROR", "sensitive_public_text", str(path), pattern.pattern)
    forbidden_section = doc_text.split("## 21. Forbidden Claims", 1)[-1]
    pre_forbidden = doc_text.split("## 21. Forbidden Claims", 1)[0]
    for claim in FORBIDDEN_CLAIMS:
        if claim in pre_forbidden:
            add(report, "ERROR", "forbidden_claim_before_section", str(DOC), claim)
        if claim not in forbidden_section:
            add(report, "ERROR", "missing_forbidden_claim", str(DOC), claim)

    notebook_text = (COLAB / "phase9d_colab_training_template.ipynb").read_text(encoding="utf-8")
    if "Only held-out retrieval metrics count" not in notebook_text:
        add(report, "ERROR", "missing_notebook_warning", str(COLAB / "phase9d_colab_training_template.ipynb"), "retrieval metric warning missing")

    inventory = pd.read_csv(OUT / "phase9d_input_inventory.csv")
    delayed_refs = int(inventory["input_file"].astype(str).str.contains("second_review|second-review", case=False, regex=True).sum())
    if delayed_refs:
        add(report, "ERROR", "delayed_second_review_reference", str(OUT / "phase9d_input_inventory.csv"), "delayed second-review reference found")

    training_result_files = list((ROOT / "outputs/czechlynx/phase9").glob("pf_eri_metric_learning_results/**/*"))
    training_result_count = len([p for p in training_result_files if p.is_file()])
    if training_result_count:
        add(report, "ERROR", "local_training_outputs_exist", str(ROOT / "outputs/czechlynx/phase9/pf_eri_metric_learning_results"), "local training result files found")

    status = "PASS" if not any(row["severity"] == "ERROR" for row in report) else "FAIL"
    lines = [
        status,
        f"required_prep_outputs={len(REQUIRED_OUTPUTS)}",
        f"required_colab_files={len(REQUIRED_COLAB)}",
        f"manifest_rows={len(manifest)}",
        f"unique_images={manifest['image_id'].nunique()}",
        f"identity_count={manifest['identity_label_internal'].nunique()}",
        f"split_count={manifest['split_id'].nunique()}",
        f"training_group_count={len(groups)}",
        f"local_training_output_files={training_result_count}",
        f"delayed_second_review_references={delayed_refs}",
        f"issue_count={len(report)}",
    ]
    QC.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    pd.DataFrame(report, columns=["severity", "issue_type", "file", "message"]).to_csv(REPORT, index=False)
    print("\n".join(lines))
    return 0 if status == "PASS" else 1


def parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(description=__doc__).parse_args()


if __name__ == "__main__":
    raise SystemExit(audit(parse_args()))
