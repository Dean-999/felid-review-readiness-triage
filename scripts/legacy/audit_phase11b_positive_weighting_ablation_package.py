#!/usr/bin/env python3
"""Audit Phase 11B positive-pair weighting ablation package."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "colab/phase11_metric_learning"
PAIR_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv"
OUT = PROJECT_ROOT / "outputs/czechlynx/phase11b/phase11b_positive_weighting_ablation_package_audit.csv"

REQUIRED_CONFIGS = {
    "config_phase11b_positive_raw.yaml": "raw",
    "config_phase11b_positive_floor05.yaml": "floor05",
    "config_phase11b_positive_sqrt.yaml": "sqrt",
    "config_phase11b_positive_clip035.yaml": "clip035",
}
REQUIRED_FILES = [
    "train_phase11_pair_weighted_metric_learning.py",
    "run_phase11b_positive_weighting_ablation.py",
    *REQUIRED_CONFIGS,
]
P11B_GROUPS = {
    "P11B_positive_raw",
    "P11B_positive_floor05",
    "P11B_positive_sqrt",
    "P11B_positive_clip035",
}
FORBIDDEN_TERMS = [
    "second-review",
    "second_review",
    "unique_name",
    "latitude",
    "longitude",
    "trap_id",
    "cell_code",
    "field deployment",
]


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

    train_script = PACKAGE_DIR / "train_phase11_pair_weighted_metric_learning.py"
    train_text = train_script.read_text(encoding="utf-8") if train_script.exists() else ""
    for mode in ["raw", "floor05", "sqrt", "clip035"]:
        add(rows, f"training_script_supports_{mode}", mode in train_text, f"mode={mode}")
    add(rows, "training_script_has_transform_function", "def transform_positive_weight" in train_text, "transform_positive_weight")

    add(rows, "pair_table_exists", PAIR_TABLE.exists(), str(PAIR_TABLE.relative_to(PROJECT_ROOT)))
    if PAIR_TABLE.exists():
        pair_table = pd.read_csv(PAIR_TABLE, usecols=["group_name"])
        add(
            rows,
            "h3_base_group_in_pair_table",
            "H3_pf_eri_quality_hybrid_matched_identity" in set(pair_table["group_name"].astype(str)),
            "H3_pf_eri_quality_hybrid_matched_identity",
        )

    observed_modes = set()
    observed_groups = set()
    for config_name, expected_mode in REQUIRED_CONFIGS.items():
        path = PACKAGE_DIR / config_name
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        prefix = f"config_{config_name}"
        observed_groups.add(str(config.get("experiment_group")))
        observed_modes.add(str(config.get("loss", {}).get("positive_weight_transform")))
        add(rows, f"{prefix}_experiment_group_phase11b", str(config.get("experiment_group")) in P11B_GROUPS, str(config.get("experiment_group")))
        add(
            rows,
            f"{prefix}_base_group_h3",
            str(config.get("base_group_name")) == "H3_pf_eri_quality_hybrid_matched_identity",
            str(config.get("base_group_name")),
        )
        add(rows, f"{prefix}_positive_transform", str(config.get("loss", {}).get("positive_weight_transform")) == expected_mode, expected_mode)
        add(
            rows,
            f"{prefix}_no_negative_reliability_control",
            str(config.get("loss", {}).get("pair_weight_mode")) == "positive_pair_weighting",
            str(config.get("loss", {}).get("pair_weight_mode")),
        )
        add(rows, f"{prefix}_epochs_one", int(config.get("model", {}).get("epochs", -1)) == 1, str(config.get("model", {}).get("epochs")))
        for key in ["manifest_path", "evaluation_manifest_path", "embedding_path", "pair_table_path"]:
            target = resolve_config_path(config, key)
            add(rows, f"{prefix}_{key}_exists", target.exists(), str(target.relative_to(PROJECT_ROOT)) if target.exists() else str(target))
        output_dir = str(config.get("output_dir", ""))
        add(rows, f"{prefix}_output_phase11b_specific", "outputs/czechlynx/phase11b/" in output_dir, output_dir)
        add(rows, f"{prefix}_does_not_overwrite_phase11_results", "outputs/czechlynx/phase11/metric_learning_results" not in output_dir, output_dir)
        add(rows, f"{prefix}_colab_project_root", str(config.get("project_root")) == "/content/felid-review-readiness-triage", str(config.get("project_root")))
        add(rows, f"{prefix}_no_raw_data_output", not output_dir.startswith("data/") and "/data/" not in output_dir, output_dir)

    add(rows, "all_required_modes_present", observed_modes == set(REQUIRED_CONFIGS.values()), f"observed={sorted(observed_modes)}")
    add(rows, "all_required_groups_present", observed_groups == P11B_GROUPS, f"observed={sorted(observed_groups)}")

    scanned_files = [PACKAGE_DIR / name for name in REQUIRED_FILES if (PACKAGE_DIR / name).exists()]
    scanned_files += [PROJECT_ROOT / "docs/phase11/phase11b_positive_weighting_ablation.md"]
    for term in FORBIDDEN_TERMS:
        hits = []
        for path in scanned_files:
            if path.exists() and term.lower() in path.read_text(encoding="utf-8", errors="ignore").lower():
                hits.append(str(path.relative_to(PROJECT_ROOT)))
        add(rows, f"forbidden_term_absent_{term}", not hits, f"hits={hits}")

    result_checkpoints = list((PROJECT_ROOT / "outputs/czechlynx/phase11b").glob("**/projection_head.pt"))
    add(rows, "no_phase11b_checkpoints_present", len(result_checkpoints) == 0, f"checkpoints={len(result_checkpoints)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 11B package audit: PASS={pass_count} FAIL={fail_count} output={OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
