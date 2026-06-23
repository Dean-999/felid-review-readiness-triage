#!/usr/bin/env python3
"""Evaluate held-out retrieval for Phase 10-Lite projection-head runs."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml


class ProjectionHead(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, projection_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, projection_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.net(x), dim=1)


def resolve_path(config: dict[str, Any], key: str) -> Path:
    path = Path(str(config[key]))
    if path.is_absolute():
        return path
    return Path(str(config.get("project_root", "."))) / path


def parse_embedding_vector(value: object) -> np.ndarray:
    if isinstance(value, str):
        return np.asarray(ast.literal_eval(value), dtype=np.float32)
    if isinstance(value, (list, tuple, np.ndarray)):
        return np.asarray(value, dtype=np.float32)
    raise ValueError(f"unsupported embedding vector value type: {type(value)!r}")


def load_embeddings(path: Path) -> dict[str, np.ndarray]:
    frame = pd.read_csv(path)
    if "expanded_image_id" not in frame.columns or "embedding_vector" not in frame.columns:
        raise ValueError(f"{path} must contain expanded_image_id and embedding_vector columns")
    return {
        str(row["expanded_image_id"]): parse_embedding_vector(row["embedding_vector"])
        for _, row in frame.iterrows()
    }


def project_embeddings(checkpoint: Path, embeddings: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    payload = torch.load(checkpoint, map_location="cpu")
    model_cfg = payload["config"]["model"]
    model = ProjectionHead(
        int(model_cfg["input_dim"]),
        int(model_cfg["hidden_dim"]),
        int(model_cfg["projection_dim"]),
    )
    model.load_state_dict(payload["model_state_dict"])
    model.eval()
    projected = {}
    with torch.no_grad():
        for image_id, vec in embeddings.items():
            z = model(torch.tensor(vec[None, :], dtype=torch.float32)).numpy()[0]
            projected[image_id] = z / max(float(np.linalg.norm(z)), 1e-12)
    return projected


def average_precision(relevance: np.ndarray) -> float:
    positives = int(relevance.sum())
    if positives == 0:
        return 0.0
    cumulative = np.cumsum(relevance)
    return float((cumulative[relevance == 1] / (np.flatnonzero(relevance == 1) + 1)).mean())


def evaluate(config: dict[str, Any], checkpoint: Path) -> None:
    print("WARNING: Held-out retrieval metrics from this package are pilot evidence only.")
    out_dir = resolve_path(config, "output_dir")
    out_dir.mkdir(parents=True, exist_ok=True)

    train_manifest = pd.read_csv(resolve_path(config, "manifest_path"))
    eval_manifest_path = config.get("evaluation_manifest_path") or config.get("source_manifest_path")
    if not eval_manifest_path:
        raise ValueError("config must include evaluation_manifest_path for held-out test-role evaluation")
    eval_manifest = pd.read_csv(resolve_path(config, "evaluation_manifest_path"))

    split_id = int(config["split_id"])
    train_rows = train_manifest[
        (train_manifest["split_id"].astype(int) == split_id)
        & (train_manifest["phase10_lite_group"].astype(str) == str(config["phase10_lite_group"]))
    ].copy()
    if "images_per_identity_k" in train_rows.columns:
        train_rows = train_rows[
            pd.to_numeric(train_rows["images_per_identity_k"], errors="coerce")
            == int(config["images_per_identity_k"])
        ].copy()
    if train_rows.empty:
        raise ValueError("0 selected train rows found for this split/group/k")

    split_eval = eval_manifest[eval_manifest["split_id"].astype(int) == split_id].copy()
    if "train_val_test_role" not in split_eval.columns:
        raise ValueError("evaluation manifest must include train_val_test_role")
    test = split_eval[split_eval["train_val_test_role"].astype(str).str.lower() == "test"].copy()
    train_identities = set(train_rows["identity_label_internal"].astype(str))
    test_identities = set(test["identity_label_internal"].astype(str))
    overlap = train_identities & test_identities
    if overlap:
        raise ValueError(f"train identities appear in test role: {len(overlap)} overlapping identities")

    embeddings = project_embeddings(checkpoint, load_embeddings(resolve_path(config, "embedding_path")))
    test = test[test["image_id"].astype(str).isin(embeddings)].copy()
    if test.empty:
        raise ValueError("0 valid held-out test queries with embeddings")

    top_k = int(config.get("evaluation", {}).get("top_k", 5))
    ap_values: list[float] = []
    rr_values: list[float] = []
    top1_values: list[int] = []
    top5_values: list[int] = []
    false_top1 = 0
    false_candidates = 0
    retained_candidates = 0
    case_rows: list[dict[str, object]] = []

    for _, query in test.iterrows():
        qid = str(query["image_id"])
        qlabel = str(query["identity_label_internal"])
        gallery = test[test["image_id"].astype(str) != qid].copy()
        if gallery.empty:
            continue
        qvec = embeddings[qid]
        sims = []
        for _, candidate in gallery.iterrows():
            gid = str(candidate["image_id"])
            sim = float(np.dot(qvec, embeddings[gid]))
            same = str(candidate["identity_label_internal"]) == qlabel
            sims.append((gid, sim, same))
        sims.sort(key=lambda item: item[1], reverse=True)
        top = sims[:top_k]
        relevance = np.asarray([int(item[2]) for item in top], dtype=int)
        ap_values.append(average_precision(relevance))
        pos = np.flatnonzero(relevance == 1)
        rr_values.append(1.0 / (int(pos[0]) + 1) if len(pos) else 0.0)
        top1_values.append(int(len(relevance) > 0 and relevance[0] == 1))
        top5_values.append(int(len(relevance) > 0 and relevance.max() == 1))
        false_top1 += int(len(relevance) > 0 and relevance[0] == 0)
        false_candidates += int((relevance == 0).sum())
        retained_candidates += len(relevance)
        for rank, (gid, sim, same) in enumerate(top, start=1):
            case_rows.append(
                {
                    "query_image_id": qid,
                    "gallery_image_id": gid,
                    "rank": rank,
                    "similarity": sim,
                    "same_identity": bool(same),
                    "experiment_group": config["experiment_group"],
                    "split_id": split_id,
                }
            )

    if not ap_values:
        raise ValueError("0 valid held-out queries after gallery construction")

    metrics = {
        "experiment_group": config["experiment_group"],
        "phase10_lite_group": config["phase10_lite_group"],
        "split_id": split_id,
        "images_per_identity_k": int(config["images_per_identity_k"]),
        "mAP": float(np.mean(ap_values)),
        "MRR": float(np.mean(rr_values)),
        "top1_accuracy": float(np.mean(top1_values)),
        "top5_accuracy": float(np.mean(top5_values)),
        "false_top1_rate": false_top1 / max(len(ap_values), 1),
        "false_candidate_burden": false_candidates / max(len(ap_values), 1),
        "query_coverage": len(ap_values) / max(len(test), 1),
        "candidate_retention": retained_candidates / max(len(ap_values) * top_k, 1),
        "valid_query_count": int(len(ap_values)),
        "test_image_count": int(len(test)),
    }
    pd.DataFrame([metrics]).to_csv(out_dir / "phase10_lite_retrieval_metrics.csv", index=False)
    pd.DataFrame(case_rows).to_csv(out_dir / "phase10_lite_failure_cases.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    evaluate(config, Path(args.checkpoint))


if __name__ == "__main__":
    main()
