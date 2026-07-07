#!/usr/bin/env python3
"""Evaluate Phase 9D held-out retrieval from fixed or projected embeddings."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml


class ProjectionHead(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, projection_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, projection_dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.net(x), dim=1)


def parse_embedding_vector(value: str) -> np.ndarray:
    return np.asarray(ast.literal_eval(value), dtype=np.float32)


def load_embeddings(path: Path) -> dict[str, np.ndarray]:
    frame = pd.read_csv(path)
    return {str(row["expanded_image_id"]): parse_embedding_vector(row["embedding_vector"]) for _, row in frame.iterrows()}


def average_precision(relevance: np.ndarray) -> float:
    positives = int(relevance.sum())
    if positives == 0:
        return 0.0
    cumulative = np.cumsum(relevance)
    return float((cumulative[relevance == 1] / (np.flatnonzero(relevance == 1) + 1)).mean())


def project_embeddings(config: dict, embeddings: dict[str, np.ndarray], checkpoint: Path | None) -> dict[str, np.ndarray]:
    if checkpoint is None:
        return {k: v / max(np.linalg.norm(v), 1e-12) for k, v in embeddings.items()}
    payload = torch.load(checkpoint, map_location="cpu")
    model_cfg = payload["config"]["model"]
    model = ProjectionHead(int(model_cfg["input_dim"]), int(model_cfg["hidden_dim"]), int(model_cfg["projection_dim"]))
    model.load_state_dict(payload["model_state_dict"])
    model.eval()
    projected = {}
    with torch.no_grad():
        for image_id, vec in embeddings.items():
            z = model(torch.tensor(vec[None, :], dtype=torch.float32)).numpy()[0]
            projected[image_id] = z
    return projected


def evaluate(config: dict, checkpoint: Path | None) -> None:
    print("WARNING: Do not claim success from training loss. Only held-out retrieval metrics count.")
    out_dir = Path(config["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(config["manifest_path"])
    manifest = manifest[manifest["split_id"] == int(config["split_id"])].copy()
    embeddings = project_embeddings(config, load_embeddings(Path(config["embedding_path"])), checkpoint)
    test = manifest[(manifest["train_val_test_role"] == "test") & (manifest["image_id"].astype(str).isin(embeddings))].copy()
    top_k = int(config.get("evaluation", {}).get("top_k", 5))

    ap_values = []
    rr_values = []
    top1 = []
    top5 = []
    false_top1 = 0
    false_candidates = 0
    retained_candidates = 0
    rows = []
    for _, query in test.iterrows():
        qid = str(query["image_id"])
        qlabel = str(query["identity_label_internal"])
        gallery = test[test["image_id"].astype(str) != qid].copy()
        qvec = embeddings[qid]
        sims = []
        for _, cand in gallery.iterrows():
            gid = str(cand["image_id"])
            sim = float(np.dot(qvec, embeddings[gid]))
            same = str(cand["identity_label_internal"]) == qlabel
            sims.append((gid, sim, same))
        sims.sort(key=lambda item: item[1], reverse=True)
        top = sims[:top_k]
        rel = np.asarray([int(x[2]) for x in top], dtype=int)
        ap_values.append(average_precision(rel))
        pos = np.flatnonzero(rel == 1)
        rr_values.append(1.0 / (int(pos[0]) + 1) if len(pos) else 0.0)
        top1.append(int(len(rel) > 0 and rel[0] == 1))
        top5.append(int(len(rel) > 0 and rel.max() == 1))
        false_top1 += int(len(rel) > 0 and rel[0] == 0)
        false_candidates += int((rel == 0).sum())
        retained_candidates += len(rel)
        rows.extend({"query_image_id": qid, "gallery_image_id": gid, "similarity": sim, "same_identity": same, "rank": rank} for rank, (gid, sim, same) in enumerate(top, start=1))

    metric_row = {
        "experiment_group": config["experiment_group"],
        "mAP": float(np.mean(ap_values)),
        "MRR": float(np.mean(rr_values)),
        "top1_accuracy": float(np.mean(top1)),
        "top5_accuracy": float(np.mean(top5)),
        "false_top1_rate": false_top1 / max(len(test), 1),
        "false_candidate_burden": false_candidates / max(len(test), 1),
        "query_coverage": 1.0 if len(test) else 0.0,
        "positive_retention": float(np.mean(top5)) if top5 else 0.0,
        "candidate_retention": retained_candidates / max(len(test) * top_k, 1),
    }
    pd.DataFrame([metric_row]).to_csv(out_dir / "phase9d_colab_retrieval_metrics.csv", index=False)
    pd.DataFrame(rows).to_csv(out_dir / "phase9d_colab_failure_cases.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", default="")
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    evaluate(config, Path(args.checkpoint) if args.checkpoint else None)


if __name__ == "__main__":
    main()
