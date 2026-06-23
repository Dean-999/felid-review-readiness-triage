#!/usr/bin/env python3
"""Audit Phase 11 Colab training package without running training."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "colab/phase11_metric_learning"
PAIR_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv"
OUT = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_training_package_audit.csv"

REQUIRED_FILES = [
    "train_phase11_pair_weighted_metric_learning.py",
    "evaluate_phase11_retrieval.py",
    "run_phase11_one_epoch.py",
    "config_phase11_c3_quality_proxy.yaml",
    "config_phase11_h3_pf_eri_quality_hybrid.yaml",
    "config_phase11_p11_positive_pair_weighting.yaml",
    "config_phase11_p11_positive_weighting_negative_reliability_control.yaml",
]
CONFIGS = [name for name in REQUIRED_FILES if name.endswith(".yaml")]
SUPPORTED_GROUPS = {
    "C3_quality_proxy_matched_identity",
    "H3_pf_eri_quality_hybrid_matched_identity",
    "P11_positive_pair_weighting",
    "P11_positive_weighting_negative_reliability_control",
}
SUPPORTED_BASE_GROUPS = {
    "C3_quality_proxy_matched_identity",
    "H3_pf_eri_quality_hybrid_matched_identity",
}


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def resolve_config_path(config: dict[str, object], key: str) -> Path:
    path = Path(str(config[key]))
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def main() -> None:
    rows: list[dict[str, object]] = []
    for name in REQUIRED_FILES:
        path = PACKAGE_DIR / name
        add(rows, f"exists_{name}", path.exists(), str(path.relative_to(PROJECT_ROOT)))

    add(rows, "pair_table_exists", PAIR_TABLE.exists(), str(PAIR_TABLE.relative_to(PROJECT_ROOT)))
    pair_groups = set()
    if PAIR_TABLE.exists():
        pair_table = pd.read_csv(PAIR_TABLE, usecols=["split_id", "group_name"])
        pair_groups = set(pair_table["group_name"].astype(str).unique())
        add(rows, "pair_table_nonempty", len(pair_table) > 0, f"rows={len(pair_table)}")

    for config_name in CONFIGS:
        path = PACKAGE_DIR / config_name
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        prefix = f"config_{config_name}"
        add(rows, f"{prefix}_training_rule", config.get("training_rule") == "use_phase11_pair_level_pf_eri_weights", str(config.get("training_rule")))
        add(rows, f"{prefix}_experiment_group_supported", config.get("experiment_group") in SUPPORTED_GROUPS, str(config.get("experiment_group")))
        add(rows, f"{prefix}_base_group_supported", config.get("base_group_name") in SUPPORTED_BASE_GROUPS, str(config.get("base_group_name")))
        if pair_groups:
            add(rows, f"{prefix}_base_group_in_pair_table", str(config.get("base_group_name")) in pair_groups, str(config.get("base_group_name")))
        for key in ["manifest_path", "evaluation_manifest_path", "embedding_path"]:
            target = resolve_config_path(config, key)
            add(rows, f"{prefix}_{key}_exists", target.exists(), str(target.relative_to(PROJECT_ROOT)) if target.exists() else str(target))
        target_pair = resolve_config_path(config, "pair_table_path")
        add(rows, f"{prefix}_pair_table_path_exists", target_pair.exists(), str(target_pair.relative_to(PROJECT_ROOT)) if target_pair.exists() else str(target_pair))
        output_dir = str(config.get("output_dir", ""))
        add(rows, f"{prefix}_output_dir_not_raw_data", not output_dir.startswith("data/") and "/data/" not in output_dir, output_dir)
        add(rows, f"{prefix}_output_under_phase11", "outputs/czechlynx/phase11/" in output_dir, output_dir)
        add(rows, f"{prefix}_epochs_one", int(config.get("model", {}).get("epochs", -1)) == 1, str(config.get("model", {}).get("epochs")))
        add(
            rows,
            f"{prefix}_loss_mode_present",
            config.get("loss", {}).get("pair_weight_mode")
            in {"uniform_pair_weight", "positive_pair_weighting", "positive_weighting_negative_reliability_control"},
            str(config.get("loss", {}).get("pair_weight_mode")),
        )

    result_dirs = list((PROJECT_ROOT / "outputs/czechlynx/phase11").glob("metric_learning_results/**/projection_head.pt"))
    add(rows, "no_phase11_checkpoints_present", len(result_dirs) == 0, f"checkpoints={len(result_dirs)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 11 training package audit: PASS={pass_count} FAIL={fail_count} output={OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
