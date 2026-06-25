#!/usr/bin/env python3
"""Phase 15 calibrated ranker training script for Colab/Kaggle.

Upload or mount the Phase 15 routing input CSV, then run this script in
Colab/Kaggle. It trains a small tabular ranker with query-group holdout and
compares it against descriptor-only ranking. It does not require a GPU.

Expected input:
outputs/phase15/hybrid_routing_policy/phase15_czechlynx_candidate_routing_input.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

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
RANDOM_SEED = 20260622


def numeric_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame[columns].apply(pd.to_numeric, errors="coerce")
    return out.fillna(out.median(numeric_only=True)).fillna(0.0)


def evaluate_ranking(frame: pd.DataFrame, score_column: str, label: str) -> list[dict]:
    rows = []
    ranked = frame.copy()
    ranked["_rank"] = ranked.groupby("query_image_evidence_id")[score_column].rank(method="first", ascending=False)
    for k in SUMMARY_K:
        top = ranked[ranked["_rank"] <= k]
        per_query = top.groupby("query_image_evidence_id")["same_identity"].agg(
            retained_pairs="size",
            retained_positive=lambda s: int(s.eq("yes").sum()),
            retained_false=lambda s: int(s.eq("no").sum()),
        )
        all_queries = pd.DataFrame(index=ranked["query_image_evidence_id"].drop_duplicates())
        per_query = all_queries.join(per_query).fillna(0)
        hit = per_query["retained_positive"] > 0
        rows.append(
            {
                "policy_id": f"{label}_top_{k}",
                "k": k,
                "queries": int(len(per_query)),
                "hit_rate": float(hit.mean()),
                "mean_false_retained_per_query": float(per_query["retained_false"].mean()),
                "mean_positive_retained_per_query": float(per_query["retained_positive"].mean()),
                "false_rate_among_retained": float(top["same_identity"].eq("no").mean()) if len(top) else float("nan"),
            }
        )
    return rows


def train_and_evaluate(input_csv: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(input_csv, low_memory=False)
    data = data[data["same_identity"].isin(["yes", "no"])].copy()
    data["label"] = data["same_identity"].eq("yes").astype(int)

    missing = sorted(set(FEATURE_COLUMNS) - set(data.columns))
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=RANDOM_SEED)
    groups = data["query_image_evidence_id"].astype(str)
    train_idx, test_idx = next(splitter.split(data, data["label"], groups))
    train = data.iloc[train_idx].copy()
    test = data.iloc[test_idx].copy()

    x_train = numeric_frame(train, FEATURE_COLUMNS)
    y_train = train["label"].to_numpy()
    x_test = numeric_frame(test, FEATURE_COLUMNS)
    y_test = test["label"].to_numpy()

    models = {
        "logistic_calibrated_ranker": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_SEED),
        ),
        "hist_gradient_boosting_ranker": HistGradientBoostingClassifier(
            max_iter=200,
            learning_rate=0.05,
            l2_regularization=0.05,
            random_state=RANDOM_SEED,
        ),
    }

    eval_rows = []
    model_rows = []
    test = test.copy()
    test["descriptor_score"] = pd.to_numeric(test["descriptor_similarity"], errors="coerce").fillna(0.0)
    eval_rows.extend(evaluate_ranking(test, "descriptor_score", "descriptor_only"))

    for model_id, model in models.items():
        model.fit(x_train, y_train)
        if hasattr(model, "predict_proba"):
            score = model.predict_proba(x_test)[:, 1]
        else:
            score = model.decision_function(x_test)
        test[model_id] = score
        model_rows.append(
            {
                "model_id": model_id,
                "test_roc_auc": float(roc_auc_score(y_test, score)),
                "test_average_precision": float(average_precision_score(y_test, score)),
                "train_rows": int(len(train)),
                "test_rows": int(len(test)),
                "train_queries": int(train["query_image_evidence_id"].nunique()),
                "test_queries": int(test["query_image_evidence_id"].nunique()),
            }
        )
        eval_rows.extend(evaluate_ranking(test, model_id, model_id))

    eval_table = pd.DataFrame(eval_rows)
    model_table = pd.DataFrame(model_rows)
    eval_table.to_csv(output_dir / "phase15_colab_ranker_policy_eval.csv", index=False)
    model_table.to_csv(output_dir / "phase15_colab_ranker_model_eval.csv", index=False)
    test[
        [
            "query_image_evidence_id",
            "candidate_image_evidence_id",
            "same_identity",
            "descriptor_score",
            "logistic_calibrated_ranker",
            "hist_gradient_boosting_ranker",
        ]
    ].to_csv(output_dir / "phase15_colab_ranker_test_scores.csv", index=False)

    audit = {
        "status": "pass",
        "input_csv": str(input_csv),
        "output_dir": str(output_dir),
        "feature_columns": FEATURE_COLUMNS,
        "random_seed": RANDOM_SEED,
        "boundary": "CzechLynx known-ID held-out query split; no bobcat identity validation.",
        "model_eval": model_rows,
    }
    (output_dir / "phase15_colab_ranker_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True))
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to phase15_czechlynx_candidate_routing_input.csv",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("phase15_colab_ranker_outputs"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = train_and_evaluate(args.input, args.output_dir)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
