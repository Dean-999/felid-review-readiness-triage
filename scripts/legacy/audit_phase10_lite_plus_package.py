#!/usr/bin/env python3
"""Audit Phase 10-Lite Plus package readiness without running training."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "colab/phase10_lite_metric_learning"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase10_lite"
DOC_PATH = PROJECT_ROOT / "docs/phase10_lite/phase10_lite_plus_accuracy_oriented_training_plan.md"
PLUS_MANIFEST = OUTPUT_DIR / "phase10_lite_plus_matched_training_manifest_k3.csv"
PLUS_MANIFEST_AUDIT = OUTPUT_DIR / "phase10_lite_plus_manifest_audit.csv"
AUDIT_CSV = OUTPUT_DIR / "phase10_lite_plus_training_package_audit.csv"

CONFIGS = [
    PACKAGE_DIR / "config_plus_k3_random_matched.yaml",
    PACKAGE_DIR / "config_plus_k3_quality_proxy_matched.yaml",
    PACKAGE_DIR / "config_plus_k3_pf_eri_matched.yaml",
    PACKAGE_DIR / "config_plus_k3_pf_eri_quality_hybrid.yaml",
    PACKAGE_DIR / "config_plus_e4_pf_eri_weighted_all_train.yaml",
]
REQUIRED_FILES = [
    PROJECT_ROOT / "scripts/build_phase10_lite_plus_training_manifest.py",
    PROJECT_ROOT / "scripts/build_phase10_lite_plus_matched_training_manifest.py",
    PROJECT_ROOT / "scripts/audit_phase10_lite_plus_manifest.py",
    PACKAGE_DIR / "train_phase10_lite_plus_metric_learning.py",
    PACKAGE_DIR / "evaluate_phase10_lite_plus_retrieval.py",
    PACKAGE_DIR / "run_phase10_lite_plus_k3_training.py",
    DOC_PATH,
    PLUS_MANIFEST,
    PLUS_MANIFEST_AUDIT,
] + CONFIGS
GROUPS = {
    "config_plus_k3_random_matched.yaml": "B3_random_matched_identity",
    "config_plus_k3_quality_proxy_matched.yaml": "C3_quality_proxy_matched_identity",
    "config_plus_k3_pf_eri_matched.yaml": "D3_pf_eri_matched_identity",
    "config_plus_k3_pf_eri_quality_hybrid.yaml": "H3_pf_eri_quality_hybrid_matched_identity",
    "config_plus_e4_pf_eri_weighted_all_train.yaml": "E4_pf_eri_weighted_all_train_reference",
}
OLD_SELECTION_STRINGS = [
    "select_training_rows(",
    "pf_eri_score_threshold",
    "random_same_size_as_pf_eri_selected",
    "highest_quality_same_size_as_pf_eri_selected",
]
TRAINING_OUTPUT_NAMES = [
    "projection_head.pt",
    "phase10_lite_plus_training_metrics.csv",
    "phase10_lite_plus_retrieval_metrics.csv",
    "training_manifest_used.csv",
    "config_used.json",
]


def add(rows: list[dict[str, object]], check: str, status: str, detail: str, file: Path | str = "") -> None:
    rows.append({"check_name": check, "status": status, "file": str(file), "detail": detail})


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("YAML did not parse as mapping")
    return loaded


def audit_configs(rows: list[dict[str, object]]) -> None:
    for path in CONFIGS:
        try:
            config = load_yaml(path)
            add(rows, "config_parses", "PASS", "parsed", path)
        except Exception as exc:
            add(rows, "config_parses", "FAIL", str(exc), path)
            continue
        expected_group = GROUPS[path.name]
        add(rows, "config_training_rule_plus", "PASS" if config.get("training_rule") == "use_preselected_phase10_lite_plus_group" else "FAIL", f"training_rule={config.get('training_rule')!r}", path)
        add(rows, "config_group_exact", "PASS" if config.get("phase10_lite_plus_group") == expected_group and config.get("experiment_group") == expected_group else "FAIL", f"group={config.get('phase10_lite_plus_group')!r}", path)
        add(rows, "config_manifest_is_plus", "PASS" if "phase10_lite_plus_matched_training_manifest_k3.csv" in str(config.get("manifest_path", "")) else "FAIL", f"manifest_path={config.get('manifest_path')!r}", path)
        add(rows, "config_not_old_phase9d_manifest", "PASS" if "phase9d_image_training_manifest_internal.csv" not in str(config.get("manifest_path", "")) else "FAIL", f"manifest_path={config.get('manifest_path')!r}", path)
        add(rows, "config_no_k2_primary", "PASS" if "k2" not in path.name.lower() and "k2" not in str(config.get("manifest_path", "")).lower() else "FAIL", "k2 not used", path)
        sampler = config.get("sampler", {})
        add(rows, "config_uses_identity_balanced_pk", "PASS" if sampler.get("type") == "identity_balanced_pk" else "FAIL", f"sampler={sampler}", path)
        add(rows, "config_pk_k_is_3", "PASS" if int(sampler.get("k_images_per_identity_per_batch", -1)) == 3 else "FAIL", f"sampler_k={sampler.get('k_images_per_identity_per_batch')}", path)
        add(rows, "config_epoch_one", "PASS" if int(config.get("model", {}).get("epochs", -1)) == 1 else "FAIL", f"epochs={config.get('model', {}).get('epochs')}", path)
        add(rows, "config_megadescriptor_only", "PASS" if str(config.get("descriptor", "")).lower() == "megadescriptor" and "megadescriptor" in str(config.get("embedding_path", "")).lower() else "FAIL", f"descriptor={config.get('descriptor')}", path)


def audit_manifest(rows: list[dict[str, object]]) -> None:
    if not PLUS_MANIFEST.exists():
        add(rows, "plus_manifest_exists", "FAIL", "missing", PLUS_MANIFEST)
        return
    df = pd.read_csv(PLUS_MANIFEST)
    matched = ["B3_random_matched_identity", "C3_quality_proxy_matched_identity", "D3_pf_eri_matched_identity", "H3_pf_eri_quality_hybrid_matched_identity"]
    for split_id, split_rows in df.groupby("split_id"):
        identity_sets = {g: set(split_rows.loc[split_rows["phase10_lite_plus_group"] == g, "identity_label_internal"].astype(str)) for g in matched}
        row_counts = {g: int((split_rows["phase10_lite_plus_group"] == g).sum()) for g in matched}
        add(rows, "manifest_b3_c3_d3_h3_identity_matched", "PASS" if len({frozenset(v) for v in identity_sets.values()}) == 1 else "FAIL", str({k: len(v) for k, v in identity_sets.items()}), PLUS_MANIFEST)
        add(rows, "manifest_b3_c3_d3_h3_row_matched", "PASS" if len(set(row_counts.values())) == 1 else "FAIL", str(row_counts), PLUS_MANIFEST)
        e4 = split_rows[split_rows["phase10_lite_plus_group"] == "E4_pf_eri_weighted_all_train_reference"]
        add(rows, "manifest_e4_all_train_reference_rows", "PASS" if len(e4) == 300 else "FAIL", f"split={split_id} rows={len(e4)}", PLUS_MANIFEST)
        add(rows, "manifest_e4_sample_weight_present", "PASS" if "sample_weight" in e4.columns and pd.to_numeric(e4["sample_weight"], errors="coerce").notna().all() else "FAIL", f"split={split_id}", PLUS_MANIFEST)


def audit_scripts(rows: list[dict[str, object]]) -> None:
    train_text = (PACKAGE_DIR / "train_phase10_lite_plus_metric_learning.py").read_text(encoding="utf-8")
    forbidden = [s for s in OLD_SELECTION_STRINGS if s in train_text]
    add(rows, "training_script_no_old_selection_strings", "PASS" if not forbidden else "FAIL", f"forbidden={forbidden}", PACKAGE_DIR / "train_phase10_lite_plus_metric_learning.py")
    add(rows, "training_script_has_pk_sampler", "PASS" if "IdentityBalancedPKBatchSampler" in train_text and "identity_balanced_pk" in train_text else "FAIL", "PK sampler required", PACKAGE_DIR / "train_phase10_lite_plus_metric_learning.py")
    add(rows, "training_script_has_plus_rule", "PASS" if "use_preselected_phase10_lite_plus_group" in train_text else "FAIL", "Plus rule required", PACKAGE_DIR / "train_phase10_lite_plus_metric_learning.py")
    runner_text = (PACKAGE_DIR / "run_phase10_lite_plus_k3_training.py").read_text(encoding="utf-8")
    add(rows, "runner_accepts_explicit_dry_run", "PASS" if "--dry-run" in runner_text else "FAIL", "runner must accept --dry-run", PACKAGE_DIR / "run_phase10_lite_plus_k3_training.py")
    add(rows, "runner_default_does_not_execute", "PASS" if "--execute" in runner_text and "planned_run_count" in runner_text else "FAIL", "runner should default to planned runs", PACKAGE_DIR / "run_phase10_lite_plus_k3_training.py")


def audit_no_training_outputs(rows: list[dict[str, object]]) -> None:
    result_root = OUTPUT_DIR / "metric_learning_plus_results"
    found: list[Path] = []
    if result_root.exists():
        for name in TRAINING_OUTPUT_NAMES:
            found.extend(result_root.rglob(name))
    add(rows, "no_training_or_checkpoint_outputs_created", "PASS" if not found else "FAIL", f"found={len(found)}", result_root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for path in REQUIRED_FILES:
        add(rows, "required_file_exists", "PASS" if path.exists() else "FAIL", "exists" if path.exists() else "missing", path)
    audit_configs(rows)
    audit_manifest(rows)
    audit_scripts(rows)
    audit_no_training_outputs(rows)
    audit = pd.DataFrame(rows, columns=["check_name", "status", "file", "detail"])
    audit.to_csv(AUDIT_CSV, index=False)
    fail_count = int((audit["status"] == "FAIL").sum())
    print(f"{'PASS' if fail_count == 0 else 'FAIL'} audit_phase10_lite_plus_package")
    print(f"pass_count={int((audit['status'] == 'PASS').sum())}")
    print(f"fail_count={fail_count}")
    print(f"audit_csv={AUDIT_CSV}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
