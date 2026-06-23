#!/usr/bin/env python3
"""Patch Phase 10-Lite Plus configs for Google Drive Colab paths."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

CONFIGS = [
    "config_plus_k3_random_matched.yaml",
    "config_plus_k3_quality_proxy_matched.yaml",
    "config_plus_k3_pf_eri_matched.yaml",
    "config_plus_k3_pf_eri_quality_hybrid.yaml",
    "config_plus_e4_pf_eri_weighted_all_train.yaml",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default="/content/drive/MyDrive/felid_phase10_lite_plus")
    args = parser.parse_args()
    package_dir = Path(__file__).resolve().parent
    out_dir = package_dir / "patched_configs"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for split_id in [1, 2, 3, 4, 5]:
        for config_name in CONFIGS:
            with open(package_dir / config_name, "r", encoding="utf-8") as handle:
                config = yaml.safe_load(handle)
            group = config["phase10_lite_plus_group"]
            config["project_root"] = args.project_root
            config["split_id"] = split_id
            config["manifest_path"] = f"{args.project_root}/phase10_lite/phase10_lite_plus_matched_training_manifest_k3.csv"
            config["evaluation_manifest_path"] = f"{args.project_root}/phase9d_image_training_manifest_internal.csv"
            config["embedding_path"] = f"{args.project_root}/czechlynx_phase4c_megadescriptor_embeddings.csv"
            config["output_dir"] = f"{args.project_root}/metric_learning_plus_results/split_{split_id}/{group}"
            patched_name = f"split_{split_id}_{config_name}"
            patched_path = out_dir / patched_name
            with open(patched_path, "w", encoding="utf-8") as handle:
                yaml.safe_dump(config, handle, sort_keys=False)
            rows.append(
                {
                    "split_id": split_id,
                    "experiment_group": group,
                    "source_config": config_name,
                    "patched_config": str(patched_path),
                    "output_dir": config["output_dir"],
                    "manifest_path": config["manifest_path"],
                    "embedding_path": config["embedding_path"],
                }
            )
    index_path = out_dir / "phase10_lite_plus_patched_config_index.csv"
    pd.DataFrame(rows).to_csv(index_path, index=False)
    print("PASS patch_phase10_lite_plus_colab_configs")
    print(f"patched_config_count={len(rows)}")
    print(f"index_csv={index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
