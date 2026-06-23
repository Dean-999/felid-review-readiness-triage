#!/usr/bin/env python3
"""Train a Phase 10-Lite Plus projection head from preselected manifests.

Colab-only training entrypoint. The dataset is not reselected here: rows are
filtered only by split_id and phase10_lite_plus_group.
"""

from __future__ import annotations

import argparse
import ast
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml
from torch.utils.data import BatchSampler, DataLoader, Dataset
from tqdm import tqdm

REQUIRED_TRAINING_RULE = "use_preselected_phase10_lite_plus_group"
MATCHED_GROUPS = {
    "B3_random_matched_identity",
    "C3_quality_proxy_matched_identity",
    "D3_pf_eri_matched_identity",
    "H3_pf_eri_quality_hybrid_matched_identity",
}
E4_GROUP = "E4_pf_eri_weighted_all_train_reference"


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
            "w": torch.tensor(float(row.get("sample_weight", 1.0)), dtype=torch.float32),
        }


class IdentityBalancedPKBatchSampler(BatchSampler):
    """Yield batches with P identities and K images per identity."""

    def __init__(self, frame: pd.DataFrame, p: int, k: int, seed: int) -> None:
        self.p = int(p)
        self.k = int(k)
        self.seed = int(seed)
        self.by_identity: dict[str, list[int]] = defaultdict(list)
        for idx, identity in enumerate(frame["identity_label_internal"].astype(str)):
            self.by_identity[identity].append(idx)
        self.identities = sorted(self.by_identity)
        if len(self.identities) < self.p:
            raise ValueError(f"PK sampler requires at least P={self.p} identities; observed {len(self.identities)}")
        too_small = [identity for identity, indices in self.by_identity.items() if len(indices) < self.k]
        if too_small:
            raise ValueError(f"PK sampler requires at least K={self.k} images per identity; bad identities={len(too_small)}")

    def __iter__(self) -> Iterator[list[int]]:
        rng = random.Random(self.seed)
        identities = self.identities[:]
        rng.shuffle(identities)
        for start in range(0, len(identities), self.p):
            chosen = identities[start : start + self.p]
            if len(chosen) < self.p:
                break
            batch: list[int] = []
            for identity in chosen:
                batch.extend(rng.sample(self.by_identity[identity], self.k))
            yield batch

    def __len__(self) -> int:
        return len(self.identities) // self.p


class ProjectionHead(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, projection_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, projection_dim))

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
    return {str(row["expanded_image_id"]): parse_embedding_vector(row["embedding_vector"]) for _, row in frame.iterrows()}


