#!/usr/bin/env python3
"""Run Phase 13D RQ4 fixed-embedding training sanity experiments.

This combines two evidence layers:
1. simulated loss-exposure analysis from Phase 13C weights;
2. fixed-embedding projection-head training with the same policy weights.

It does not fine-tune an image backbone. The default run is intentionally small
for local sanity checking before Colab/GPU expansion.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_MANIFEST = PROJECT_ROOT / "outputs/czechlynx/phase13/rq4_training_control_manifest/phase13c_rq4_pair_training_control_manifest.csv"
IDENTITY_TABLE = PROJECT_ROOT / "data/interim/czechlynx/czechlynx_phase7a_1000_internal_with_ids.csv"
MEGA_EMBEDDINGS = PROJECT_ROOT / "outputs/czechlynx/phase7a/czechlynx_phase7a_1000_megadescriptor_embeddings.csv"
RESNET_EMBEDDINGS = PROJECT_ROOT / "outputs/czechlynx/phase7a/czechlynx_phase7a_1000_resnet50_embeddings.csv"
OUT_DIR = PROJECT_ROOT / "outputs/czechlynx/phase13/rq4_fixed_embedding_training"

EXPOSURE = OUT_DIR / "phase13d_rq4_loss_exposure_summary.csv"
TRAINING_METRICS = OUT_DIR / "phase13d_rq4_training_metrics.csv"
RETRIEVAL_METRICS = OUT_DIR / "phase13d_rq4_retrieval_metrics.csv"
PAIR_SAMPLE = OUT_DIR / "phase13d_rq4_training_pair_sample.csv"
SUMMARY_MD = OUT_DIR / "phase13d_rq4_fixed_embedding_training_summary.md"
BUILD_AUDIT = OUT_DIR / "phase13d_rq4_fixed_embedding_training_build_audit.json"

RANDOM_SEED = 20260618
POLICIES = [
    "descriptor_only",
    "random_control",
    "quality_control",
    "pf_eri_positive",
    "pf_eri_conflict_aware",
]


@dataclass(frozen=True)
class PolicyColumns:
    positive: str
    negative: str


POLICY_COLUMNS = {
    "descriptor_only": PolicyColumns("descriptor_only_positive_weight", "descriptor_only_negative_weight"),
    "random_control": PolicyColumns("random_positive_weight", "random_negative_weight"),
    "quality_control": PolicyColumns("quality_control_positive_weight", "quality_control_negative_weight"),
    "pf_eri_positive": PolicyColumns("pf_eri_positive_weight", "pf_eri_negative_weight"),
    "pf_eri_conflict_aware": PolicyColumns(
        "pf_eri_conflict_aware_positive_weight",
        "pf_eri_conflict_aware_negative_weight",
    ),
}


class ProjectionHead(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, projection_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, projection_dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.net(x), dim=1)


class IdentityProjection(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(x, dim=1)


def yes_no_to_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"yes", "true", "1"})


def safe_mean(values: pd.Series | np.ndarray | list[float]) -> float:
    series = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    return float(series.mean()) if len(series) else math.nan


def image_token(expanded_image_id: object) -> str:
    return hashlib.sha256(str(expanded_image_id).encode("utf-8")).hexdigest()[:12]


def parse_embedding_vector(value: object) -> np.ndarray:
    if isinstance(value, str):
        return np.asarray(ast.literal_eval(value), dtype=np.float32)
    if isinstance(value, (list, tuple, np.ndarray)):
        return np.asarray(value, dtype=np.float32)
    raise ValueError(f"unsupported embedding vector value type: {type(value)!r}")


def load_embeddings(path: Path) -> tuple[dict[str, np.ndarray], int]:
    frame = pd.read_csv(path)
    embeddings: dict[str, np.ndarray] = {}
    dim = 0
    for _, row in frame.iterrows():
        vec = parse_embedding_vector(row["embedding_vector"])
        dim = int(len(vec))
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            embeddings[image_token(row["expanded_image_id"])] = vec / norm
    return embeddings, dim


def load_identity_roles(path: Path) -> pd.DataFrame:
    identity = pd.read_csv(path, usecols=["expanded_image_id", "working_individual_id"])
    identity["image_token"] = identity["expanded_image_id"].map(image_token)
    counts = identity.groupby("working_individual_id")["expanded_image_id"].transform("nunique")
    identity["identity_image_count"] = counts.astype(int)
    identity["can_form_positive_pair"] = identity["identity_image_count"].ge(2)
    return identity[["image_token", "working_individual_id", "identity_image_count", "can_form_positive_pair"]].copy()


def load_pair_manifest(path: Path, split_id: int, descriptor: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame = frame[
        frame["split_id"].astype(int).eq(int(split_id))
        & frame["descriptor"].astype(str).eq(str(descriptor))
    ].copy()
    if frame.empty:
        raise ValueError(f"0 pair rows for split_id={split_id} descriptor={descriptor}")
    bool_cols = [
        "same_identity",
        "positive_pair_eligible",
        "singleton_involved",
        "unsafe_hard_negative",
        "descriptor_hard_negative",
        "conflict_hard_negative",
    ]
    for col in bool_cols:
        frame[col] = yes_no_to_bool(frame[col])
    if "random_negative_weight" not in frame.columns:
        frame["random_negative_weight"] = frame["descriptor_only_negative_weight"]
    return frame


def build_exposure(frame: pd.DataFrame, split_id: int, descriptor: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    positives = frame[frame["positive_pair_eligible"]]
    negatives = frame[~frame["same_identity"]]
    unsafe = frame[frame["unsafe_hard_negative"]]
    for policy_id in POLICIES:
        cols = POLICY_COLUMNS[policy_id]
        rows.append(
            {
                "split_id": int(split_id),
                "descriptor": descriptor,
                "policy_id": policy_id,
                "pair_count": int(len(frame)),
                "eligible_positive_count": int(len(positives)),
                "negative_count": int(len(negatives)),
                "unsafe_hard_negative_count": int(len(unsafe)),
                "positive_weight_sum": float(positives[cols.positive].sum()),
                "negative_weight_sum": float(negatives[cols.negative].sum()),
                "unsafe_hard_negative_weight_sum": float(unsafe[cols.negative].sum()),
                "mean_positive_weight": safe_mean(positives[cols.positive]),
                "mean_negative_weight": safe_mean(negatives[cols.negative]),
                "mean_unsafe_hard_negative_weight": safe_mean(unsafe[cols.negative]),
                "positive_to_negative_weight_ratio": float(positives[cols.positive].sum() / max(negatives[cols.negative].sum(), 1e-12)),
                "unsafe_negative_weight_fraction": float(unsafe[cols.negative].sum() / max(negatives[cols.negative].sum(), 1e-12)),
            }
        )
    return pd.DataFrame(rows)


def pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((str(a), str(b))))


def policy_pair_frame(frame: pd.DataFrame, policy_id: str, embeddings: dict[str, np.ndarray]) -> pd.DataFrame:
    cols = POLICY_COLUMNS[policy_id]
    out = frame[
        frame["query_image_id"].astype(str).isin(embeddings)
        & frame["candidate_image_id"].astype(str).isin(embeddings)
    ].copy()
    out["pair_label"] = out["same_identity"].astype(int)
    out["policy_weight"] = np.where(out["same_identity"], out[cols.positive], out[cols.negative])
    out["policy_weight"] = pd.to_numeric(out["policy_weight"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    out = out[out["policy_weight"].gt(0)].copy()
    return out.reset_index(drop=True)


def sample_training_pairs(frame: pd.DataFrame, max_pairs: int, seed: int) -> pd.DataFrame:
    positives = frame[frame["pair_label"].eq(1)].copy()
    negatives = frame[frame["pair_label"].eq(0)].copy()
    if positives.empty or negatives.empty:
        raise ValueError("training requires both positive and negative pairs")
    target_per_class = max(1, max_pairs // 2)
    pos_n = min(len(positives), target_per_class)
    neg_n = min(len(negatives), target_per_class)
    positives = positives.sample(n=pos_n, random_state=seed, weights=positives["policy_weight"])
    negatives = negatives.sample(n=neg_n, random_state=seed + 1, weights=negatives["policy_weight"])
    sampled = pd.concat([positives, negatives], ignore_index=True)
    return sampled.sample(frac=1.0, random_state=seed + 2).reset_index(drop=True)


def pairwise_projection_loss(
    za: torch.Tensor,
    zb: torch.Tensor,
    labels: torch.Tensor,
    weights: torch.Tensor,
    margin: float,
) -> torch.Tensor:
    distance = 1.0 - (za * zb).sum(dim=1).clamp(-1.0, 1.0)
    positive_loss = labels * distance.pow(2)
    negative_loss = (1.0 - labels) * F.relu(margin - distance).pow(2)
    weighted = (positive_loss + negative_loss) * weights
    return weighted.sum() / weights.sum().clamp_min(1e-12)


def choose_training_images(frame: pd.DataFrame, identities: pd.DataFrame, embeddings: dict[str, np.ndarray], max_images: int) -> pd.DataFrame:
    tokens = set(frame["query_image_id"].astype(str)) | set(frame["candidate_image_id"].astype(str))
    eligible = identities[
        identities["image_token"].isin(tokens)
        & identities["image_token"].isin(embeddings)
        & identities["can_form_positive_pair"]
    ].copy()
    eligible["identity_size_in_pool"] = eligible.groupby("working_individual_id")["image_token"].transform("nunique")
    eligible = eligible[eligible["identity_size_in_pool"].ge(2)].copy()
    eligible = eligible.sort_values(["working_individual_id", "image_token"])
    if len(eligible) <= max_images:
        return eligible.reset_index(drop=True)
    selected_rows = []
    for _, group in eligible.groupby("working_individual_id", sort=True):
        selected_rows.append(group.head(3))
    selected = pd.concat(selected_rows, ignore_index=True)
    if len(selected) > max_images:
        selected = selected.head(max_images)
    return selected.reset_index(drop=True)


def train_policy(
    policy_id: str,
    frame: pd.DataFrame,
    embeddings: dict[str, np.ndarray],
    input_dim: int,
    args: argparse.Namespace,
) -> tuple[nn.Module, list[dict[str, Any]]]:
    torch.manual_seed(RANDOM_SEED)
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    model = ProjectionHead(input_dim=input_dim, hidden_dim=args.hidden_dim, projection_dim=args.projection_dim)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    policy_pairs = sample_training_pairs(policy_pair_frame(frame, policy_id, embeddings), args.max_train_pairs, RANDOM_SEED)
    batch_count = int(math.ceil(len(policy_pairs) / args.batch_size))
    rows: list[dict[str, Any]] = []
    for epoch in range(1, args.epochs + 1):
        epoch_pairs = policy_pairs.sample(frac=1.0, random_state=RANDOM_SEED + epoch).reset_index(drop=True)
        losses: list[float] = []
        model.train()
        for start in range(0, len(epoch_pairs), args.batch_size):
            batch = epoch_pairs.iloc[start : start + args.batch_size]
            xa = torch.tensor(np.stack([embeddings[str(token)] for token in batch["query_image_id"]]), dtype=torch.float32)
            xb = torch.tensor(np.stack([embeddings[str(token)] for token in batch["candidate_image_id"]]), dtype=torch.float32)
            labels = torch.tensor(batch["pair_label"].to_numpy(dtype=np.float32), dtype=torch.float32)
            weights = torch.tensor(batch["policy_weight"].to_numpy(dtype=np.float32), dtype=torch.float32)
            optimizer.zero_grad()
            loss = pairwise_projection_loss(model(xa), model(xb), labels, weights, args.margin)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        rows.append(
            {
                "policy_id": policy_id,
                "epoch": epoch,
                "train_loss": float(np.mean(losses)),
                "batch_count": batch_count,
                "train_pair_count": int(len(policy_pairs)),
                "train_positive_pair_count": int(policy_pairs["pair_label"].sum()),
                "train_negative_pair_count": int((1 - policy_pairs["pair_label"]).sum()),
                "mean_policy_weight": safe_mean(policy_pairs["policy_weight"]),
            }
        )
    return model, rows


def average_precision(relevance: np.ndarray) -> float:
    positives = int(relevance.sum())
    if positives == 0:
        return 0.0
    cumulative = np.cumsum(relevance)
    return float((cumulative[relevance == 1] / (np.flatnonzero(relevance == 1) + 1)).mean())


def project_all(model: nn.Module, embeddings: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    projected: dict[str, np.ndarray] = {}
    model.eval()
    with torch.no_grad():
        for token, vec in embeddings.items():
            z = model(torch.tensor(vec[None, :], dtype=torch.float32)).numpy()[0]
            norm = max(float(np.linalg.norm(z)), 1e-12)
            projected[token] = z / norm
    return projected


def evaluate_policy(
    policy_id: str,
    model: nn.Module,
    embeddings: dict[str, np.ndarray],
    identities: pd.DataFrame,
    frame: pd.DataFrame,
    split_id: int,
    descriptor: str,
    top_k: int,
) -> dict[str, Any]:
    projected = project_all(model, embeddings)
    eval_tokens = set(frame.loc[frame["calibration_or_evaluation"].eq("evaluation"), "query_image_id"].astype(str))
    eval_images = identities[
        identities["image_token"].isin(eval_tokens)
        & identities["image_token"].isin(projected)
        & identities["can_form_positive_pair"]
    ].copy()
    eval_images["identity_size_eval"] = eval_images.groupby("working_individual_id")["image_token"].transform("nunique")
    eval_images = eval_images[eval_images["identity_size_eval"].ge(2)].copy()
    if eval_images.empty:
        raise ValueError("0 evaluation images with positive gallery")
    gallery = eval_images.reset_index(drop=True)
    ap_values: list[float] = []
    rr_values: list[float] = []
    top1_values: list[int] = []
    top5_values: list[int] = []
    false_candidates = 0
    false_top1 = 0
    for _, query in eval_images.iterrows():
        qid = str(query["image_token"])
        qlabel = str(query["working_individual_id"])
        qvec = projected[qid]
        sims = []
        for _, candidate in gallery.iterrows():
            gid = str(candidate["image_token"])
            if gid == qid:
                continue
            same = str(candidate["working_individual_id"]) == qlabel
            sims.append((gid, float(np.dot(qvec, projected[gid])), same))
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
    return {
        "split_id": int(split_id),
        "descriptor": descriptor,
        "policy_id": policy_id,
        "valid_query_count": int(len(ap_values)),
        "mAP_at_k": float(np.mean(ap_values)),
        "MRR_at_k": float(np.mean(rr_values)),
        "top1_accuracy": float(np.mean(top1_values)),
        "top5_accuracy": float(np.mean(top5_values)),
        "false_top1_rate": float(false_top1 / max(len(ap_values), 1)),
        "false_candidate_burden_at_k": float(false_candidates / max(len(ap_values), 1)),
        "query_coverage": float(len(ap_values) / max(len(eval_images), 1)),
    }


def add_raw_delta_metrics(retrieval: pd.DataFrame) -> pd.DataFrame:
    retrieval = retrieval.copy()
    metric_cols = [
        "mAP_at_k",
        "MRR_at_k",
        "top1_accuracy",
        "top5_accuracy",
        "false_top1_rate",
        "false_candidate_burden_at_k",
    ]
    for _, group in retrieval.groupby(["split_id", "descriptor"], sort=False):
        raw = group[group["policy_id"].eq("raw_fixed_embedding")]
        if raw.empty:
            continue
        raw_row = raw.iloc[0]
        idx = group.index
        for col in metric_cols:
            retrieval.loc[idx, f"delta_vs_raw_{col}"] = pd.to_numeric(retrieval.loc[idx, col], errors="coerce") - float(raw_row[col])
    return retrieval


def write_summary(exposure: pd.DataFrame, training: pd.DataFrame, retrieval: pd.DataFrame, args: argparse.Namespace) -> None:
    lines = [
        "# Phase 13D RQ4 Fixed-Embedding Training",
        "",
        "Date: 2026-06-18",
        "",
        "## Purpose",
        "",
        "This phase combines simulated loss-exposure analysis with a fixed-embedding projection-head sanity run. It is not a backbone fine-tuning result.",
        "",
        "## Run Scope",
        "",
        f"- split_id: {args.split_id}",
        f"- descriptor: {args.descriptor}",
        f"- epochs: {args.epochs}",
        f"- max train images: {args.max_train_images}",
        "",
        "## Exposure Summary",
        "",
    ]
    for _, row in exposure.iterrows():
        lines.append(
            "- "
            f"{row['policy_id']}: positive weight sum={row['positive_weight_sum']:.2f}, "
            f"negative weight sum={row['negative_weight_sum']:.2f}, "
            f"unsafe negative fraction={row['unsafe_negative_weight_fraction']:.4f}, "
            f"mean unsafe negative weight={row['mean_unsafe_hard_negative_weight']:.3f}"
        )
    lines += ["", "## Retrieval Summary", ""]
    for _, row in retrieval.sort_values("policy_id").iterrows():
        lines.append(
            "- "
            f"{row['policy_id']}: mAP@{args.top_k}={row['mAP_at_k']:.4f}, "
            f"delta_mAP={row.get('delta_vs_raw_mAP_at_k', math.nan):.4f}, "
            f"top1={row['top1_accuracy']:.4f}, "
            f"delta_top1={row.get('delta_vs_raw_top1_accuracy', math.nan):.4f}, "
            f"false_top1={row['false_top1_rate']:.4f}, "
            f"false burden@{args.top_k}={row['false_candidate_burden_at_k']:.4f}"
        )
    lines += [
        "",
        "## Interpretation Boundary",
        "",
        "A local sanity run checks implementation and signal direction only. Scientific RQ4 evidence requires multi-split runs and comparison against quality-control and random-control policies.",
        "",
        "## Outputs",
        "",
        f"- `{EXPOSURE.relative_to(PROJECT_ROOT)}`",
        f"- `{TRAINING_METRICS.relative_to(PROJECT_ROOT)}`",
        f"- `{RETRIEVAL_METRICS.relative_to(PROJECT_ROOT)}`",
        f"- `{PAIR_SAMPLE.relative_to(PROJECT_ROOT)}`",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    descriptor_to_embeddings = {
        "megadescriptor": MEGA_EMBEDDINGS,
        "resnet50": RESNET_EMBEDDINGS,
    }
    frame = load_pair_manifest(args.pair_manifest, args.split_id, args.descriptor)
    identities = load_identity_roles(args.identity_table)
    embeddings, input_dim = load_embeddings(descriptor_to_embeddings[args.descriptor])
    train_rows = frame[frame["calibration_or_evaluation"].eq("calibration")].copy()
    train_images = choose_training_images(train_rows, identities, embeddings, args.max_train_images)
    if train_images.empty:
        raise ValueError("0 training images selected")
    exposure = build_exposure(frame, args.split_id, args.descriptor)
    all_training_rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = [
        evaluate_policy(
            "raw_fixed_embedding",
            IdentityProjection(),
            embeddings,
            identities,
            frame,
            args.split_id,
            args.descriptor,
            args.top_k,
        )
    ]
    policies = args.policies or POLICIES
    for policy_id in policies:
        model, training_rows = train_policy(policy_id, train_rows, embeddings, input_dim, args)
        all_training_rows.extend(
            {
                "split_id": int(args.split_id),
                "descriptor": args.descriptor,
                **row,
            }
            for row in training_rows
        )
        retrieval_rows.append(
            evaluate_policy(policy_id, model, embeddings, identities, frame, args.split_id, args.descriptor, args.top_k)
        )
    training = pd.DataFrame(all_training_rows)
    retrieval = add_raw_delta_metrics(pd.DataFrame(retrieval_rows))
    exposure = exposure[exposure["policy_id"].isin(policies)].copy()

    exposure.to_csv(EXPOSURE, index=False)
    training.to_csv(TRAINING_METRICS, index=False)
    retrieval.to_csv(RETRIEVAL_METRICS, index=False)
    sample_cols = [
        "split_id",
        "calibration_or_evaluation",
        "descriptor",
        "query_image_id",
        "candidate_image_id",
        "same_identity",
        "positive_pair_eligible",
        "unsafe_hard_negative",
        "pf_eri_positive_weight",
        "quality_control_positive_weight",
        "pf_eri_conflict_aware_negative_weight",
        "recommended_rq4_policy",
    ]
    frame[sample_cols].head(500).to_csv(PAIR_SAMPLE, index=False)
    write_summary(exposure, training, retrieval, args)

    audit = {
        "split_id": int(args.split_id),
        "descriptor": args.descriptor,
        "input_pair_rows": int(len(frame)),
        "train_pair_rows": int(len(train_rows)),
        "train_image_count": int(len(train_images)),
        "train_identity_count": int(train_images["working_individual_id"].nunique()),
        "embedding_count": int(len(embeddings)),
        "input_dim": int(input_dim),
        "max_train_pairs": int(args.max_train_pairs),
        "batch_size": int(args.batch_size),
        "policies": policies,
        "training_metric_rows": int(len(training)),
        "retrieval_metric_rows": int(len(retrieval)),
    }
    BUILD_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote Phase 13D RQ4 fixed-embedding training outputs to {OUT_DIR.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-manifest", type=Path, default=PAIR_MANIFEST)
    parser.add_argument("--identity-table", type=Path, default=IDENTITY_TABLE)
    parser.add_argument("--split-id", type=int, default=1)
    parser.add_argument("--descriptor", choices=["megadescriptor", "resnet50"], default="megadescriptor")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--max-train-images", type=int, default=240)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--projection-dim", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--margin", type=float, default=0.35)
    parser.add_argument("--max-train-pairs", type=int, default=3000)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--p-identities", type=int, default=12)
    parser.add_argument("--k-images", type=int, default=2)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--policies", nargs="*", choices=POLICIES)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
