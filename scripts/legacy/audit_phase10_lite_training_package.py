#!/usr/bin/env python3
"""Audit the Phase 10-Lite matched training package without running training."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "colab/phase10_lite_metric_learning"
DOC_PATH = PROJECT_ROOT / "docs/phase10_lite/phase10_lite_matched_training_plan.md"
OUTPUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase10_lite"
AUDIT_CSV = OUTPUT_DIR / "phase10_lite_training_package_audit.csv"

REQUIRED_FILES = [
    PACKAGE_DIR / "train_phase10_lite_metric_learning.py",
    PACKAGE_DIR / "evaluate_phase10_lite_retrieval.py",
    PACKAGE_DIR / "requirements_colab.txt",
    PACKAGE_DIR / "config_k2_random_matched.yaml",
    PACKAGE_DIR / "config_k2_quality_matched.yaml",
    PACKAGE_DIR / "config_k2_pf_eri_matched.yaml",
    PACKAGE_DIR / "config_k3_random_matched.yaml",
    PACKAGE_DIR / "config_k3_quality_matched.yaml",
    PACKAGE_DIR / "config_k3_pf_eri_matched.yaml",
    PACKAGE_DIR / "run_phase10_lite_matched_training.py",
    DOC_PATH,
]
CONFIGS = [
    PACKAGE_DIR / "config_k2_random_matched.yaml",
    PACKAGE_DIR / "config_k2_quality_matched.yaml",
    PACKAGE_DIR / "config_k2_pf_eri_matched.yaml",
    PACKAGE_DIR / "config_k3_random_matched.yaml",
    PACKAGE_DIR / "config_k3_quality_matched.yaml",
    PACKAGE_DIR / "config_k3_pf_eri_matched.yaml",
]
GROUPS = {
    "random": "B2_random_matched_identity",
    "quality": "C2_quality_matched_identity",
    "pf_eri": "D2_pf_eri_matched_identity",
}
OLD_PHASE9D_GROUPS = [
    "A_all_images_baseline",
    "B_random_same_size_baseline",
    "C_quality_only_selected_baseline",
    "D_pf_eri_selected_training",
    "E_pf_eri_weighted_training",
]
OLD_SELECTION_PATTERNS = [
    "select_training_rows(",
    "pf_eri_score_threshold",
    "random_same_size_as_pf_eri_selected",
    "highest_quality_same_size_as_pf_eri_selected",
    ".sample(",
    "pf_eri_min_score",
]
EXPECTED_TRAINING_OUTPUT_NAMES = [
    "projection_head.pt",
    "phase10_lite_training_metrics.csv",
    "phase10_lite_retrieval_metrics.csv",
    "training_manifest_used.csv",
    "config_used.json",
]


def add(
    rows: list[dict[str, object]],
    check_name: str,
    status: str,
    detail: str,
    file: Path | str = "",
) -> None:
    rows.append(
        {
            "check_name": check_name,
            "status": status,
            "file": str(file),
            "detail": detail,
        }
    )


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} did not parse to a YAML mapping")
    return value


def expected_group_from_name(path: Path) -> str:
    name = path.name
    if "random" in name:
        return GROUPS["random"]
    if "quality" in name:
        return GROUPS["quality"]
    if "pf_eri" in name:
        return GROUPS["pf_eri"]
    raise ValueError(f"cannot infer group from {name}")


def expected_k_from_name(path: Path) -> int:
    match = re.search(r"config_k([23])_", path.name)
    if not match:
        raise ValueError(f"cannot infer k from {path.name}")
    return int(match.group(1))


def audit_configs(rows: list[dict[str, object]]) -> None:
    output_dirs: list[str] = []
    for path in CONFIGS:
        try:
            config = load_yaml(path)
            add(rows, "config_parses_as_yaml", "PASS", "parsed", path)
        except Exception as exc:
            add(rows, "config_parses_as_yaml", "FAIL", str(exc), path)
            continue

        expected_group = expected_group_from_name(path)
        expected_k = expected_k_from_name(path)
        add(
            rows,
            "training_rule_is_phase10_preselected",
            "PASS" if config.get("training_rule") == "use_preselected_phase10_lite_group" else "FAIL",
            f"training_rule={config.get('training_rule')!r}",
            path,
        )
        add(
            rows,
            "manifest_points_to_phase10_lite",
            "PASS"
            if f"phase10_lite_matched_training_manifest_k{expected_k}.csv"
            in str(config.get("manifest_path", ""))
            else "FAIL",
            f"manifest_path={config.get('manifest_path')!r}",
            path,
        )
        add(
            rows,
            "phase10_group_matches_config_name",
            "PASS"
            if config.get("phase10_lite_group") == expected_group
            and config.get("experiment_group") == expected_group
            else "FAIL",
            f"experiment_group={config.get('experiment_group')!r}; phase10_lite_group={config.get('phase10_lite_group')!r}",
            path,
        )
        add(
            rows,
            "k_value_matches_config_name",
            "PASS" if int(config.get("images_per_identity_k", -1)) == expected_k else "FAIL",
            f"images_per_identity_k={config.get('images_per_identity_k')!r}; expected={expected_k}",
            path,
        )
        old_groups = [
            old
            for old in OLD_PHASE9D_GROUPS
            if old in str(config.get("experiment_group", "")) or old in str(config.get("phase10_lite_group", ""))
        ]
        add(
            rows,
            "no_old_phase9d_group_names",
            "PASS" if not old_groups else "FAIL",
            f"old_groups={old_groups}",
            path,
        )
        add(
            rows,
            "epochs_is_one",
            "PASS" if int(config.get("model", {}).get("epochs", -1)) == 1 else "FAIL",
            f"epochs={config.get('model', {}).get('epochs')!r}",
            path,
        )
        add(
            rows,
            "uses_megadescriptor_embedding",
            "PASS"
            if "megadescriptor" in str(config.get("embedding_path", "")).lower()
            and str(config.get("descriptor", "")).lower() == "megadescriptor"
            else "FAIL",
            f"descriptor={config.get('descriptor')!r}; embedding_path={config.get('embedding_path')!r}",
            path,
        )
        output_dir = str(config.get("output_dir", ""))
        output_dirs.append(output_dir)
        expected_fragments = [f"k{expected_k}", "split_1", expected_group]
        missing_fragments = [part for part in expected_fragments if part not in output_dir]
        add(
            rows,
            "output_dir_separated_by_k_split_group",
            "PASS" if not missing_fragments else "FAIL",
            f"output_dir={output_dir!r}; missing_fragments={missing_fragments}",
            path,
        )
    add(
        rows,
        "output_dirs_unique",
        "PASS" if len(output_dirs) == len(set(output_dirs)) else "FAIL",
        f"unique={len(set(output_dirs))}; total={len(output_dirs)}",
    )


def audit_script_text(rows: list[dict[str, object]]) -> None:
    train_path = PACKAGE_DIR / "train_phase10_lite_metric_learning.py"
    text = train_path.read_text(encoding="utf-8")
    forbidden_found = [pattern for pattern in OLD_SELECTION_PATTERNS if pattern in text]
    add(
        rows,
        "training_script_no_old_selection_patterns",
        "PASS" if not forbidden_found else "FAIL",
        f"forbidden_found={forbidden_found}",
        train_path,
    )
    add(
        rows,
        "training_script_requires_preselected_rule",
        "PASS" if "use_preselected_phase10_lite_group" in text else "FAIL",
        "explicit Phase 10-Lite rule present",
        train_path,
    )
    add(
        rows,
        "training_script_no_backbone_finetuning_reference",
        "PASS" if "backbone" not in text.lower() and "finetun" not in text.lower() else "FAIL",
        "no backbone fine-tuning text found" if "backbone" not in text.lower() else "backbone text found",
        train_path,
    )


def audit_required_files(rows: list[dict[str, object]]) -> None:
    for path in REQUIRED_FILES:
        add(
            rows,
            "required_file_exists",
            "PASS" if path.exists() else "FAIL",
            "exists" if path.exists() else "missing",
            path,
        )


def audit_no_training_outputs(rows: list[dict[str, object]]) -> None:
    result_root = OUTPUT_DIR / "metric_learning_results"
    found: list[Path] = []
    if result_root.exists():
        for name in EXPECTED_TRAINING_OUTPUT_NAMES:
            found.extend(result_root.rglob(name))
    add(
        rows,
        "no_training_outputs_generated_by_package_audit",
        "PASS" if not found else "FAIL",
        f"found_training_outputs={len(found)}",
        result_root,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    audit_required_files(rows)
    audit_configs(rows)
    audit_script_text(rows)
    audit_no_training_outputs(rows)

    audit = pd.DataFrame(rows, columns=["check_name", "status", "file", "detail"])
    audit.to_csv(AUDIT_CSV, index=False)
    fail_count = int((audit["status"] == "FAIL").sum())
    pass_count = int((audit["status"] == "PASS").sum())
    print(f"{'PASS' if fail_count == 0 else 'FAIL'} audit_phase10_lite_training_package")
    print(f"pass_count={pass_count}")
    print(f"fail_count={fail_count}")
    print(f"audit_csv={AUDIT_CSV}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
