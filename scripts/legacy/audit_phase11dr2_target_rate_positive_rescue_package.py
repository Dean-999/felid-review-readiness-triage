#!/usr/bin/env python3
"""Audit Phase 11D-R2 target-rate positive-rescue package."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "colab/phase11_metric_learning"
PAIR_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv"
PREVIEW = PROJECT_ROOT / (
    "outputs/czechlynx/phase11d/target_rate_positive_rescue/"
    "phase11dr2_target_rate_positive_rescue_count_preview.csv"
)
OUT = PROJECT_ROOT / "outputs/czechlynx/phase11d/target_rate_positive_rescue/phase11dr2_package_audit.csv"

CONFIGS = {
    "config_phase11dr2_target05_floor035.yaml": {
        "group": "P11DR2_target05_floor035",
        "target_fraction": 0.05,
        "floor": 0.35,
    },
    "config_phase11dr2_target10_floor035.yaml": {
        "group": "P11DR2_target10_floor035",
        "target_fraction": 0.10,
        "floor": 0.35,
    },
    "config_phase11dr2_target10_floor040.yaml": {
        "group": "P11DR2_target10_floor040",
        "target_fraction": 0.10,
        "floor": 0.40,
    },
}

REQUIRED_FILES = [
    "train_phase11_pair_weighted_metric_learning.py",
    "run_phase11dr2_target_rate_positive_rescue.py",
    *CONFIGS,
]
PAIR_REQUIRED_COLUMNS = {
    "split_id",
    "group_name",
    "image_id_a",
    "image_id_b",
    "same_identity",
    "descriptor_similarity",
    "pair_reliability_score",
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


def close_enough(value: object, expected: float) -> bool:
    return abs(float(value) - expected) < 1e-9


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
    text = train_script.read_text(encoding="utf-8") if train_script.exists() else ""
    for token in [
        "sqrt_target_rate_rescue",
        "target_rescue_enabled",
        "target_rescue_fraction",
        "target_rescue_reliability_max",
        "target_rescue_floor",
        "descriptor_times_one_minus_reliability",
        "target_rescue_selected",
    ]:
        add(rows, f"training_script_supports_{token}", token in text, token)

    add(rows, "pair_table_exists", PAIR_TABLE.exists(), str(PAIR_TABLE.relative_to(PROJECT_ROOT)))
    if PAIR_TABLE.exists():
        cols = set(pd.read_csv(PAIR_TABLE, nrows=0).columns)
        missing = sorted(PAIR_REQUIRED_COLUMNS - cols)
        add(rows, "pair_table_target_rate_columns", not missing, f"missing={missing}")

    for config_name, expected in CONFIGS.items():
        path = PACKAGE_DIR / config_name
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        loss = config.get("loss", {})
        prefix = f"config_{config_name}"
        add(rows, f"{prefix}_group_name", str(config.get("experiment_group")) == expected["group"], str(config.get("experiment_group")))
        add(
            rows,
            f"{prefix}_base_group_h3",
            str(config.get("base_group_name")) == "H3_pf_eri_quality_hybrid_matched_identity",
            str(config.get("base_group_name")),
        )
        out_dir = str(config.get("output_dir"))
        add(rows, f"{prefix}_phase11dr2_output", "outputs/czechlynx/phase11d/target_rate_positive_rescue/" in out_dir, out_dir)
        add(rows, f"{prefix}_not_original_phase11d_output", "outputs/czechlynx/phase11d/evidence_conditional_pair_weighting/" not in out_dir, out_dir)
        add(rows, f"{prefix}_not_phase11dr_output", "outputs/czechlynx/phase11d/revised_positive_rescue/" not in out_dir, out_dir)
        add(rows, f"{prefix}_does_not_overwrite_phase11", "outputs/czechlynx/phase11/metric_learning_results" not in out_dir, out_dir)
        add(rows, f"{prefix}_does_not_overwrite_phase11b", "outputs/czechlynx/phase11b/" not in out_dir, out_dir)
        add(rows, f"{prefix}_does_not_overwrite_phase11c", "outputs/czechlynx/phase11c/" not in out_dir, out_dir)
        add(rows, f"{prefix}_transform", str(loss.get("positive_weight_transform")) == "sqrt_target_rate_rescue", str(loss.get("positive_weight_transform")))
        add(rows, f"{prefix}_positive_rescue_disabled", bool(loss.get("positive_rescue_enabled")) is False, str(loss.get("positive_rescue_enabled")))
        add(rows, f"{prefix}_target_rescue_enabled", bool(loss.get("target_rescue_enabled")) is True, str(loss.get("target_rescue_enabled")))
        add(rows, f"{prefix}_target_fraction", close_enough(loss.get("target_rescue_fraction"), expected["target_fraction"]), str(loss.get("target_rescue_fraction")))
        add(rows, f"{prefix}_target_reliability_max", close_enough(loss.get("target_rescue_reliability_max"), 0.55), str(loss.get("target_rescue_reliability_max")))
        add(rows, f"{prefix}_target_floor", close_enough(loss.get("target_rescue_floor"), expected["floor"]), str(loss.get("target_rescue_floor")))
        add(rows, f"{prefix}_target_score", str(loss.get("target_rescue_score")) == "descriptor_times_one_minus_reliability", str(loss.get("target_rescue_score")))
        add(rows, f"{prefix}_soft_negative_disabled", bool(loss.get("soft_negative_enabled")) is False, str(loss.get("soft_negative_enabled")))
        add(rows, f"{prefix}_no_negative_weight_025", "0.25" not in str(loss), str(loss))
        add(rows, f"{prefix}_pair_weight_mode", str(loss.get("pair_weight_mode")) == "positive_pair_weighting", str(loss.get("pair_weight_mode")))
        add(rows, f"{prefix}_epochs_one", int(config.get("model", {}).get("epochs", -1)) == 1, str(config.get("model", {}).get("epochs")))
        add(rows, f"{prefix}_colab_project_root", str(config.get("project_root")) == "/content/felid-review-readiness-triage", str(config.get("project_root")))
        for key in ["manifest_path", "evaluation_manifest_path", "embedding_path", "pair_table_path"]:
            target = resolve_config_path(config, key)
            add(rows, f"{prefix}_{key}_exists", target.exists(), str(target.relative_to(PROJECT_ROOT)) if target.exists() else str(target))

    add(rows, "preview_exists", PREVIEW.exists(), str(PREVIEW.relative_to(PROJECT_ROOT)))
    if PREVIEW.exists():
        preview = pd.read_csv(PREVIEW)
        add(rows, "preview_nonempty", len(preview) > 0, f"rows={len(preview)}")
        add(rows, "preview_splits_1_3", set(preview["split_id"].astype(int)) == {1, 3}, f"splits={sorted(set(preview['split_id'].astype(int)))}")
        add(rows, "preview_nonzero_all_groups", (preview["actual_rescued_count"].astype(int) > 0).all(), preview[["experiment_group", "actual_rescued_count"]].to_dict("records").__repr__())
        enough = preview["candidate_positive_pairs"].astype(int) >= preview["target_rescue_count"].astype(int)
        within = (preview["actual_rescued_count"].astype(int) - preview["target_rescue_count"].astype(int)).abs() <= 1
        add(rows, "preview_target_tolerance_when_candidates_available", bool((within[enough]).all()), preview[["experiment_group", "candidate_positive_pairs", "target_rescue_count", "actual_rescued_count"]].to_dict("records").__repr__())

    scanned_files = [PACKAGE_DIR / name for name in REQUIRED_FILES if (PACKAGE_DIR / name).exists()]
    scanned_files += [
        PROJECT_ROOT / "docs/phase11/phase11dr2_target_rate_positive_rescue.md",
        PROJECT_ROOT / "scripts/preview_phase11dr2_target_rate_positive_rescue_counts.py",
    ]
    for term in FORBIDDEN_TERMS:
        hits = []
        for path in scanned_files:
            if path.exists() and term.lower() in path.read_text(encoding="utf-8", errors="ignore").lower():
                hits.append(str(path.relative_to(PROJECT_ROOT)))
        add(rows, f"forbidden_term_absent_{term}", not hits, f"hits={hits}")

    result_checkpoints = list((PROJECT_ROOT / "outputs/czechlynx/phase11d/target_rate_positive_rescue").glob("**/projection_head.pt"))
    add(rows, "no_phase11dr2_checkpoints_present", len(result_checkpoints) == 0, f"checkpoints={len(result_checkpoints)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 11D-R2 package audit: PASS={pass_count} FAIL={fail_count} output={OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
