#!/usr/bin/env python3
"""Train a Phase 10-Lite projection head from preselected matched manifests.

This script is intended for Colab execution after the Phase 10-Lite package is
uploaded. It does not select samples. It only filters the already-built matched
manifest by split, group, and k.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

REQUIRED_TRAINING_RULE = "use_preselected_phase10_lite_group"


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
        return {
            "x": torch.tensor(self.embeddings[image_id], dtype=torch.float32),
            "y": torch.tensor(self.label_map[str(row["identity_label_internal"])], dtype=torch.long),
            "w": torch.tensor(1.0, dtype=torch.float32),
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


def select_preselected_training_rows(manifest: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if config.get("training_rule") != REQUIRED_TRAINING_RULE:
        raise ValueError(
            f"Phase 10-Lite requires training_rule={REQUIRED_TRAINING_RULE}; "
            f"observed {config.get('training_rule')!r}"
        )
    required = {"split_id", "phase10_lite_group", "identity_label_internal", "image_id"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"manifest missing required columns: {sorted(missing)}")

    split_id = int(config["split_id"])
    phase10_group = str(config["phase10_lite_group"])
    selected = manifest[
        (manifest["split_id"].astype(int) == split_id)
        & (manifest["phase10_lite_group"].astype(str) == phase10_group)
    ].copy()
    if "images_per_identity_k" in selected.columns:
        selected = selected[
            pd.to_numeric(selected["images_per_identity_k"], errors="coerce")
            == int(config["images_per_identity_k"])
        ].copy()
    if "train_val_test_role" in selected.columns:
        roles = sorted(selected["train_val_test_role"].astype(str).str.lower().unique().tolist())
        if roles != ["train"]:
            raise ValueError(f"selected Phase 10-Lite rows must be train-only; observed roles={roles}")
    if selected.empty:
        raise ValueError("selected Phase 10-Lite training rows are empty")

    k = int(config["images_per_identity_k"])
    per_identity = selected.groupby("identity_label_internal")["image_id"].nunique()
    bad = per_identity[per_identity != k]
    if len(bad):
        raise ValueError(f"every identity must have exactly k={k} unique images; bad identities={len(bad)}")

    expected_identity_count = int(config.get("expected_identity_count", 75))
    observed_identity_count = int(selected["identity_label_internal"].nunique())
    if observed_identity_count != expected_identity_count:
        raise ValueError(
            f"expected {expected_identity_count} train identities, observed {observed_identity_count}"
        )

    duplicated = selected.duplicated(["identity_label_internal", "image_id"]).sum()
    if duplicated:
        raise ValueError(f"duplicate image rows within selected identity set: {duplicated}")

    selected["sample_weight"] = 1.0
    return selected


def verify_embedding_coverage(selected: pd.DataFrame, embeddings: dict[str, np.ndarray]) -> None:
    missing = sorted(set(selected["image_id"].astype(str)) - set(embeddings))
    if missing:
        preview = ", ".join(missing[:10])
        raise ValueError(f"embeddings missing for {len(missing)} selected image_id values: {preview}")


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


def train(config: dict[str, Any]) -> None:
    print("WARNING: Phase 10-Lite training is a controlled follow-up only, not a scientific claim.")
    out_dir = resolve_path(config, "output_dir")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(resolve_path(config, "manifest_path"))
    selected = select_preselected_training_rows(manifest, config)
    embeddings = load_embeddings(resolve_path(config, "embedding_path"))
    verify_embedding_coverage(selected, embeddings)

    label_map = {
        label: idx
        for idx, label in enumerate(sorted(selected["identity_label_internal"].astype(str).unique()))
    }
    dataset = EmbeddingDataset(selected, embeddings, label_map)
    if len(dataset) == 0:
        raise ValueError("empty training dataset after validation")

    generator = torch.Generator()
    generator.manual_seed(int(config.get("random_seed", 20260615)))
    loader = DataLoader(
        dataset,
        batch_size=min(int(config["model"].get("batch_size", 64)), len(dataset)),
        shuffle=True,
        drop_last=False,
        generator=generator,
    )

    model_cfg = config["model"]
    model = ProjectionHead(
        int(model_cfg["input_dim"]),
        int(model_cfg["hidden_dim"]),
        int(model_cfg["projection_dim"]),
    )
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
        rows.append(
            {
                "epoch": epoch,
                "train_loss": float(np.mean(losses)) if losses else np.nan,
                "experiment_group": config["experiment_group"],
                "phase10_lite_group": config["phase10_lite_group"],
                "split_id": int(config["split_id"]),
                "images_per_identity_k": int(config["images_per_identity_k"]),
                "selected_rows": int(len(selected)),
                "identity_count": int(selected["identity_label_internal"].nunique()),
            }
        )

    pd.DataFrame(rows).to_csv(out_dir / "phase10_lite_training_metrics.csv", index=False)
    torch.save({"model_state_dict": model.state_dict(), "config": config, "label_map": label_map}, out_dir / "projection_head.pt")
    selected.to_csv(out_dir / "training_manifest_used.csv", index=False)
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
