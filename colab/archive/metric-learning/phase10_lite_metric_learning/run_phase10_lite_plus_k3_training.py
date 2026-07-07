#!/usr/bin/env python3
"""Dry-run runner for Phase 10-Lite Plus k=3 Colab training commands."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

CONFIGS = [
    "config_plus_k3_random_matched.yaml",
    "config_plus_k3_quality_proxy_matched.yaml",
    "config_plus_k3_pf_eri_matched.yaml",
    "config_plus_k3_pf_eri_quality_hybrid.yaml",
    "config_plus_e4_pf_eri_weighted_all_train.yaml",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print planned runs without executing training.")
    parser.add_argument("--execute", action="store_true", help="Actually run training commands in Colab.")
    parser.add_argument("--splits", nargs="*", type=int, default=[1, 2, 3, 4, 5])
    args = parser.parse_args()
    if args.dry_run and args.execute:
        raise SystemExit("--dry-run and --execute are mutually exclusive")
    root = Path(__file__).resolve().parent
    print("Phase 10-Lite Plus planned commands:")
    print("Default mode is dry-run/package inspection. Use --execute only in Colab after uploads are verified.")
    run_records = []
    for split_id in args.splits:
        for config_name in CONFIGS:
            config_path = root / config_name
            with open(config_path, "r", encoding="utf-8") as handle:
                config = yaml.safe_load(handle)
            output_dir = str(config["output_dir"]).replace("split_1", f"split_{split_id}")
            command = [
                "python",
                str(root / "train_phase10_lite_plus_metric_learning.py"),
                "--config",
                str(config_path),
            ]
            record = {
                "split_id": split_id,
                "group": config["phase10_lite_plus_group"],
                "config_path": str(config_path),
                "output_dir": output_dir,
                "command": " ".join(command),
                "path_placeholder_patchable": "split_1" in str(config["output_dir"]),
            }
            run_records.append(record)
            print(
                "planned_run "
                f"split_id={record['split_id']} "
                f"group={record['group']} "
                f"config_path={record['config_path']} "
                f"output_dir={record['output_dir']} "
                f"path_placeholder_patchable={record['path_placeholder_patchable']} "
                f"command={record['command']}"
            )
            if args.execute:
                print("WARNING: config split_id/output_dir must be patched per split before execution.")
                subprocess.run(command, check=True)
    print(f"planned_run_count={len(run_records)}")
    if len(run_records) != len(args.splits) * len(CONFIGS):
        raise SystemExit("planned run count mismatch")
    if args.execute:
        record_path = root / "phase10_lite_plus_run_records.json"
        record_path.write_text(json.dumps(run_records, indent=2), encoding="utf-8")
        print(f"run_records={record_path}")


if __name__ == "__main__":
    main()
