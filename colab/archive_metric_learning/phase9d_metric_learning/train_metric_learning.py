#!/usr/bin/env python3
"""Colab template for Phase 9D fixed-embedding metric-head training.

This script is intended to run in Colab only after the Phase 9D prep package
and required data files have been uploaded. It is not run during local prep.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm


class EmbeddingDataset(Dataset):
    def __init__(self, frame: pd.DataFrame, embeddings: dict[str, np.ndarray], label_map: dict[str, int]) -> None:
        self.frame = frame.reset_index(drop=True)
        self.embeddings = embeddings
        self.label_map = label_map

    def __len__(self) -> int:
        return len(self.frame)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        row = self.frame.iloc[idx]
        image_id = str(row["image_id"])
        weight = float(row.get("sample_weight", 1.0))
        return {
            "x": torch.tensor(self.embeddings[image_id], dtype=torch.float32),
            "y": torch.tensor(self.label_map[str(row["identity_label_internal"])], dtype=torch.long),
            "w": torch.tensor(weight, dtype=torch.float32),
        }


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


def parse_embedding_vector(value: str) -> np.ndarray:
    return np.asarray(ast.literal_eval(value), dtype=np.float32)


def load_embeddings(path: Path) -> dict[str, np.ndarray]:
    frame = pd.read_csv(path)
    return {str(row["expanded_image_id"]): parse_embedding_vector(row["embedding_vector"]) for _, row in frame.iterrows()}


def select_training_rows(manifest: pd.DataFrame, config: dict) -> pd.DataFrame:
    split_id = int(config["split_id"])
    train = manifest[(manifest["split_id"] == split_id) & (manifest["train_val_test_role"] == "train")].copy()
    rule = config["training_rule"]
    if rule == "all_train_role_images":
        selected = train
    elif rule == "pf_eri_score_threshold":
        threshold = float(config.get("selection", {}).get("pf_eri_min_score", 0.55))
        selected = train[train["pf_eri_image_score"] >= threshold].copy()
    elif rule == "random_same_size_as_pf_eri_selected":
        threshold = 0.55
        target_n = int((train["pf_eri_image_score"] >= threshold).sum())
        selected = train.sample(n=target_n, random_state=int(config.get("random_seed", 20260615))).copy()
    elif rule == "highest_quality_same_size_as_pf_eri_selected":
        threshold = 0.55
        target_n = int((train["pf_eri_image_score"] >= threshold).sum())
        selected = train.sort_values(["pf_eri_image_score", "visual_penalty"], ascending=[False, True]).head(target_n).copy()
    else:
        raise ValueError(f"Unknown training_rule: {rule}")

    if config.get("sample_weight_mode") == "pf_eri_weight":
        selected["sample_weight"] = 0.25 + 0.75 * selected["pf_eri_image_score"].astype(float)
    else:
        selected["sample_weight"] = 1.0
    return selected


def supervised_contrastive_loss(z: torch.Tensor, y: torch.Tensor, weights: torch.Tensor, temperature: float) -> torch.Tensor:
    sim = torch.matmul(z, z.T) / temperature
    eye = torch.eye(len(z), device=z.device, dtype=torch.bool)
    same = y[:, None].eq(y[None, :]) & ~eye
    logits = sim - sim.max(dim=1, keepdim=True).values.detach()
    exp_logits = torch.exp(logits) * (~eye)
    log_prob = logits - torch.log(exp_logits.sum(dim=1, keepdim=True).clamp_min(1e-12))
    positive_count = same.sum(dim=1).clamp_min(1)
    per_sample = -(log_prob * same).sum(dim=1) / positive_count
    has_positive = same.any(dim=1).float()
    weighted = per_sample * weights * has_positive
    return weighted.sum() / (weights * has_positive).sum().clamp_min(1.0)


def train(config: dict) -> None:
    print("WARNING: Do not claim success from training loss. Only held-out retrieval metrics count.")
    out_dir = Path(config["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(config["manifest_path"])
    embeddings = load_embeddings(Path(config["embedding_path"]))
    selected = select_training_rows(manifest, config)
    selected = selected[selected["image_id"].astype(str).isin(embeddings)].copy()
    label_map = {label: idx for idx, label in enumerate(sorted(selected["identity_label_internal"].astype(str).unique()))}
    dataset = EmbeddingDataset(selected, embeddings, label_map)
    loader = DataLoader(dataset, batch_size=min(64, len(dataset)), shuffle=True, drop_last=False)

    model_cfg = config["model"]
    model = ProjectionHead(int(model_cfg["input_dim"]), int(model_cfg["hidden_dim"]), int(model_cfg["projection_dim"]))
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(model_cfg["learning_rate"]))
    temperature = float(config["loss"].get("temperature", 0.07))

    rows = []
    for epoch in range(1, int(model_cfg["epochs"]) + 1):
        losses = []
        model.train()
        for batch in tqdm(loader, desc=f"epoch {epoch}", leave=False):
            optimizer.zero_grad()
            z = model(batch["x"])
            loss = supervised_contrastive_loss(z, batch["y"], batch["w"], temperature)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        rows.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "experiment_group": config["experiment_group"]})

    pd.DataFrame(rows).to_csv(out_dir / "phase9d_colab_training_metrics.csv", index=False)
    torch.save({"model_state_dict": model.state_dict(), "config": config, "label_map": label_map}, out_dir / "projection_head.pt")
    (out_dir / "training_manifest_used.csv").write_text(selected.to_csv(index=False), encoding="utf-8")
    (out_dir / "config_used.json").write_text(json.dumps(config, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    train(config)


if __name__ == "__main__":
    main()
