#!/usr/bin/env python3
"""Train Phase 11 pair-level PF-ERI weighted metric-learning projection head.

This is a Colab entrypoint. It uses fixed MegaDescriptor embeddings and a
small projection head. It does not fine-tune an image backbone.
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

REQUIRED_TRAINING_RULE = "use_phase11_pair_level_pf_eri_weights"
SUPPORTED_GROUPS = {
    "C3_quality_proxy_matched_identity",
    "H3_pf_eri_quality_hybrid_matched_identity",
    "P11_positive_pair_weighting",
    "P11_positive_weighting_negative_reliability_control",
    "P11B_positive_raw",
    "P11B_positive_floor05",
    "P11B_positive_sqrt",
    "P11B_positive_clip035",
    "P11C_C3base_sqrt",
    "P11C_C3base_a05_g065",
    "P11C_C3base_a10_g065",
    "P11C_H3base_a00_g050",
    "P11C_H3base_a05_g050",
    "P11C_H3base_a05_g065",
    "P11C_H3base_a10_g065",
    "P11C_H3base_a05_g080",
    "P11D_pos_rescue_q75_floor035",
    "P11D_pos_rescue_q85_floor035",
    "P11D_pos_rescue_q75_floor035_softneg_q95_w085",
    "P11D_pos_rescue_q85_floor035_softneg_q95_w085",
    "P11DR_rescue_desc_q80_R045_floor035",
    "P11DR_rescue_pattern030_q75_R045_floor035",
    "P11DR_rescue_desc_q85_R050_floor030",
    "P11DR2_target05_floor035",
    "P11DR2_target10_floor035",
    "P11DR2_target10_floor040",
}
SUPPORTED_POSITIVE_WEIGHT_TRANSFORMS = {
    "raw",
    "floor05",
    "sqrt",
    "clip035",
    "alpha_gamma",
    "parameterized_power",
    "sqrt_conditional_rescue",
    "sqrt_target_rate_rescue",
}


class EmbeddingDataset(Dataset):
    def __init__(self, frame: pd.DataFrame, embeddings: dict[str, np.ndarray], label_map: dict[str, int]) -> None:
        self.frame = frame.reset_index(drop=True)
        self.embeddings = embeddings
        self.label_map = label_map

    def __len__(self) -> int:
        return len(self.frame)

    def __getitem__(self, idx: int) -> dict[str, object]:
        row = self.frame.iloc[idx]
        image_id = str(row["image_id"])
        return {
            "x": torch.tensor(self.embeddings[image_id], dtype=torch.float32),
            "y": torch.tensor(self.label_map[str(row["identity_label_internal"])], dtype=torch.long),
            "image_id": image_id,
        }


class IdentityBalancedPKBatchSampler(BatchSampler):
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
    required = {"expanded_image_id", "embedding_vector"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    out = {}
    for _, row in frame.iterrows():
        vec = parse_embedding_vector(row["embedding_vector"])
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            out[str(row["expanded_image_id"])] = vec / norm
    return out


def select_rows(manifest: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if config.get("training_rule") != REQUIRED_TRAINING_RULE:
        raise ValueError(f"required training_rule={REQUIRED_TRAINING_RULE}; observed {config.get('training_rule')!r}")
    if config.get("experiment_group") not in SUPPORTED_GROUPS:
        raise ValueError(f"unsupported experiment_group={config.get('experiment_group')!r}")
    required = {"split_id", "phase10_lite_plus_group", "identity_label_internal", "image_id", "train_val_test_role"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"manifest missing columns: {sorted(missing)}")
    selected = manifest[
        (manifest["split_id"].astype(int) == int(config["split_id"]))
        & (manifest["phase10_lite_plus_group"].astype(str) == str(config["base_group_name"]))
    ].copy()
    if selected.empty:
        raise ValueError("selected training rows are empty")
    roles = sorted(selected["train_val_test_role"].astype(str).str.lower().unique())
    if roles != ["train"]:
        raise ValueError(f"Phase 11 selected rows must be train-only; observed roles={roles}")
    if selected.duplicated(["identity_label_internal", "image_id"]).any():
        raise ValueError("duplicate image rows in selected training rows")
    return selected


def load_pair_weights(
    pair_table_path: Path,
    split_id: int,
    base_group_name: str,
    config: dict[str, Any],
) -> tuple[dict[tuple[str, str], dict[str, float]], dict[str, float]]:
    pair_table = pd.read_csv(pair_table_path)
    required = {
        "split_id",
        "group_name",
        "image_id_a",
        "image_id_b",
        "same_identity",
        "descriptor_similarity",
        "pattern_pair_score",
        "positive_pair_weight",
        "negative_pair_weight",
        "pair_reliability_score",
    }
    missing = required - set(pair_table.columns)
    if missing:
        raise ValueError(f"pair table missing columns: {sorted(missing)}")
    subset = pair_table[
        (pair_table["split_id"].astype(int) == int(split_id)) & (pair_table["group_name"].astype(str) == str(base_group_name))
    ].copy()
    if subset.empty:
        raise ValueError("0 pair rows for requested split/base_group_name")
    subset["same_identity_bool"] = subset["same_identity"].astype(str).str.lower().isin(["true", "1", "yes"])
    subset["descriptor_similarity"] = pd.to_numeric(subset["descriptor_similarity"], errors="coerce")
    if subset["descriptor_similarity"].isna().any():
        raise ValueError("pair table descriptor_similarity contains missing/non-numeric values")
    loss_cfg = config.get("loss", {})
    positive_similarity_quantile = float(loss_cfg.get("positive_rescue_similarity_quantile", 0.75))
    soft_negative_similarity_quantile = float(loss_cfg.get("soft_negative_similarity_quantile", 0.95))
    positives = subset[subset["same_identity_bool"]]
    negatives = subset[~subset["same_identity_bool"]]
    thresholds = {
        "positive_rescue_similarity_threshold": float(positives["descriptor_similarity"].quantile(positive_similarity_quantile))
        if len(positives)
        else float("nan"),
        "soft_negative_similarity_threshold": float(negatives["descriptor_similarity"].quantile(soft_negative_similarity_quantile))
        if len(negatives)
        else float("nan"),
    }
    target_rescue_keys: set[tuple[str, str]] = set()
    if bool(loss_cfg.get("target_rescue_enabled", False)):
        score_name = str(loss_cfg.get("target_rescue_score", "descriptor_times_one_minus_reliability"))
        if score_name != "descriptor_times_one_minus_reliability":
            raise ValueError(f"unsupported target_rescue_score={score_name!r}")
        reliability_max = float(loss_cfg.get("target_rescue_reliability_max", 0.55))
        target_fraction = float(loss_cfg.get("target_rescue_fraction", 0.05))
        candidates = positives[pd.to_numeric(positives["pair_reliability_score"], errors="coerce") < reliability_max].copy()
        if len(candidates):
            candidates["target_rescue_score"] = (
                pd.to_numeric(candidates["descriptor_similarity"], errors="coerce")
                * (1.0 - pd.to_numeric(candidates["pair_reliability_score"], errors="coerce"))
            )
            target_k = int(round(target_fraction * len(positives)))
            target_k = max(1, target_k) if len(positives) else 0
            rescued = candidates.sort_values(
                ["target_rescue_score", "descriptor_similarity", "pair_reliability_score"],
                ascending=[False, False, True],
            ).head(target_k)
            for _, row in rescued.iterrows():
                target_rescue_keys.add(tuple(sorted((str(row["image_id_a"]), str(row["image_id_b"])))))
        thresholds.update(
            {
                "target_rescue_candidate_count": int(len(candidates)),
                "target_rescue_count": int(len(target_rescue_keys)),
                "target_rescue_fraction": target_fraction,
                "target_rescue_reliability_max": reliability_max,
            }
        )
    weights = {}
    for _, row in subset.iterrows():
        a = str(row["image_id_a"])
        b = str(row["image_id_b"])
        key = tuple(sorted((a, b)))
        weights[key] = {
            "positive": float(row["positive_pair_weight"]),
            "negative": float(row["negative_pair_weight"]),
            "reliability": float(row["pair_reliability_score"]),
            "descriptor_similarity": float(row["descriptor_similarity"]),
            "pattern_pair_score": float(row["pattern_pair_score"]),
            "same_identity": bool(row["same_identity_bool"]),
            "target_rescue_selected": bool(key in target_rescue_keys),
        }
    return weights, thresholds


def verify_embedding_coverage(selected: pd.DataFrame, embeddings: dict[str, np.ndarray]) -> None:
    missing = sorted(set(selected["image_id"].astype(str)) - set(embeddings))
    if missing:
        raise ValueError(f"embeddings missing for {len(missing)} selected images; first missing={missing[:10]}")


def transform_positive_weight(
    pair_reliability_score: float,
    mode: str,
    alpha: float = 0.0,
    gamma: float = 1.0,
) -> float:
    """Transform pair reliability into a positive-pair loss weight."""
    reliability = max(0.0, min(1.0, float(pair_reliability_score)))
    if mode == "raw":
        return reliability
    if mode == "floor05":
        return 0.5 + 0.5 * reliability
    if mode == "sqrt":
        return float(np.sqrt(reliability))
    if mode == "sqrt_conditional_rescue":
        return float(np.sqrt(reliability))
    if mode == "sqrt_target_rate_rescue":
        return float(np.sqrt(reliability))
    if mode == "clip035":
        return max(0.35, reliability)
    if mode in {"alpha_gamma", "parameterized_power"}:
        alpha = max(0.0, min(1.0, float(alpha)))
        gamma = max(0.0, float(gamma))
        return max(0.0, min(1.0, alpha + (1.0 - alpha) * (reliability**gamma)))
    raise ValueError(f"unsupported positive_weight_transform={mode!r}")


def batch_pair_weight_matrices(
    image_ids: list[str],
    y: torch.Tensor,
    pair_weights: dict[tuple[str, str], dict[str, float]],
    loss_mode: str,
    positive_weight_transform: str,
    positive_weight_alpha: float,
    positive_weight_gamma: float,
    conditional_cfg: dict[str, Any],
    pair_thresholds: dict[str, float],
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    n = len(image_ids)
    positive_weights = torch.zeros((n, n), dtype=torch.float32, device=device)
    denominator_weights = torch.ones((n, n), dtype=torch.float32, device=device)
    eye = torch.eye(n, dtype=torch.bool, device=device)
    denominator_weights[eye] = 0.0
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            same = bool(y[i].item() == y[j].item())
            key = tuple(sorted((image_ids[i], image_ids[j])))
            payload = pair_weights.get(key)
            if same:
                if loss_mode == "uniform_pair_weight":
                    positive_weights[i, j] = 1.0
                else:
                    reliability = float(payload["reliability"] if payload else 1.0)
                    weight = transform_positive_weight(
                        pair_reliability_score=reliability,
                        mode=positive_weight_transform,
                        alpha=positive_weight_alpha,
                        gamma=positive_weight_gamma,
                    )
                    if bool(conditional_cfg.get("positive_rescue_enabled", False)) and payload:
                        pattern_required = bool(conditional_cfg.get("positive_rescue_pattern_required", True))
                        pattern_supported = (not pattern_required) or (
                            float(payload["pattern_pair_score"])
                            >= float(conditional_cfg.get("positive_rescue_pattern_min", 0.45))
                        )
                        rescue = (
                            reliability < float(conditional_cfg.get("positive_rescue_reliability_max", 0.40))
                            and float(payload["descriptor_similarity"])
                            >= float(pair_thresholds["positive_rescue_similarity_threshold"])
                            and pattern_supported
                        )
                        if rescue:
                            weight = max(weight, float(conditional_cfg.get("positive_rescue_floor", 0.35)))
                    if bool(conditional_cfg.get("target_rescue_enabled", False)) and payload:
                        if bool(payload.get("target_rescue_selected", False)):
                            weight = max(weight, float(conditional_cfg.get("target_rescue_floor", 0.35)))
                    positive_weights[i, j] = weight
            elif loss_mode == "positive_weighting_negative_reliability_control":
                denominator_weights[i, j] = float(payload["negative"] if payload else 1.0)
            elif bool(conditional_cfg.get("soft_negative_enabled", False)) and payload:
                soft_negative = (
                    float(payload["descriptor_similarity"]) >= float(pair_thresholds["soft_negative_similarity_threshold"])
                    and float(payload["reliability"]) <= float(conditional_cfg.get("soft_negative_reliability_max", 0.40))
                )
                denominator_weights[i, j] = float(conditional_cfg.get("soft_negative_weight", 0.85)) if soft_negative else 1.0
    return positive_weights, denominator_weights


def pair_weighted_supervised_contrastive_loss(
    z: torch.Tensor,
    y: torch.Tensor,
    image_ids: list[str],
    pair_weights: dict[tuple[str, str], dict[str, float]],
    loss_mode: str,
    positive_weight_transform: str,
    positive_weight_alpha: float,
    positive_weight_gamma: float,
    conditional_cfg: dict[str, Any],
    pair_thresholds: dict[str, float],
    temperature: float,
) -> torch.Tensor:
    sim = torch.matmul(z, z.T) / temperature
    logits = sim - sim.max(dim=1, keepdim=True).values.detach()
    pos_w, denom_w = batch_pair_weight_matrices(
        image_ids=image_ids,
        y=y,
        pair_weights=pair_weights,
        loss_mode=loss_mode,
        positive_weight_transform=positive_weight_transform,
        positive_weight_alpha=positive_weight_alpha,
        positive_weight_gamma=positive_weight_gamma,
        conditional_cfg=conditional_cfg,
        pair_thresholds=pair_thresholds,
        device=z.device,
    )
    exp_logits = torch.exp(logits) * denom_w
    log_prob = logits - torch.log(exp_logits.sum(dim=1, keepdim=True).clamp_min(1e-12))
    pos_sum = pos_w.sum(dim=1)
    per_sample = -(log_prob * pos_w).sum(dim=1) / pos_sum.clamp_min(1e-12)
    has_positive = pos_sum > 0
    if not bool(has_positive.any()):
        raise ValueError("batch has no positive pairs")
    return per_sample[has_positive].mean()


def build_loader(selected: pd.DataFrame, embeddings: dict[str, np.ndarray], label_map: dict[str, int], config: dict[str, Any]) -> DataLoader:
    sampler_cfg = config.get("sampler", {})
    if sampler_cfg.get("type") != "identity_balanced_pk":
        raise ValueError("Phase 11 requires sampler.type=identity_balanced_pk")
    dataset = EmbeddingDataset(selected, embeddings, label_map)
    sampler = IdentityBalancedPKBatchSampler(
        selected,
        p=int(sampler_cfg.get("p_identities_per_batch", 16)),
        k=int(sampler_cfg.get("k_images_per_identity_per_batch", 3)),
        seed=int(config.get("random_seed", 20260615)),
    )
    return DataLoader(dataset, batch_sampler=sampler)


def train(config: dict[str, Any]) -> None:
    print("WARNING: Phase 11 one-epoch training is an engineering/pilot run, not scientific success evidence.")
    out_dir = resolve_path(config, "output_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(resolve_path(config, "manifest_path"))
    selected = select_rows(manifest, config)
    embeddings = load_embeddings(resolve_path(config, "embedding_path"))
    verify_embedding_coverage(selected, embeddings)
    pair_weights, pair_thresholds = load_pair_weights(
        resolve_path(config, "pair_table_path"),
        int(config["split_id"]),
        str(config["base_group_name"]),
        config,
    )
    label_map = {label: idx for idx, label in enumerate(sorted(selected["identity_label_internal"].astype(str).unique()))}
    loader = build_loader(selected, embeddings, label_map, config)

    model_cfg = config["model"]
    model = ProjectionHead(int(model_cfg["input_dim"]), int(model_cfg["hidden_dim"]), int(model_cfg["projection_dim"]))
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(model_cfg["learning_rate"]))
    temperature = float(config["loss"].get("temperature", 0.07))
    loss_mode = str(config["loss"].get("pair_weight_mode", "uniform_pair_weight"))
    positive_weight_transform = str(config["loss"].get("positive_weight_transform", "raw"))
    if positive_weight_transform not in SUPPORTED_POSITIVE_WEIGHT_TRANSFORMS:
        raise ValueError(f"unsupported positive_weight_transform={positive_weight_transform!r}")
    positive_weight_alpha = float(config["loss"].get("positive_weight_alpha", 0.0))
    positive_weight_gamma = float(config["loss"].get("positive_weight_gamma", 1.0))
    conditional_cfg = {
        "positive_rescue_enabled": bool(config["loss"].get("positive_rescue_enabled", False)),
        "positive_rescue_reliability_max": float(config["loss"].get("positive_rescue_reliability_max", 0.40)),
        "positive_rescue_similarity_quantile": float(config["loss"].get("positive_rescue_similarity_quantile", 0.75)),
        "positive_rescue_pattern_min": float(config["loss"].get("positive_rescue_pattern_min", 0.45)),
        "positive_rescue_pattern_required": bool(config["loss"].get("positive_rescue_pattern_required", True)),
        "positive_rescue_floor": float(config["loss"].get("positive_rescue_floor", 0.35)),
        "soft_negative_enabled": bool(config["loss"].get("soft_negative_enabled", False)),
        "soft_negative_similarity_quantile": float(config["loss"].get("soft_negative_similarity_quantile", 0.95)),
        "soft_negative_reliability_max": float(config["loss"].get("soft_negative_reliability_max", 0.40)),
        "soft_negative_weight": float(config["loss"].get("soft_negative_weight", 0.85)),
        "target_rescue_enabled": bool(config["loss"].get("target_rescue_enabled", False)),
        "target_rescue_fraction": float(config["loss"].get("target_rescue_fraction", 0.0)),
        "target_rescue_reliability_max": float(config["loss"].get("target_rescue_reliability_max", 0.55)),
        "target_rescue_floor": float(config["loss"].get("target_rescue_floor", 0.35)),
        "target_rescue_score": str(config["loss"].get("target_rescue_score", "descriptor_times_one_minus_reliability")),
    }

    rows = []
    for epoch in range(1, int(model_cfg["epochs"]) + 1):
        losses = []
        model.train()
        for batch in tqdm(loader, desc=f"epoch {epoch}", leave=False):
            optimizer.zero_grad()
            z = model(batch["x"])
            loss = pair_weighted_supervised_contrastive_loss(
                z=z,
                y=batch["y"],
                image_ids=[str(v) for v in batch["image_id"]],
                pair_weights=pair_weights,
                loss_mode=loss_mode,
                positive_weight_transform=positive_weight_transform,
                positive_weight_alpha=positive_weight_alpha,
                positive_weight_gamma=positive_weight_gamma,
                conditional_cfg=conditional_cfg,
                pair_thresholds=pair_thresholds,
                temperature=temperature,
            )
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        rows.append(
            {
                "epoch": epoch,
                "train_loss": float(np.mean(losses)) if losses else np.nan,
                "experiment_group": config["experiment_group"],
                "base_group_name": config["base_group_name"],
                "split_id": int(config["split_id"]),
                "selected_rows": int(len(selected)),
                "identity_count": int(selected["identity_label_internal"].nunique()),
                "loss_mode": loss_mode,
                "positive_weight_transform": positive_weight_transform,
                "positive_weight_alpha": positive_weight_alpha,
                "positive_weight_gamma": positive_weight_gamma,
                "positive_rescue_enabled": conditional_cfg["positive_rescue_enabled"],
                "positive_rescue_pattern_required": conditional_cfg["positive_rescue_pattern_required"],
                "positive_rescue_similarity_threshold": pair_thresholds["positive_rescue_similarity_threshold"],
                "soft_negative_enabled": conditional_cfg["soft_negative_enabled"],
                "soft_negative_similarity_threshold": pair_thresholds["soft_negative_similarity_threshold"],
                "target_rescue_enabled": conditional_cfg["target_rescue_enabled"],
                "target_rescue_fraction": conditional_cfg["target_rescue_fraction"],
                "target_rescue_candidate_count": pair_thresholds.get("target_rescue_candidate_count", 0),
                "target_rescue_count": pair_thresholds.get("target_rescue_count", 0),
            }
        )

    pd.DataFrame(rows).to_csv(out_dir / "phase11_training_metrics.csv", index=False)
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
