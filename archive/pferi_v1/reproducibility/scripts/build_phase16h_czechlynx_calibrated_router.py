#!/usr/bin/env python3
"""Validate Phase16H calibrated review-router candidates with grouped splits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "outputs/phase16/phase16h_czechlynx_readiness_controls/phase16h_czechlynx_scored_pair_table.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16h_czechlynx_calibrated_router"
FEATURE_COLUMNS = [
    "score_descriptor_only",
    "score_quality_only",
    "score_evidence_only",
    "score_conflict_penalized_descriptor",
    "score_phase16h_diagnostic",
    "descriptor_similarity",
    "weakest_iqa_score",
    "query_side_probability",
    "candidate_side_probability",
    "descriptor_margin",
]
K_VALUES = [1, 5, 10, 20]


def _bool_series(frame: pd.DataFrame, column: str, default: bool = False) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=bool)
    values = frame[column]
    if values.dtype == bool:
        return values.fillna(default)
    return values.astype(str).str.lower().isin({"true", "1", "yes"})


def _numeric_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame[columns].apply(pd.to_numeric, errors="coerce")
    return out.fillna(out.median(numeric_only=True)).fillna(0.0)


def build_model_frame(pair_table: pd.DataFrame, exclude_leakage: bool = True) -> pd.DataFrame:
    missing = [column for column in FEATURE_COLUMNS if column not in pair_table.columns]
    required = ["pair_id", "query_image_id", "split_group"]
    missing.extend(column for column in required if column not in pair_table.columns)
    if "phase16h_label" not in pair_table.columns and "same_identity_label" not in pair_table.columns:
        missing.append("phase16h_label_or_same_identity_label")
    if missing:
        raise ValueError("Phase16H calibrated input missing required columns: " + ", ".join(missing))

    out = pair_table.copy()
    if "phase16h_label" not in out.columns:
        out["phase16h_label"] = _bool_series(out, "same_identity_label")
    else:
        out["phase16h_label"] = _bool_series(out, "phase16h_label")
    out["source_leakage_pressure_flag"] = _bool_series(out, "source_leakage_pressure_flag")
    if exclude_leakage:
        out = out[~out["source_leakage_pressure_flag"]].copy()
    out = out[out["label_allowed_for_modeling"].fillna(True).astype(bool)].copy()
    if out["phase16h_label"].nunique() < 2:
        raise ValueError("Phase16H model frame requires both positive and false pairs")
    return out.reset_index(drop=True)


def grouped_shuffle_splits(
    frame: pd.DataFrame,
    repeats: int,
    test_size: float,
    random_seed: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    groups = np.array(sorted(frame["split_group"].astype(str).unique()))
    rng = np.random.default_rng(random_seed)
    splits: list[tuple[np.ndarray, np.ndarray]] = []
    test_group_count = max(1, int(round(len(groups) * test_size)))
    for _ in range(repeats):
        shuffled = groups.copy()
        rng.shuffle(shuffled)
        test_groups = set(shuffled[:test_group_count])
        is_test = frame["split_group"].astype(str).isin(test_groups).to_numpy()
        train_idx = np.where(~is_test)[0]
        test_idx = np.where(is_test)[0]
        if len(train_idx) and len(test_idx):
            splits.append((train_idx, test_idx))
    return splits


def standardize_train_test(train_x: pd.DataFrame, test_x: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    mean = train_x.mean(axis=0)
    std = train_x.std(axis=0).replace(0, 1.0)
    return ((train_x - mean) / std).to_numpy(), ((test_x - mean) / std).to_numpy()


def add_interactions(features: pd.DataFrame) -> pd.DataFrame:
    out = features.copy()
    out["descriptor_x_quality"] = out["score_descriptor_only"] * out["score_quality_only"]
    out["descriptor_x_evidence"] = out["score_descriptor_only"] * out["score_evidence_only"]
    out["quality_x_side"] = out["weakest_iqa_score"] * np.minimum(
        out["query_side_probability"],
        out["candidate_side_probability"],
    )
    return out


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -35, 35)))


def fit_logistic_scores(
    train_x: pd.DataFrame,
    train_y: pd.Series,
    test_x: pd.DataFrame,
    learning_rate: float = 0.05,
    steps: int = 500,
    l2: float = 0.01,
) -> np.ndarray:
    x_train, x_test = standardize_train_test(train_x, test_x)
    x_train = np.column_stack([np.ones(len(x_train)), x_train])
    x_test = np.column_stack([np.ones(len(x_test)), x_test])
    y = train_y.astype(float).to_numpy()
    pos_rate = max(float(y.mean()), 1e-6)
    neg_rate = max(1.0 - pos_rate, 1e-6)
    weights_per_row = np.where(y > 0, 0.5 / pos_rate, 0.5 / neg_rate)
    coef = np.zeros(x_train.shape[1], dtype=float)
    for _ in range(steps):
        pred = sigmoid(x_train @ coef)
        error = (pred - y) * weights_per_row
        grad = (x_train.T @ error) / len(x_train)
        grad[1:] += l2 * coef[1:]
        coef -= learning_rate * grad
    return sigmoid(x_test @ coef)


def roc_auc_score_np(y_true: pd.Series, score: np.ndarray) -> float:
    y = y_true.astype(bool).to_numpy()
    pos = score[y]
    neg = score[~y]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    comparisons = (pos[:, None] > neg[None, :]).mean()
    ties = (pos[:, None] == neg[None, :]).mean()
    return float(comparisons + 0.5 * ties)


def average_precision_np(y_true: pd.Series, score: np.ndarray) -> float:
    y = y_true.astype(bool).to_numpy()
    if y.sum() == 0:
        return float("nan")
    order = np.argsort(-score)
    ranked = y[order]
    cumulative_positive = np.cumsum(ranked)
    precision = cumulative_positive / (np.arange(len(ranked)) + 1)
    return float((precision * ranked).sum() / ranked.sum())


def evaluate_rank_scores(
    frame: pd.DataFrame,
    score_columns: dict[str, str],
    k_values: list[int],
    split_id: int,
    subset_name: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    all_queries = pd.DataFrame(index=frame["query_image_id"].drop_duplicates())
    for policy_id, score_column in score_columns.items():
        ranked = frame.copy()
        ranked["_policy_rank"] = ranked.groupby("query_image_id")[score_column].rank(method="first", ascending=False)
        for k in k_values:
            top = ranked[ranked["_policy_rank"] <= k]
            per_query = top.groupby("query_image_id")["phase16h_label"].agg(
                retained_pairs="size",
                retained_positive=lambda s: int(s.sum()),
                retained_false=lambda s: int((~s.astype(bool)).sum()),
            )
            per_query = all_queries.join(per_query).fillna(0)
            rows.append(
                {
                    "split_id": int(split_id),
                    "subset_name": subset_name,
                    "policy_id": policy_id,
                    "k": int(k),
                    "queries": int(len(per_query)),
                    "retained_pairs": int(len(top)),
                    "hit_rate": float((per_query["retained_positive"] > 0).mean()),
                    "mean_false_retained_per_query": float(per_query["retained_false"].mean()),
                    "mean_positive_retained_per_query": float(per_query["retained_positive"].mean()),
                    "false_rate_among_retained": float((~top["phase16h_label"].astype(bool)).mean()) if len(top) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _fit_and_score_split(train: pd.DataFrame, test: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    del seed
    x_train = _numeric_frame(train, FEATURE_COLUMNS)
    x_test = _numeric_frame(test, FEATURE_COLUMNS)
    y_train = train["phase16h_label"].astype(bool)
    y_test = test["phase16h_label"].astype(bool)
    scored = test.copy()
    model_rows: list[dict[str, object]] = []

    model_inputs = {
        "logistic_calibrated_router": (x_train, x_test),
        "interaction_logistic_router": (add_interactions(x_train), add_interactions(x_test)),
    }
    for model_id, (train_features, test_features) in model_inputs.items():
        score = fit_logistic_scores(train_features, y_train, test_features)
        scored[f"score_{model_id}"] = score
        model_rows.append(
            {
                "model_id": model_id,
                "roc_auc": roc_auc_score_np(y_test, score),
                "average_precision": average_precision_np(y_test, score),
                "train_rows": int(len(train)),
                "test_rows": int(len(test)),
                "train_positive_rate": float(y_train.mean()),
                "test_positive_rate": float(y_test.mean()),
            }
        )
    return scored, model_rows


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    group_cols = ["subset_name", "policy_id", "k"]
    value_cols = [
        "hit_rate",
        "mean_false_retained_per_query",
        "mean_positive_retained_per_query",
        "false_rate_among_retained",
    ]
    for keys, group in metrics.groupby(group_cols, dropna=False):
        row: dict[str, object] = {
            "subset_name": keys[0],
            "policy_id": keys[1],
            "k": int(keys[2]),
            "repeats": int(group["split_id"].nunique()),
            "mean_queries": float(group["queries"].mean()),
        }
        for column in value_cols:
            row[f"{column}_mean"] = float(group[column].mean())
            row[f"{column}_ci95_low"] = float(group[column].quantile(0.025))
            row[f"{column}_ci95_high"] = float(group[column].quantile(0.975))
        rows.append(row)
    return pd.DataFrame(rows)


def determine_claim_status(summary: pd.DataFrame) -> dict[str, object]:
    k10 = summary[summary["k"].eq(10)]
    descriptor = k10[k10["policy_id"].eq("descriptor_only")]
    if descriptor.empty:
        return {"claim_status": "NO_IMPROVEMENT_CLAIM", "claim_reason": "descriptor baseline missing"}
    descriptor_row = descriptor.iloc[0]
    candidates = k10[k10["policy_id"].isin(["logistic_calibrated_router", "interaction_logistic_router"])]
    best = None
    for row in candidates.to_dict(orient="records"):
        false_delta = (
            float(descriptor_row["mean_false_retained_per_query_mean"])
            - float(row["mean_false_retained_per_query_mean"])
        )
        hit_delta = float(row["hit_rate_mean"]) - float(descriptor_row["hit_rate_mean"])
        if best is None or false_delta > best["false_delta"]:
            best = {
                "policy_id": row["policy_id"],
                "false_delta": false_delta,
                "hit_delta": hit_delta,
            }
    if best and best["false_delta"] > 0.10 and best["hit_delta"] >= -0.01:
        return {
            "claim_status": "CANDIDATE_SIGNAL_ONLY",
            "claim_reason": (
                f"{best['policy_id']} reduces mean false retained/query by {best['false_delta']:.3f} "
                f"with hit-rate delta {best['hit_delta']:.3f} at k=10; requires sensitivity review."
            ),
        }
    return {
        "claim_status": "NO_IMPROVEMENT_CLAIM",
        "claim_reason": "No calibrated model cleared the conservative k=10 descriptor-only improvement gate.",
    }


def run_phase16h_calibrated_router(
    input_csv: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    repeats: int = 20,
    test_size: float = 0.30,
    random_seed: int = 20260628,
) -> dict[str, object]:
    raw = pd.read_csv(input_csv, low_memory=False)
    frame = build_model_frame(raw, exclude_leakage=True)
    split_metrics: list[pd.DataFrame] = []
    model_eval_rows: list[dict[str, object]] = []

    splits = grouped_shuffle_splits(frame, repeats=repeats, test_size=test_size, random_seed=random_seed)
    for split_id, (train_idx, test_idx) in enumerate(splits, start=1):
        train = frame.iloc[train_idx].copy()
        test = frame.iloc[test_idx].copy()
        scored, model_rows = _fit_and_score_split(train, test, seed=random_seed + split_id)
        for row in model_rows:
            row["split_id"] = split_id
            row["subset_name"] = "leakage_excluded"
        model_eval_rows.extend(model_rows)
        score_columns = {
            "descriptor_only": "score_descriptor_only",
            "quality_only": "score_quality_only",
            "phase16h_diagnostic_no_training": "score_phase16h_diagnostic",
            "logistic_calibrated_router": "score_logistic_calibrated_router",
            "interaction_logistic_router": "score_interaction_logistic_router",
        }
        split_metrics.append(
            evaluate_rank_scores(
                scored,
                score_columns=score_columns,
                k_values=K_VALUES,
                split_id=split_id,
                subset_name="leakage_excluded",
            )
        )

    metrics = pd.concat(split_metrics, ignore_index=True)
    summary = summarize_metrics(metrics)
    model_eval = pd.DataFrame(model_eval_rows)
    claim = determine_claim_status(summary)
    audit = {
        "status": "PASS",
        "claim_status": claim["claim_status"],
        "claim_reason": claim["claim_reason"],
        "input_rows": int(len(raw)),
        "training_scope_rows": int(len(frame)),
        "excluded_leakage_rows": int(len(raw) - len(frame)),
        "query_count": int(frame["query_image_id"].nunique()),
        "split_repeats": int(repeats),
        "test_size": float(test_size),
        "claim_boundary": "Grouped-split calibrated CzechLynx validation only; no Bobcat identity claim and no automatic identity assignment.",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(output_dir / "phase16h_calibrated_router_split_metrics.csv", index=False)
    summary.to_csv(output_dir / "phase16h_calibrated_router_summary.csv", index=False)
    model_eval.to_csv(output_dir / "phase16h_calibrated_router_model_eval.csv", index=False)
    (output_dir / "phase16h_calibrated_router_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n"
    )
    write_report(audit, summary, model_eval, output_dir)
    return audit


def write_report(audit: dict[str, object], summary: pd.DataFrame, model_eval: pd.DataFrame, output_dir: Path) -> None:
    k10 = summary[summary["k"].eq(10)].sort_values("mean_false_retained_per_query_mean")
    lines = [
        "# Phase16H CzechLynx Calibrated Router Validation",
        "",
        "This report evaluates grouped-split calibrated router candidates on leakage-excluded CzechLynx pairs.",
        "It is not automatic identity assignment and does not validate Bobcat identity accuracy.",
        "",
        "## Audit",
        "",
        f"- Status: {audit['status']}",
        f"- Claim status: {audit['claim_status']}",
        f"- Claim reason: {audit['claim_reason']}",
        f"- Training-scope rows: {audit['training_scope_rows']:,}",
        f"- Excluded leakage rows: {audit['excluded_leakage_rows']:,}",
        f"- Query count: {audit['query_count']:,}",
        "",
        "## k=10 Summary",
        "",
        "| policy | hit rate | mean false/query | false rate retained |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in k10.to_dict(orient="records"):
        lines.append(
            f"| {row['policy_id']} | {row['hit_rate_mean']:.4f} | "
            f"{row['mean_false_retained_per_query_mean']:.4f} | "
            f"{row['false_rate_among_retained_mean']:.4f} |"
        )
    if not model_eval.empty:
        eval_summary = model_eval.groupby("model_id")[["roc_auc", "average_precision"]].mean().reset_index()
        lines.extend(["", "## Model Discrimination", "", "| model | ROC-AUC | AP |", "| --- | ---: | ---: |"])
        for row in eval_summary.to_dict(orient="records"):
            lines.append(f"| {row['model_id']} | {row['roc_auc']:.4f} | {row['average_precision']:.4f} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Only use this output as CzechLynx grouped-split validation evidence. Do not claim a new descriptor, automatic identity assignment, or Bobcat identity accuracy.",
            "",
        ]
    )
    (output_dir / "phase16h_calibrated_router_report.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--test-size", type=float, default=0.30)
    parser.add_argument("--random-seed", type=int, default=20260628)
    args = parser.parse_args()

    audit = run_phase16h_calibrated_router(
        input_csv=args.input,
        output_dir=args.output_dir,
        repeats=args.repeats,
        test_size=args.test_size,
        random_seed=args.random_seed,
    )
    print(f"Status: {audit['status']}")
    print(f"Claim status: {audit['claim_status']}")
    print(f"Training-scope rows: {audit['training_scope_rows']}")
    print(f"Excluded leakage rows: {audit['excluded_leakage_rows']}")
    print(f"Wrote {args.output_dir}")
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
