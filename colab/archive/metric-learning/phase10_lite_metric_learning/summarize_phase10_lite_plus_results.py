#!/usr/bin/env python3
"""Summarize Phase 10-Lite Plus Colab results after runs exist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", default="outputs/czechlynx/phase10_lite/metric_learning_plus_results")
    args = parser.parse_args()
    root = Path(args.results_root)
    if not root.exists():
        print(f"NO_RUN_OUTPUTS: results root does not exist: {root}")
        return 0

    run_records: list[dict[str, object]] = []
    retrieval_frames: list[pd.DataFrame] = []
    failure_frames: list[pd.DataFrame] = []
    for metrics_path in root.rglob("phase10_lite_plus_retrieval_metrics.csv"):
        run_dir = metrics_path.parent
        train_metrics = read_csv_if_exists(run_dir / "phase10_lite_plus_training_metrics.csv")
        retrieval = read_csv_if_exists(metrics_path)
        failures = read_csv_if_exists(run_dir / "phase10_lite_plus_failure_cases.csv")
        config_path = run_dir / "config_used.json"
        config = {}
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
        if retrieval is not None:
            retrieval_frames.append(retrieval.assign(run_dir=str(run_dir)))
        if failures is not None:
            failure_frames.append(failures.assign(run_dir=str(run_dir)))
        run_records.append(
            {
                "run_dir": str(run_dir),
                "has_training_metrics": train_metrics is not None,
                "has_retrieval_metrics": retrieval is not None,
                "has_failure_cases": failures is not None,
                "has_config_used": bool(config),
                "has_checkpoint": (run_dir / "projection_head.pt").exists(),
                "experiment_group": config.get("experiment_group", ""),
                "split_id": config.get("split_id", ""),
            }
        )

    if not run_records:
        print(f"NO_RUN_OUTPUTS: no retrieval metric files found under {root}")
        return 0

    run_records_df = pd.DataFrame(run_records)
    run_records_df.to_csv(root / "phase10_lite_plus_run_records.csv", index=False)
    retrieval_df = pd.concat(retrieval_frames, ignore_index=True) if retrieval_frames else pd.DataFrame()
    retrieval_df.to_csv(root / "phase10_lite_plus_retrieval_metrics.csv", index=False)
    if failure_frames:
        pd.concat(failure_frames, ignore_index=True).to_csv(root / "phase10_lite_plus_failure_cases.csv", index=False)

    group_summary = (
        retrieval_df.groupby("experiment_group")
        .agg(
            split_count=("split_id", "nunique"),
            mean_mAP=("mAP", "mean"),
            mean_MRR=("MRR", "mean"),
            mean_top1_accuracy=("top1_accuracy", "mean"),
            mean_top5_accuracy=("top5_accuracy", "mean"),
            mean_false_candidate_burden=("false_candidate_burden", "mean"),
            mean_query_coverage=("query_coverage", "mean"),
        )
        .reset_index()
    )
    group_summary.to_csv(root / "phase10_lite_plus_group_summary.csv", index=False)

    baselines = ["B3_random_matched_identity", "C3_quality_proxy_matched_identity"]
    candidates = ["H3_pf_eri_quality_hybrid_matched_identity", "E4_pf_eri_weighted_all_train_reference"]
    deltas: list[dict[str, object]] = []
    for split_id, split_df in retrieval_df.groupby("split_id"):
        for candidate in candidates:
            cand = split_df[split_df["experiment_group"] == candidate]
            if cand.empty:
                continue
            cand_row = cand.iloc[0]
            for baseline in baselines:
                base = split_df[split_df["experiment_group"] == baseline]
                if base.empty:
                    continue
                base_row = base.iloc[0]
                deltas.append(
                    {
                        "split_id": split_id,
                        "candidate": candidate,
                        "baseline": baseline,
                        "delta_mAP": float(cand_row["mAP"] - base_row["mAP"]),
                        "delta_MRR": float(cand_row["MRR"] - base_row["MRR"]),
                        "delta_false_candidate_burden": float(cand_row["false_candidate_burden"] - base_row["false_candidate_burden"]),
                        "delta_query_coverage": float(cand_row["query_coverage"] - base_row["query_coverage"]),
                    }
                )
    pd.DataFrame(deltas).to_csv(root / "phase10_lite_plus_pairwise_delta_summary.csv", index=False)
    print("PASS summarize_phase10_lite_plus_results")
    print(f"run_count={len(run_records_df)}")
    print(f"retrieval_metric_rows={len(retrieval_df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
