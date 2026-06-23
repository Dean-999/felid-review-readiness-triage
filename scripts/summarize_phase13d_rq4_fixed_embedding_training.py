#!/usr/bin/env python3
"""Summarize Phase 13D RQ4 fixed-embedding training evidence.

Input is one or more retrieval metric CSV files produced by
build_phase13d_rq4_fixed_embedding_training.py. The summary reports paired
policy contrasts across split/descriptor runs so Phase 13D can be interpreted
as a confidence-building experiment rather than a single-run score table.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "outputs/czechlynx/phase13/rq4_fixed_embedding_training/phase13d_rq4_retrieval_metrics.csv"
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/rq4_fixed_embedding_training"
CONTRASTS_OUT = OUT_DIR / "phase13d_rq4_policy_contrast_summary.csv"
CONFIDENCE_OUT = OUT_DIR / "phase13d_rq4_policy_confidence_statement.md"

PRIMARY_POLICIES = [
    "descriptor_only",
    "random_control",
    "quality_control",
    "pf_eri_positive",
    "pf_eri_conflict_aware",
]

METRICS = [
    "mAP_at_k",
    "MRR_at_k",
    "top1_accuracy",
    "top5_accuracy",
    "false_top1_rate",
    "false_candidate_burden_at_k",
]


def load_inputs(paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in paths]
    frame = pd.concat(frames, ignore_index=True)
    frame["run_key"] = frame["split_id"].astype(str) + "::" + frame["descriptor"].astype(str)
    return frame


def paired_contrast(frame: pd.DataFrame, policy_id: str, baseline_id: str, metric: str) -> dict[str, object]:
    wide = frame.pivot_table(index="run_key", columns="policy_id", values=metric, aggfunc="mean")
    if policy_id not in wide.columns or baseline_id not in wide.columns:
        return {
            "policy_id": policy_id,
            "baseline_id": baseline_id,
            "metric": metric,
            "paired_run_count": 0,
            "mean_delta": np.nan,
            "median_delta": np.nan,
            "positive_delta_fraction": np.nan,
        }
    delta = (wide[policy_id] - wide[baseline_id]).dropna()
    return {
        "policy_id": policy_id,
        "baseline_id": baseline_id,
        "metric": metric,
        "paired_run_count": int(len(delta)),
        "mean_delta": float(delta.mean()) if len(delta) else np.nan,
        "median_delta": float(delta.median()) if len(delta) else np.nan,
        "positive_delta_fraction": float((delta > 0).mean()) if len(delta) else np.nan,
    }


def build_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for policy_id in PRIMARY_POLICIES:
        for baseline_id in ["raw_fixed_embedding", "random_control", "quality_control"]:
            if policy_id == baseline_id:
                continue
            for metric in METRICS:
                rows.append(paired_contrast(frame, policy_id, baseline_id, metric))
    return pd.DataFrame(rows)


def write_statement(summary: pd.DataFrame, run_count: int) -> None:
    def delta(policy: str, baseline: str, metric: str) -> float:
        rows = summary[
            summary["policy_id"].eq(policy)
            & summary["baseline_id"].eq(baseline)
            & summary["metric"].eq(metric)
        ]
        return float(rows["mean_delta"].iloc[0]) if len(rows) else float("nan")

    lines = [
        "# Phase 13D RQ4 Confidence Statement",
        "",
        "Date: 2026-06-18",
        "",
        f"Summarized paired split/descriptor runs: {run_count}",
        "",
        "## Current Reading",
        "",
        "Phase 13D combines simulated loss-exposure analysis with fixed-embedding projection-head training. The evidence should be read as a controlled RQ4 sanity layer, not as final full metric-learning validation.",
        "",
        "## Key Paired Contrasts",
        "",
        f"- PF-ERI positive vs quality-control mean delta mAP: {delta('pf_eri_positive', 'quality_control', 'mAP_at_k'):.4f}",
        f"- PF-ERI conflict-aware vs quality-control mean delta mAP: {delta('pf_eri_conflict_aware', 'quality_control', 'mAP_at_k'):.4f}",
        f"- PF-ERI conflict-aware vs random-control mean delta mAP: {delta('pf_eri_conflict_aware', 'random_control', 'mAP_at_k'):.4f}",
        f"- PF-ERI conflict-aware vs raw fixed embedding mean delta mAP: {delta('pf_eri_conflict_aware', 'raw_fixed_embedding', 'mAP_at_k'):.4f}",
        "",
        "## Claim Boundary",
        "",
        "A strong RQ4 claim requires PF-ERI policies to beat quality-control and random-control across multiple split/descriptor runs without losing query coverage or increasing false-candidate burden. If projection-head training underperforms raw fixed embeddings, the result is a useful boundary condition: PF-ERI may still improve training-signal reliability, but the projection objective or regularization must be upgraded before claiming retrieval improvement.",
    ]
    CONFIDENCE_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="*", type=Path, default=[DEFAULT_INPUT])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = load_inputs(args.inputs)
    summary = build_summary(frame)
    summary.to_csv(CONTRASTS_OUT, index=False)
    write_statement(summary, frame["run_key"].nunique())
    print(f"Wrote Phase 13D RQ4 contrast summary to {CONTRASTS_OUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
