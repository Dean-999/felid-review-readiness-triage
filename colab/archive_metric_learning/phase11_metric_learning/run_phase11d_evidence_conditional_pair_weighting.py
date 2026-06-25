#!/usr/bin/env python3
"""Dry-run runner for Phase 11D evidence-conditional pair weighting."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

CONFIGS = [
    "config_phase11d_pos_rescue_q75_floor035.yaml",
    "config_phase11d_pos_rescue_q85_floor035.yaml",
    "config_phase11d_pos_rescue_q75_floor035_softneg_q95_w085.yaml",
    "config_phase11d_pos_rescue_q85_floor035_softneg_q95_w085.yaml",
]


def planned_record(root: Path, config_name: str, split_id: int) -> dict[str, object]:
    config_path = root / config_name
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    output_dir = str(config["output_dir"]).replace("split_1", f"split_{split_id}")
    command = [
        "python",
        str(root / "train_phase11_pair_weighted_metric_learning.py"),
        "--config",
        str(config_path),
    ]
    loss = config["loss"]
    return {
        "split_id": int(split_id),
        "experiment_group": str(config["experiment_group"]),
        "base_group_name": str(config["base_group_name"]),
        "positive_rescue_similarity_quantile": float(loss["positive_rescue_similarity_quantile"]),
        "positive_rescue_floor": float(loss["positive_rescue_floor"]),
        "soft_negative_enabled": bool(loss["soft_negative_enabled"]),
        "soft_negative_weight": float(loss["soft_negative_weight"]),
        "config_path": str(config_path),
        "output_dir": output_dir,
        "command": " ".join(command),
        "requires_config_patch_before_execute": int(config["split_id"]) != int(split_id),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Actually run training commands in Colab.")
    parser.add_argument("--splits", nargs="*", type=int, default=[1, 3])
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    print("Phase 11D evidence-conditional pair-weighting planned runs:")
    print("Default mode is dry-run. Default splits are 1 and 3. Use --execute only in Colab after configs are patched.")
    records = []
    for split_id in args.splits:
        for config_name in CONFIGS:
            record = planned_record(root, config_name, split_id)
            records.append(record)
            print(
                "planned_run "
                f"split_id={record['split_id']} "
                f"experiment_group={record['experiment_group']} "
                f"base_group_name={record['base_group_name']} "
                f"positive_q={record['positive_rescue_similarity_quantile']} "
                f"soft_negative_enabled={record['soft_negative_enabled']} "
                f"soft_negative_weight={record['soft_negative_weight']} "
                f"requires_config_patch_before_execute={record['requires_config_patch_before_execute']} "
                f"command={record['command']}"
            )
            if args.execute:
                if record["requires_config_patch_before_execute"]:
                    raise SystemExit("Patch split_id/output_dir configs before --execute.")
                subprocess.run(str(record["command"]).split(), check=True)
    record_path = root / "phase11d_evidence_conditional_pair_weighting_run_records.json"
    record_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"planned_run_count={len(records)}")
    print(f"run_records={record_path}")


if __name__ == "__main__":
    main()
