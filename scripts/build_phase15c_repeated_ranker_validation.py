#!/usr/bin/env python3
"""Repeated query-split validation for Phase 15 calibrated rankers.

This script validates whether PF-ERI/quality/conflict features provide stable
query-level retrieval improvements beyond descriptor-only ranking. It uses
grouped query splits and reports repeated-split means, confidence intervals,
subgroup behavior, risk-coverage curves, and simple permutation importance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "outputs/phase15/hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv"
OUT_DIR = PROJECT_ROOT / "outputs/phase15/repeated_ranker_validation"
REPEATED_METRICS = OUT_DIR / "phase15c_repeated_split_topk_metrics.csv"
SUMMARY_METRICS = OUT_DIR / "phase15c_repeated_split_summary.csv"
RISK_COVERAGE = OUT_DIR / "phase15c_risk_coverage_curve.csv"
PERMUTATION_IMPORTANCE = OUT_DIR / "phase15c_permutation_importance.csv"
AUDIT_JSON = OUT_DIR / "phase15c_repeated_ranker_validation_audit.json"
REPORT_MD = OUT_DIR / "phase15c_repeated_ranker_validation_report.md"

FEATURE_COLUMNS = [
    "descriptor_similarity",
    "descriptor_rank_support_score",
    "pair_comparability_score",
    "weakest_image_utility_score",
    "mean_image_utility_score",
    "pattern_pair_score",
    "side_comparability_score",
    "body_visibility_pair_score",
    "blur_pair_score",
    "occlusion_pair_score",
    "detector_geometry_pair_score",
    "edge_touch_pair_penalty",
    "descriptor_evidence_conflict_score",
    "descriptor_evidence_support_score",
]
SUMMARY_K = [1, 5, 10, 20, 50]
RISK_COVERAGE_LEVELS = [0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00]
DEFAULT_REPEATS = 20
DEFAULT_TEST_SIZE = 0.30
DEFAULT_SEED = 20260622


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def numeric_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame[columns].apply(pd.to_numeric, errors="coerce")
    return out.fillna(out.median(numeric_only=True)).fillna(0.0)


def ci_low(series: pd.Series) -> float:
    return float(series.quantile(0.025))


def ci_high(series: pd.Series) -> float:
    return float(series.quantile(0.975))


def add_query_subgroups(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    query_axis = (
        out[["query_image_evidence_id", "query_evidence_axis"]]
        .drop_duplicates("query_image_evidence_id")
        .set_index("query_image_evidence_id")["query_evidence_axis"]
    )
    out["query_group"] = out["query_image_evidence_id"].map(query_axis).fillna("unknown")
    out["candidate_relation_group"] = np.where(
        out["pair_evidence_axis_relation"].eq("mixed_axis"),
        "mixed_evidence_candidates",
        "same_evidence_candidates",
    )
    out["conflict_group"] = np.where(
        pd.to_numeric(out["descriptor_evidence_conflict_score"], errors="coerce") >= 0.50,
        "high_conflict_candidates",
        "low_conflict_candidates",
    )
    return out


def evaluate_topk(
    frame: pd.DataFrame,
    score_column: str,
    policy_id: str,
    split_id: int,
    subgroup_name: str,
) -> list[dict[str, Any]]:
    rows = []
    ranked = frame.copy()
    ranked["_rank"] = ranked.groupby("query_image_evidence_id")[score_column].rank(method="first", ascending=False)
    all_queries = pd.DataFrame(index=ranked["query_image_evidence_id"].drop_duplicates())
    for k in SUMMARY_K:
        top = ranked[ranked["_rank"] <= k]
        per_query = top.groupby("query_image_evidence_id")["same_identity"].agg(
            retained_pairs="size",
            retained_positive=lambda s: int(s.eq("yes").sum()),
            retained_false=lambda s: int(s.eq("no").sum()),
        )
        per_query = all_queries.join(per_query).fillna(0)
        hit = per_query["retained_positive"] > 0
        rows.append(
            {
                "split_id": split_id,
                "subgroup": subgroup_name,
                "policy_id": policy_id,
                "k": k,
                "queries": int(len(per_query)),
                "hit_rate": float(hit.mean()),
                "mean_false_retained_per_query": float(per_query["retained_false"].mean()),
                "mean_positive_retained_per_query": float(per_query["retained_positive"].mean()),
                "false_rate_among_retained": float(top["same_identity"].eq("no").mean()) if len(top) else float("nan"),
            }
        )
    return rows


def evaluate_risk_coverage(
    frame: pd.DataFrame,
    score_column: str,
    policy_id: str,
    split_id: int,
) -> list[dict[str, Any]]:
    rows = []
    all_queries = pd.DataFrame(index=frame["query_image_evidence_id"].drop_duplicates())
    for coverage in RISK_COVERAGE_LEVELS:
        threshold = frame[score_column].quantile(1.0 - coverage)
        retained = frame[frame[score_column] >= threshold]
        per_query = retained.groupby("query_image_evidence_id")["same_identity"].agg(
            retained_pairs="size",
            retained_positive=lambda s: int(s.eq("yes").sum()),
            retained_false=lambda s: int(s.eq("no").sum()),
        )
        per_query = all_queries.join(per_query).fillna(0)
        hit = per_query["retained_positive"] > 0
        rows.append(
            {
                "split_id": split_id,
                "policy_id": policy_id,
                "target_pair_coverage": coverage,
                "actual_pair_coverage": float(len(retained) / max(len(frame), 1)),
                "query_coverage": float((per_query["retained_pairs"] > 0).mean()),
                "hit_rate": float(hit.mean()),
                "mean_false_retained_per_query": float(per_query["retained_false"].mean()),
                "mean_positive_retained_per_query": float(per_query["retained_positive"].mean()),
                "score_threshold": float(threshold),
            }
        )
    return rows


def make_models(seed: int) -> dict[str, Any]:
    return {
        "descriptor_only": None,
        "logistic_calibrated_ranker": make_pipeline(
            StandardScaler(),
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=seed,
                solver="liblinear",
            ),
        ),
        "hist_gradient_boosting_ranker": HistGradientBoostingClassifier(
            max_iter=160,
            learning_rate=0.05,
            l2_regularization=0.05,
            random_state=seed,
        ),
    }


def summarize_repeats(metrics: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["subgroup", "policy_id", "k"]
    value_cols = [
        "hit_rate",
        "mean_false_retained_per_query",
        "mean_positive_retained_per_query",
        "false_rate_among_retained",
    ]
    rows = []
    for keys, frame in metrics.groupby(group_cols, dropna=False):
        row: dict[str, Any] = {
            "subgroup": keys[0],
            "policy_id": keys[1],
            "k": int(keys[2]),
            "repeats": int(frame["split_id"].nunique()),
            "mean_queries": float(frame["queries"].mean()),
        }
        for column in value_cols:
            row[f"{column}_mean"] = float(frame[column].mean())
            row[f"{column}_ci95_low"] = ci_low(frame[column])
            row[f"{column}_ci95_high"] = ci_high(frame[column])
        rows.append(row)
    return pd.DataFrame(rows)


def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    data = pd.read_csv(args.input, low_memory=False)
    missing = sorted(set(FEATURE_COLUMNS) - set(data.columns))
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    data = data[data["same_identity"].isin(["yes", "no"])].copy()
    data = add_query_subgroups(data)
    data["label"] = data["same_identity"].eq("yes").astype(int)
    data["descriptor_only"] = pd.to_numeric(data["descriptor_similarity"], errors="coerce").fillna(0.0)

    splitter = GroupShuffleSplit(n_splits=args.repeats, test_size=args.test_size, random_state=args.seed)
    groups = data["query_image_evidence_id"].astype(str)
    metric_rows: list[dict[str, Any]] = []
    risk_rows: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []
    first_hgb_model = None
    first_hgb_test_x = None
    first_hgb_test_y = None

    for split_id, (train_idx, test_idx) in enumerate(splitter.split(data, data["label"], groups), start=1):
        train = data.iloc[train_idx].copy()
        test = data.iloc[test_idx].copy()
        x_train = numeric_frame(train, FEATURE_COLUMNS)
        y_train = train["label"].to_numpy()
        x_test = numeric_frame(test, FEATURE_COLUMNS)
        y_test = test["label"].to_numpy()

        models = make_models(args.seed + split_id)
        for model_id, model in models.items():
            if model is None:
                test[model_id] = test["descriptor_only"]
                auc = roc_auc_score(y_test, test[model_id])
                ap = average_precision_score(y_test, test[model_id])
            else:
                model.fit(x_train, y_train)
                score = model.predict_proba(x_test)[:, 1]
                test[model_id] = score
                auc = roc_auc_score(y_test, score)
                ap = average_precision_score(y_test, score)
                if model_id == "hist_gradient_boosting_ranker" and first_hgb_model is None:
                    first_hgb_model = model
                    first_hgb_test_x = x_test.copy()
                    first_hgb_test_y = y_test.copy()
            model_rows.append(
                {
                    "split_id": split_id,
                    "model_id": model_id,
                    "test_roc_auc": float(auc),
                    "test_average_precision": float(ap),
                    "train_rows": int(len(train)),
                    "test_rows": int(len(test)),
                    "train_queries": int(train["query_image_evidence_id"].nunique()),
                    "test_queries": int(test["query_image_evidence_id"].nunique()),
                }
            )

            subgroup_frames = [("all", test)]
            for query_group, part in test.groupby("query_group", sort=True):
                subgroup_frames.append((f"query_{query_group}", part))
            for relation_group, part in test.groupby("candidate_relation_group", sort=True):
                subgroup_frames.append((relation_group, part))
            for conflict_group, part in test.groupby("conflict_group", sort=True):
                subgroup_frames.append((conflict_group, part))

            for subgroup_name, subgroup_frame in subgroup_frames:
                metric_rows.extend(evaluate_topk(subgroup_frame, model_id, model_id, split_id, subgroup_name))
            risk_rows.extend(evaluate_risk_coverage(test, model_id, model_id, split_id))

    metrics = pd.DataFrame(metric_rows)
    summary = summarize_repeats(metrics)
    risk = pd.DataFrame(risk_rows)
    model_eval = pd.DataFrame(model_rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(REPEATED_METRICS, index=False)
    summary.to_csv(SUMMARY_METRICS, index=False)
    risk.to_csv(RISK_COVERAGE, index=False)
    model_eval.to_csv(args.output_dir / "phase15c_repeated_model_eval.csv", index=False)

    importance_rows = []
    if first_hgb_model is not None and first_hgb_test_x is not None and first_hgb_test_y is not None:
        sample_n = min(args.importance_sample, len(first_hgb_test_x))
        sample_positions = np.random.default_rng(args.seed).choice(len(first_hgb_test_x), size=sample_n, replace=False)
        sample_x = first_hgb_test_x.iloc[sample_positions]
        sample_y = first_hgb_test_y[sample_positions]
        result = permutation_importance(
            first_hgb_model,
            sample_x,
            sample_y,
            scoring="average_precision",
            n_repeats=args.importance_repeats,
            random_state=args.seed,
        )
        for column, mean, std in zip(FEATURE_COLUMNS, result.importances_mean, result.importances_std):
            importance_rows.append(
                {
                    "model_id": "hist_gradient_boosting_ranker",
                    "feature": column,
                    "importance_mean_average_precision_drop": float(mean),
                    "importance_std": float(std),
                    "importance_sample_rows": int(sample_n),
                    "importance_repeats": int(args.importance_repeats),
                }
            )
    importance = pd.DataFrame(importance_rows).sort_values(
        "importance_mean_average_precision_drop", ascending=False
    )
    importance.to_csv(PERMUTATION_IMPORTANCE, index=False)

    audit = {
        "status": "pass",
        "script": rel(Path(__file__)),
        "input": rel(args.input),
        "output_dir": rel(args.output_dir),
        "repeats": int(args.repeats),
        "test_size": float(args.test_size),
        "seed": int(args.seed),
        "rows": int(len(data)),
        "queries": int(data["query_image_evidence_id"].nunique()),
        "feature_columns": FEATURE_COLUMNS,
        "outputs": {
            "repeated_metrics": rel(REPEATED_METRICS),
            "summary_metrics": rel(SUMMARY_METRICS),
            "risk_coverage": rel(RISK_COVERAGE),
            "permutation_importance": rel(PERMUTATION_IMPORTANCE),
        },
        "claim_boundary": "CzechLynx known-ID repeated query-split validation only; no bobcat identity validation.",
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    write_report(summary, risk, model_eval, importance, audit)
    return audit


def metric(summary: pd.DataFrame, policy: str, k: int, column: str, subgroup: str = "all") -> str:
    row = summary[
        summary["subgroup"].eq(subgroup) & summary["policy_id"].eq(policy) & summary["k"].eq(k)
    ]
    if row.empty:
        return "NA"
    value = row.iloc[0][f"{column}_mean"]
    low = row.iloc[0][f"{column}_ci95_low"]
    high = row.iloc[0][f"{column}_ci95_high"]
    return f"{value:.3f} [{low:.3f}, {high:.3f}]"


def write_report(
    summary: pd.DataFrame,
    risk: pd.DataFrame,
    model_eval: pd.DataFrame,
    importance: pd.DataFrame,
    audit: dict[str, Any],
) -> None:
    model_summary = model_eval.groupby("model_id").agg(
        test_roc_auc_mean=("test_roc_auc", "mean"),
        test_roc_auc_ci95_low=("test_roc_auc", ci_low),
        test_roc_auc_ci95_high=("test_roc_auc", ci_high),
        test_average_precision_mean=("test_average_precision", "mean"),
        test_average_precision_ci95_low=("test_average_precision", ci_low),
        test_average_precision_ci95_high=("test_average_precision", ci_high),
    )
    lines = [
        "# Phase 15C Repeated Ranker Validation",
        "",
        "This report validates calibrated PF-ERI/quality rankers with repeated held-out query splits.",
        "",
        "## Audit",
        "",
        f"- Repeats: {audit['repeats']}",
        f"- Rows: {audit['rows']}",
        f"- Queries: {audit['queries']}",
        "",
        "## Model-Level Metrics",
        "",
        "| Model | ROC-AUC mean [95% interval] | AP mean [95% interval] |",
        "|---|---:|---:|",
    ]
    for model_id, row in model_summary.iterrows():
        lines.append(
            f"| {model_id} | {row['test_roc_auc_mean']:.3f} "
            f"[{row['test_roc_auc_ci95_low']:.3f}, {row['test_roc_auc_ci95_high']:.3f}] | "
            f"{row['test_average_precision_mean']:.3f} "
            f"[{row['test_average_precision_ci95_low']:.3f}, {row['test_average_precision_ci95_high']:.3f}] |"
        )
    lines.extend(
        [
            "",
            "## Top-k Queue Metrics",
            "",
            "| Policy | hit@5 | hit@10 | hit@20 | false/query@10 | false/query@20 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for policy in ["descriptor_only", "logistic_calibrated_ranker", "hist_gradient_boosting_ranker"]:
        lines.append(
            f"| {policy} | {metric(summary, policy, 5, 'hit_rate')} | "
            f"{metric(summary, policy, 10, 'hit_rate')} | "
            f"{metric(summary, policy, 20, 'hit_rate')} | "
            f"{metric(summary, policy, 10, 'mean_false_retained_per_query')} | "
            f"{metric(summary, policy, 20, 'mean_false_retained_per_query')} |"
        )
    lines.extend(
        [
            "",
            "## Top Feature Contributions",
            "",
        ]
    )
    if importance.empty:
        lines.append("Permutation importance was not computed.")
    else:
        lines.append("| Feature | AP drop mean |")
        lines.append("|---|---:|")
        for _, row in importance.head(10).iterrows():
            lines.append(
                f"| {row['feature']} | {row['importance_mean_average_precision_drop']:.4f} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This is CzechLynx known-ID repeated query-split validation. It can support claims about CzechLynx candidate reranking and review burden only. It does not validate urban bobcat identity accuracy.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--test-size", type=float, default=DEFAULT_TEST_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--importance-sample", type=int, default=30000)
    parser.add_argument("--importance-repeats", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = run_validation(args)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
