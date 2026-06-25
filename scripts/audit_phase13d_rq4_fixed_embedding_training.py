#!/usr/bin/env python3
"""Audit Phase 13D RQ4 fixed-embedding training sanity outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/rq4_fixed_embedding_training"

EXPOSURE = OUT_DIR / "phase13d_rq4_loss_exposure_summary.csv"
TRAINING_METRICS = OUT_DIR / "phase13d_rq4_training_metrics.csv"
RETRIEVAL_METRICS = OUT_DIR / "phase13d_rq4_retrieval_metrics.csv"
PAIR_SAMPLE = OUT_DIR / "phase13d_rq4_training_pair_sample.csv"
SUMMARY_MD = OUT_DIR / "phase13d_rq4_fixed_embedding_training_summary.md"
BUILD_AUDIT = OUT_DIR / "phase13d_rq4_fixed_embedding_training_build_audit.json"
AUDIT_OUT = OUT_DIR / "phase13d_rq4_fixed_embedding_training_audit.csv"


def add(rows: list[dict[str, object]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def unit_interval(series: pd.Series) -> bool:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return bool(((values >= 0) & (values <= 1)).all())


def main() -> None:
    rows: list[dict[str, object]] = []
    for label, path in {
        "exposure": EXPOSURE,
        "training_metrics": TRAINING_METRICS,
        "retrieval_metrics": RETRIEVAL_METRICS,
        "pair_sample": PAIR_SAMPLE,
        "summary_md": SUMMARY_MD,
        "build_audit": BUILD_AUDIT,
    }.items():
        add(rows, f"{label}_exists", path.exists(), str(path))

    if EXPOSURE.exists():
        frame = pd.read_csv(EXPOSURE)
        add(rows, "exposure_nonempty", len(frame) > 0, f"rows={len(frame)}")
        required = {"descriptor_only", "random_control", "quality_control", "pf_eri_positive", "pf_eri_conflict_aware"}
        add(rows, "exposure_all_policies", required <= set(frame["policy_id"].astype(str)), f"policies={sorted(set(frame['policy_id'].astype(str)))}")
        add(rows, "unsafe_negative_fraction_unit_interval", unit_interval(frame["unsafe_negative_weight_fraction"]), "unsafe_negative_weight_fraction")
        conflict = frame[frame["policy_id"].eq("pf_eri_conflict_aware")]
        add(
            rows,
            "conflict_aware_unsafe_downweighted",
            bool((pd.to_numeric(conflict["mean_unsafe_hard_negative_weight"], errors="coerce") < 1.0).all()),
            "pf_eri_conflict_aware mean unsafe hard-negative weight < 1",
        )

    if TRAINING_METRICS.exists():
        frame = pd.read_csv(TRAINING_METRICS)
        add(rows, "training_metrics_nonempty", len(frame) > 0, f"rows={len(frame)}")
        add(rows, "training_loss_finite", bool(pd.to_numeric(frame["train_loss"], errors="coerce").notna().all()), "train_loss")
        add(rows, "training_pair_counts_present", {"train_pair_count", "train_positive_pair_count", "train_negative_pair_count"} <= set(frame.columns), "pair-level training columns")
        if {"train_positive_pair_count", "train_negative_pair_count"} <= set(frame.columns):
            add(
                rows,
                "training_has_positive_and_negative_pairs",
                bool((pd.to_numeric(frame["train_positive_pair_count"], errors="coerce") > 0).all() and (pd.to_numeric(frame["train_negative_pair_count"], errors="coerce") > 0).all()),
                "positive and negative pair counts > 0",
            )

    if RETRIEVAL_METRICS.exists():
        frame = pd.read_csv(RETRIEVAL_METRICS)
        add(rows, "retrieval_metrics_nonempty", len(frame) > 0, f"rows={len(frame)}")
        for col in ["mAP_at_k", "MRR_at_k", "top1_accuracy", "top5_accuracy", "false_top1_rate", "query_coverage"]:
            add(rows, f"{col}_unit_interval", unit_interval(frame[col]), col)
        add(rows, "retrieval_all_policies", len(set(frame["policy_id"].astype(str))) >= 5, f"policies={sorted(set(frame['policy_id'].astype(str)))}")
        add(rows, "retrieval_has_raw_baseline", "raw_fixed_embedding" in set(frame["policy_id"].astype(str)), "raw_fixed_embedding")
        delta_cols = [col for col in frame.columns if col.startswith("delta_vs_raw_")]
        add(rows, "retrieval_has_raw_delta_columns", len(delta_cols) >= 4, f"delta_cols={delta_cols}")

    if PAIR_SAMPLE.exists():
        frame = pd.read_csv(PAIR_SAMPLE)
        forbidden = {"query_identity_token", "candidate_identity_token", "working_individual_id", "expanded_image_id", "path", "local_image_path"}
        add(rows, "pair_sample_no_sensitive_columns", forbidden.isdisjoint(frame.columns), f"forbidden_present={sorted(forbidden & set(frame.columns))}")

    if BUILD_AUDIT.exists():
        try:
            audit = json.loads(BUILD_AUDIT.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            add(rows, "build_audit_valid_json", False, str(exc))
        else:
            add(rows, "build_audit_valid_json", True, "valid")
            add(rows, "build_audit_has_train_images", int(audit.get("train_image_count", 0)) > 0, f"train_images={audit.get('train_image_count')}")
            add(rows, "build_audit_has_retrieval_rows", int(audit.get("retrieval_metric_rows", 0)) >= 5, f"retrieval_rows={audit.get('retrieval_metric_rows')}")

    pd.DataFrame(rows).to_csv(AUDIT_OUT, index=False)
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)
    print(f"Phase 13D RQ4 fixed-embedding training audit: PASS={pass_count} FAIL={fail_count} output={AUDIT_OUT.relative_to(PROJECT_ROOT)}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
