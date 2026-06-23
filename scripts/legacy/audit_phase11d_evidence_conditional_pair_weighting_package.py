#!/usr/bin/env python3
"""Audit Phase 11D evidence-conditional pair-weighting package."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "colab/phase11_metric_learning"
PAIR_TABLE = PROJECT_ROOT / "outputs/czechlynx/phase11/phase11_pair_level_pf_eri_table.csv"
PREVIEW = PROJECT_ROOT / (
    "outputs/czechlynx/phase11d/evidence_conditional_pair_weighting/"
    "phase11d_conditional_pair_count_preview.csv"
)
OUT = PROJECT_ROOT / "outputs/czechlynx/phase11d/evidence_conditional_pair_weighting/phase11d_package_audit.csv"

CONFIGS = {
    "config_phase11d_pos_rescue_q75_floor035.yaml": (0.75, False),
    "config_phase11d_pos_rescue_q85_floor035.yaml": (0.85, False),
    "config_phase11d_pos_rescue_q75_floor035_softneg_q95_w085.yaml": (0.75, True),
    "config_phase11d_pos_rescue_q85_floor035_softneg_q95_w085.yaml": (0.85, True),
}
REQUIRED_FILES = [
    "train_phase11_pair_weighted_metric_learning.py",
    "run_phase11d_evidence_conditional_pair_weighting.py",
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
    "pattern_pair_score",
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


def close_enough(value: object, expected: float) -> bool:
    return abs(float(value) - expected) < 1e-9


def main() -> None:
    rows: list[dict[str, object]] = []
    for name in REQUIRED_FILES:
        path = PACKAGE_DIR / name
        add(rows, f"exists_{name}", path.exists(), str(path.relative_to(PROJECT_ROOT)))

    train_script = PACKAGE_DIR / "train_phase11_pair_weighted_metric_learning.py"
    text = train_script.read_text(encoding="utf-8") if train_script.exists() else ""
    for token in [
        "sqrt_conditional_rescue",
        "positive_rescue_enabled",
        "positive_rescue_reliability_max",
        "positive_rescue_similarity_quantile",
        "positive_rescue_pattern_min",
        "positive_rescue_floor",
        "soft_negative_enabled",
        "soft_negative_similarity_quantile",
        "soft_negative_reliability_max",
        "soft_negative_weight",
    ]:
        add(rows, f"training_script_supports_{token}", token in text, token)

    add(rows, "pair_table_exists", PAIR_TABLE.exists(), str(PAIR_TABLE.relative_to(PROJECT_ROOT)))
    if PAIR_TABLE.exists():
        cols = set(pd.read_csv(PAIR_TABLE, nrows=0).columns)
        missing = sorted(PAIR_REQUIRED_COLUMNS - cols)
        add(rows, "pair_table_conditional_columns", not missing, f"missing={missing}")

    for config_name, (expected_q, expected_softneg) in CONFIGS.items():
        path = PACKAGE_DIR / config_name
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        loss = config.get("loss", {})
        prefix = f"config_{config_name}"
        add(
            rows,
            f"{prefix}_base_group_h3",
            str(config.get("base_group_name")) == "H3_pf_eri_quality_hybrid_matched_identity",
            str(config.get("base_group_name")),
        )
        add(rows, f"{prefix}_phase11d_output", "outputs/czechlynx/phase11d/" in str(config.get("output_dir")), str(config.get("output_dir")))
        add(rows, f"{prefix}_does_not_overwrite_phase11", "outputs/czechlynx/phase11/metric_learning_results" not in str(config.get("output_dir")), str(config.get("output_dir")))
        add(rows, f"{prefix}_does_not_overwrite_phase11b", "outputs/czechlynx/phase11b/" not in str(config.get("output_dir")), str(config.get("output_dir")))
        add(rows, f"{prefix}_does_not_overwrite_phase11c", "outputs/czechlynx/phase11c/" not in str(config.get("output_dir")), str(config.get("output_dir")))
        add(rows, f"{prefix}_transform", str(loss.get("positive_weight_transform")) == "sqrt_conditional_rescue", str(loss.get("positive_weight_transform")))
        add(rows, f"{prefix}_positive_rescue_enabled", bool(loss.get("positive_rescue_enabled")) is True, str(loss.get("positive_rescue_enabled")))
        add(rows, f"{prefix}_positive_reliability_max", close_enough(loss.get("positive_rescue_reliability_max"), 0.40), str(loss.get("positive_rescue_reliability_max")))
        add(rows, f"{prefix}_positive_floor", close_enough(loss.get("positive_rescue_floor"), 0.35), str(loss.get("positive_rescue_floor")))
        add(rows, f"{prefix}_positive_pattern_min", close_enough(loss.get("positive_rescue_pattern_min"), 0.45), str(loss.get("positive_rescue_pattern_min")))
        add(rows, f"{prefix}_positive_similarity_quantile", close_enough(loss.get("positive_rescue_similarity_quantile"), expected_q), str(loss.get("positive_rescue_similarity_quantile")))
        add(rows, f"{prefix}_soft_negative_enabled", bool(loss.get("soft_negative_enabled")) is expected_softneg, str(loss.get("soft_negative_enabled")))
        add(rows, f"{prefix}_soft_negative_quantile", close_enough(loss.get("soft_negative_similarity_quantile"), 0.95), str(loss.get("soft_negative_similarity_quantile")))
        add(rows, f"{prefix}_soft_negative_reliability_max", close_enough(loss.get("soft_negative_reliability_max"), 0.40), str(loss.get("soft_negative_reliability_max")))
        expected_weight = 0.85 if expected_softneg else 1.0
        add(rows, f"{prefix}_soft_negative_weight", close_enough(loss.get("soft_negative_weight"), expected_weight), str(loss.get("soft_negative_weight")))
        add(rows, f"{prefix}_no_negative_weight_025", "0.25" not in str(loss), str(loss))
        add(rows, f"{prefix}_no_old_negative_control", str(loss.get("pair_weight_mode")) == "positive_pair_weighting", str(loss.get("pair_weight_mode")))
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

    scanned_files = [PACKAGE_DIR / name for name in REQUIRED_FILES if (PACKAGE_DIR / name).exists()]
    scanned_files += [
        PROJECT_ROOT / "docs/phase11/phase11d_evidence_conditional_pair_weighting.md",
        PROJECT_ROOT / "scripts/preview_phase11d_conditional_pair_counts.py",
    ]
    for term in FORBIDDEN_TERMS:
        hits = []
        for path in scanned_files:
            if path.exists() and term.lower() in path.read_text(encoding="utf-8", errors="ignore").lower():
                hits.append(str(path.relative_to(PROJECT_ROOT)))
        add(rows, f"forbidden_term_absent_{term}", not hits, f"hits={hits}")

    result_checkpoints = list((PROJECT_ROOT / "outputs/czechlynx/phase11d").glob("**/projection_head.pt"))
    add(rows, "no_phase11d_checkpoints_present", len(result_checkpoints) == 0, f"checkpoints={len(result_checkpoints)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 11D package audit: PASS={pass_count} FAIL={fail_count} output={OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
