#!/usr/bin/env python3
"""Plan staged Phase 10-Lite Plus Colab runs without executing training."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

CONFIGS = [
    "config_plus_k3_random_matched.yaml",
    "config_plus_k3_quality_proxy_matched.yaml",
    "config_plus_k3_pf_eri_matched.yaml",
    "config_plus_k3_pf_eri_quality_hybrid.yaml",
    "config_plus_e4_pf_eri_weighted_all_train.yaml",
]


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def planned_record(root: Path, config_name: str, split_id: int) -> dict[str, object]:
    config_path = root / config_name
    cfg = load_config(config_path)
    output_dir = str(cfg["output_dir"]).replace("split_1", f"split_{split_id}")
    return {
        "split_id": split_id,
        "group": cfg["phase10_lite_plus_group"],
        "config_path": str(config_path),
        "output_dir": output_dir,
        "patchable_split_id": "split_id" in cfg,
        "patchable_output_dir": "split_1" in str(cfg["output_dir"]),
        "train_command": f"python {root / 'train_phase10_lite_plus_metric_learning.py'} --config {config_path}",
        "eval_command": f"python {root / 'evaluate_phase10_lite_plus_retrieval.py'} --config {config_path} --checkpoint <checkpoint_path>",
    }


def print_records(label: str, records: list[dict[str, object]]) -> None:
    print(label)
    for rec in records:
        print(
            "planned_run "
            f"split_id={rec['split_id']} "
            f"group={rec['group']} "
            f"config_path={rec['config_path']} "
            f"output_dir={rec['output_dir']} "
            f"patchable_split_id={rec['patchable_split_id']} "
            f"patchable_output_dir={rec['patchable_output_dir']}"
        )
    print(f"{label.lower().replace(' ', '_')}_count={len(records)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    root = Path(__file__).resolve().parent
    stage1 = [planned_record(root, config, 1) for config in CONFIGS]
    stage2 = [planned_record(root, config, split_id) for split_id in [1, 2, 3, 4, 5] for config in CONFIGS]
    print("DRY RUN ONLY: no training, evaluation, checkpoint, or upload action is performed.")
    print_records("Stage 1 planned runs", stage1)
    print_records("Stage 2 planned runs", stage2)
    if len(stage1) != 5 or len(stage2) != 25:
        raise SystemExit("planned run count mismatch")
    if not all(rec["patchable_split_id"] and rec["patchable_output_dir"] for rec in stage2):
        raise SystemExit("one or more configs are not patchable by split_id/output_dir")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