def select_preselected_rows(manifest: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if config.get("training_rule") != REQUIRED_TRAINING_RULE:
        raise ValueError(f"required training_rule={REQUIRED_TRAINING_RULE}; observed {config.get('training_rule')!r}")
    required = {"split_id", "phase10_lite_plus_group", "identity_label_internal", "image_id", "train_val_test_role"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"manifest missing required columns: {sorted(missing)}")

    selected = manifest[
        (manifest["split_id"].astype(int) == int(config["split_id"]))
        & (manifest["phase10_lite_plus_group"].astype(str) == str(config["phase10_lite_plus_group"]))
    ].copy()
    if selected.empty:
        raise ValueError("selected Phase 10-Lite Plus rows are empty")
    roles = sorted(selected["train_val_test_role"].astype(str).str.lower().unique())
    if roles != ["train"]:
        raise ValueError(f"selected rows must be train-only; observed roles={roles}")

    group = str(config["phase10_lite_plus_group"])
    if group in MATCHED_GROUPS:
        k = int(config["images_per_identity_k"])
        if k != 3:
            raise ValueError(f"matched Plus groups must use k=3; observed {k}")
        if "images_per_identity_k" in selected.columns:
            selected = selected[selected["images_per_identity_k"].astype(str) == "3"].copy()
        per_identity = selected.groupby("identity_label_internal")["image_id"].nunique()
        bad = per_identity[per_identity != 3]
        if len(bad):
            raise ValueError(f"matched group requires exactly 3 images per identity; bad identities={len(bad)}")
    elif group == E4_GROUP:
        if "sample_weight" not in selected.columns:
            raise ValueError("E4 all-train reference requires sample_weight")
        per_identity = selected.groupby("identity_label_internal")["image_id"].nunique()
        if int(per_identity.min()) < 1 or int(per_identity.max()) < 3:
            raise ValueError("E4 all-train reference has too few images for PK sampling")
    else:
        raise ValueError(f"unknown Phase 10-Lite Plus group: {group}")

    expected_identity_count = int(config.get("expected_identity_count", 75))
    observed_identity_count = int(selected["identity_label_internal"].nunique())
    if observed_identity_count != expected_identity_count:
        raise ValueError(f"expected {expected_identity_count} identities, observed {observed_identity_count}")
    duplicated = int(selected.duplicated(["identity_label_internal", "image_id"]).sum())
    if duplicated:
        raise ValueError(f"duplicate image rows within selected identity set: {duplicated}")
    if "sample_weight" not in selected.columns:
        selected["sample_weight"] = 1.0
    selected["sample_weight"] = pd.to_numeric(selected["sample_weight"], errors="coerce").fillna(1.0)
    return selected


def verify_embedding_coverage(selected: pd.DataFrame, embeddings: dict[str, np.ndarray]) -> None:
    missing = sorted(set(selected["image_id"].astype(str)) - set(embeddings))
    if missing:
        raise ValueError(f"embeddings missing for {len(missing)} selected images; first missing={missing[:10]}")


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


def build_loader(selected: pd.DataFrame, embeddings: dict[str, np.ndarray], label_map: dict[str, int], config: dict[str, Any]) -> DataLoader:
    sampler_cfg = config.get("sampler", {})
    if sampler_cfg.get("type") != "identity_balanced_pk":
        raise ValueError("Phase 10-Lite Plus requires sampler.type=identity_balanced_pk")
    p = int(sampler_cfg.get("p_identities_per_batch", 16))
    k = int(sampler_cfg.get("k_images_per_identity_per_batch", 3))
    dataset = EmbeddingDataset(selected, embeddings, label_map)
    batch_sampler = IdentityBalancedPKBatchSampler(selected, p=p, k=k, seed=int(config.get("random_seed", 20260615)))
    return DataLoader(dataset, batch_sampler=batch_sampler)


def train(config: dict[str, Any]) -> None:
    print("WARNING: Phase 10-Lite Plus is a controlled pilot; no claim follows from training loss.")
    out_dir = resolve_path(config, "output_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(resolve_path(config, "manifest_path"))
    selected = select_preselected_rows(manifest, config)
    embeddings = load_embeddings(resolve_path(config, "embedding_path"))
    verify_embedding_coverage(selected, embeddings)
    label_map = {label: idx for idx, label in enumerate(sorted(selected["identity_label_internal"].astype(str).unique()))}
    loader = build_loader(selected, embeddings, label_map, config)

    model_cfg = config["model"]
    model = ProjectionHead(int(model_cfg["input_dim"]), int(model_cfg["hidden_dim"]), int(model_cfg["projection_dim"]))
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(model_cfg["learning_rate"]))
    temperature = float(config["loss"].get("temperature", 0.07))
    use_sample_weight = bool(config.get("loss", {}).get("use_sample_weight", False))

    rows = []
    for epoch in range(1, int(model_cfg["epochs"]) + 1):
        losses = []
        model.train()
        for batch in tqdm(loader, desc=f"epoch {epoch}", leave=False):
            optimizer.zero_grad()
            weights = batch["w"] if use_sample_weight else torch.ones_like(batch["w"])
            z = model(batch["x"])
            loss = supervised_contrastive_loss(z, batch["y"], weights, temperature)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        rows.append(
            {
                "epoch": epoch,
                "train_loss": float(np.mean(losses)) if losses else np.nan,
                "experiment_group": config["experiment_group"],
                "phase10_lite_plus_group": config["phase10_lite_plus_group"],
                "split_id": int(config["split_id"]),
                "selected_rows": int(len(selected)),
                "identity_count": int(selected["identity_label_internal"].nunique()),
                "sampler": "identity_balanced_pk",
                "p_identities_per_batch": int(config["sampler"]["p_identities_per_batch"]),
                "k_images_per_identity_per_batch": int(config["sampler"]["k_images_per_identity_per_batch"]),
            }
        )

    pd.DataFrame(rows).to_csv(out_dir / "phase10_lite_plus_training_metrics.csv", index=False)
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
