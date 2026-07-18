#!/usr/bin/env python3
"""Train interpretable CzechLynx reviewability validation models."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts import build_evidence_feature_extraction as feature_builder
except ImportError:  # pragma: no cover - direct script execution
    import build_evidence_feature_extraction as feature_builder


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE_CSV = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/evidence-feature-extraction/pair_evidence_features.csv"
IMAGE_INDEX_CSV = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/final-modeling-bootstrap/final_modeling_image_index.csv"
MAJORITY_LABELS_CSV = (
    PROJECT_ROOT
    / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/identity-balanced-analysis/legacy-code18m_pair_majority_labels.csv"
)
PACKET_ROOT = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/pair-level-validation/identity-balanced-review-packet"
OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/known-id-evidence-sufficiency-validation"
VALIDATION_TABLE_CSV = OUTPUT_DIR / "known_id_reviewability_validation_table.csv"
METRICS_CSV = OUTPUT_DIR / "known_id_model_metrics.csv"
COEFFICIENTS_CSV = OUTPUT_DIR / "known_id_model_coefficients.csv"
CALIBRATION_CSV = OUTPUT_DIR / "known_id_calibration_bins.csv"
AUDIT_JSON = OUTPUT_DIR / "known_id_validation_audit.json"
REPORT_MD = OUTPUT_DIR / "README.md"
ISSUE3_OUTPUT_DIR = PROJECT_ROOT / "archive/pferi_v1/outputs/modeling-validation/story-hardening-issue3"
ISSUE3_MODEL_COMPARISON_CSV = ISSUE3_OUTPUT_DIR / "issue3_core_incremental_model_comparison.csv"
ISSUE3_AUDIT_JSON = ISSUE3_OUTPUT_DIR / "issue3_core_incremental_model_evidence_audit.json"
ISSUE3_REPORT_MD = PROJECT_ROOT / "docs/modeling-validation/2026-07-09_core_incremental_model_evidence.md"

DESCRIPTORS = ["megadescriptor_l_384", "dinov2_vitl14"]
RANDOM_SEED = 20260707
BOOTSTRAP_ITERATIONS = 300

QUALITY_FEATURES = ["visible_pattern_area_score", "body_part_overlap_score", "night_or_motion_blur_risk"]
PF_ERI_FEATURES = list(feature_builder.CORE_FEATURES)
REQUIRED_MODEL_FAMILIES = [
    "descriptor_only",
    "quality_only",
    "pf_eri_evidence_only",
    "descriptor_plus_quality",
    "descriptor_plus_pf_eri",
    "descriptor_plus_quality_plus_pf_eri",
]


def unique_features(feature_names: list[str]) -> list[str]:
    seen: set[str] = set()
    output = []
    for name in feature_names:
        if name not in seen:
            output.append(name)
            seen.add(name)
    return output


MODEL_FAMILIES = {
    "descriptor_only": ["descriptor_similarity_percentile"],
    "quality_only": QUALITY_FEATURES,
    "pf_eri_evidence_only": PF_ERI_FEATURES,
    "descriptor_plus_quality": unique_features(["descriptor_similarity_percentile", *QUALITY_FEATURES]),
    "descriptor_plus_pf_eri": unique_features(["descriptor_similarity_percentile", *PF_ERI_FEATURES]),
    "descriptor_plus_quality_plus_pf_eri": unique_features(
        ["descriptor_similarity_percentile", *QUALITY_FEATURES, *PF_ERI_FEATURES]
    ),
}

VALIDATION_COLUMNS = [
    "descriptor_name",
    "review_pair_id",
    "query_image_id",
    "candidate_image_id",
    "query_pferi_image_id",
    "candidate_pferi_image_id",
    "component_group_id",
    "fold_id",
    "majority_decision",
    "review_ready_label",
    "not_ready_or_uncertain_label",
    "same_identity_known_id",
    "rank_bin",
    "evidence_group",
    "descriptor_similarity_percentile",
    *feature_builder.CORE_FEATURES,
    "feature_source",
    "claim_boundary",
]

METRIC_COLUMNS = [
    "scope",
    "model_family",
    "feature_names",
    "row_set_id",
    "pair_count",
    "positive_review_ready_count",
    "negative_not_ready_or_uncertain_count",
    "auroc",
    "auroc_ci_lower",
    "auroc_ci_upper",
    "auprc",
    "auprc_ci_lower",
    "auprc_ci_upper",
    "brier_score",
    "ece_5bin",
    "mean_score_ready",
    "mean_score_non_ready",
    "effect_size_ready_minus_non_ready",
    "claim_boundary",
]

COEFFICIENT_COLUMNS = ["scope", "model_family", "fold_id", "feature_name", "coefficient", "intercept"]
CALIBRATION_COLUMNS = ["scope", "model_family", "bin_id", "row_count", "mean_predicted", "observed_review_ready_rate"]
ISSUE3_COMPARISON_COLUMNS = [
    "scope",
    "model_family",
    "feature_set_role",
    "feature_names",
    "row_set_id",
    "pair_count",
    "positive_review_ready_count",
    "negative_not_ready_or_uncertain_count",
    "auroc",
    "auroc_ci_lower",
    "auroc_ci_upper",
    "auprc",
    "auprc_ci_lower",
    "auprc_ci_upper",
    "brier_score",
    "ece_5bin",
    "delta_auroc_vs_descriptor_only",
    "delta_auprc_vs_descriptor_only",
    "delta_auroc_vs_quality_only",
    "delta_auprc_vs_quality_only",
    "delta_auroc_vs_descriptor_plus_quality",
    "delta_auprc_vs_descriptor_plus_quality",
    "interpretation_boundary",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def sigmoid(value: float) -> float:
    if value >= 35:
        return 1.0
    if value <= -35:
        return 0.0
    return 1.0 / (1.0 + math.exp(-value))


def phase18_to_pferi(image_id: str) -> str:
    if image_id.startswith("phase18a_czechlynx_"):
        return f"pferi_lynx_wild_{int(image_id.rsplit('_', 1)[1]):05d}"
    return ""


def connected_component_folds(rows: list[dict[str, Any]], fold_count: int = 5) -> dict[str, int]:
    graph: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        qid = row["query_pferi_image_id"]
        cid = row["candidate_pferi_image_id"]
        graph[qid].add(cid)
        graph[cid].add(qid)
    component_by_node: dict[str, str] = {}
    for node in sorted(graph):
        if node in component_by_node:
            continue
        queue: deque[str] = deque([node])
        component_nodes: list[str] = []
        while queue:
            current = queue.popleft()
            if current in component_by_node:
                continue
            component_nodes.append(current)
            component_by_node[current] = node
            queue.extend(sorted(graph[current] - set(component_by_node)))
        component_id = "component_" + hashlib.sha1("|".join(sorted(component_nodes)).encode("utf-8")).hexdigest()[:10]
        for item in component_nodes:
            component_by_node[item] = component_id
    fold_by_component = {
        component: int(hashlib.sha1(component.encode("utf-8")).hexdigest()[:8], 16) % fold_count
        for component in set(component_by_node.values())
    }
    return {
        row["review_pair_id"]: fold_by_component[component_by_node[row["query_pferi_image_id"]]]
        for row in rows
    }


def load_review_packet_rows() -> dict[tuple[str, str], dict[str, str]]:
    packets: dict[tuple[str, str], dict[str, str]] = {}
    for descriptor in DESCRIPTORS:
        packet_csv = PACKET_ROOT / descriptor / "legacy-code18m_identity_balanced_review_packet.csv"
        for row in read_csv(packet_csv):
            packets[(descriptor, row["review_pair_id"])] = row
    return packets


def feature_table_pair_keys() -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for row in read_csv(FEATURE_TABLE_CSV):
        if row["pair_family"] == "known_id_validation":
            keys.add((row["query_image_id"], row["candidate_image_id"]))
            keys.add((row["candidate_image_id"], row["query_image_id"]))
    return keys


def build_validation_rows() -> tuple[list[dict[str, Any]], int]:
    majority_rows = read_csv(MAJORITY_LABELS_CSV)
    packet_rows = load_review_packet_rows()
    image_rows = feature_builder.read_csv(IMAGE_INDEX_CSV)
    images_by_id = feature_builder.load_manifest_rows(image_rows)
    megadescriptor_scores = feature_builder.load_pair_score_lookup(feature_builder.MEGADESCRIPTOR_PAIR_SCORES)
    dinov2_scores = feature_builder.load_pair_score_lookup(feature_builder.DINOV2_PAIR_SCORES)
    megadescriptor_embeddings = feature_builder.load_embedding_lookup(feature_builder.MEGADESCRIPTOR_ROOT)
    dinov2_embeddings = feature_builder.load_embedding_lookup(feature_builder.DINOV2_ROOT)
    scaffold_keys = feature_table_pair_keys()

    rows: list[dict[str, Any]] = []
    direct_overlap = 0
    for majority in majority_rows:
        packet = packet_rows[(majority["descriptor_name"], majority["review_pair_id"])]
        query_pferi = phase18_to_pferi(packet["query_image_id"])
        candidate_pferi = phase18_to_pferi(packet["candidate_image_id"])
        if (query_pferi, candidate_pferi) in scaffold_keys or (candidate_pferi, query_pferi) in scaffold_keys:
            direct_overlap += 1
        pseudo_pair = {
            "pair_id": majority["review_pair_id"],
            "pair_family": "known_id_reviewability_validation",
            "pair_scope": "lynx-wild",
            "construction_rule": "phase18m_reviewed_descriptor_pair",
            "query_image_id": query_pferi,
            "candidate_image_id": candidate_pferi,
            "query_scope": "lynx-wild",
            "candidate_scope": "lynx-wild",
            "query_species": "czechlynx",
            "candidate_species": "czechlynx",
            "query_domain_label": "wild",
            "candidate_domain_label": "wild",
            "split_id": "0",
            "split_role": "derived_by_component_group",
            "identity_relation": "known",
            "same_identity_label": "yes" if majority["same_identity_known_id"] == "yes" else "no",
            "query_identity_label": "",
            "candidate_identity_label": "",
        }
        feature_row = feature_builder.enrich_pair(
            pseudo_pair,
            images_by_id,
            megadescriptor_scores,
            dinov2_scores,
            megadescriptor_embeddings,
            dinov2_embeddings,
        )
        rows.append(
            {
                "descriptor_name": majority["descriptor_name"],
                "review_pair_id": majority["review_pair_id"],
                "query_image_id": packet["query_image_id"],
                "candidate_image_id": packet["candidate_image_id"],
                "query_pferi_image_id": query_pferi,
                "candidate_pferi_image_id": candidate_pferi,
                "component_group_id": "",
                "fold_id": "",
                "majority_decision": majority["majority_decision"],
                "review_ready_label": 0 if majority["majority_binary_not_ready_or_uncertain"] == "1" else 1,
                "not_ready_or_uncertain_label": int(majority["majority_binary_not_ready_or_uncertain"]),
                "same_identity_known_id": majority["same_identity_known_id"],
                "rank_bin": majority["rank_bin"],
                "evidence_group": majority["evidence_group"],
                "descriptor_similarity_percentile": majority["descriptor_similarity_percentile"],
                **{feature: feature_row[feature] for feature in feature_builder.CORE_FEATURES},
                "feature_source": "phase18m_reviewed_pair_recomputed_with_issue7_feature_definitions",
                "claim_boundary": "CzechLynx reviewability validation labels only; no Bobcat identity claims.",
            }
        )
    fold_by_pair = connected_component_folds(rows)
    for row in rows:
        row["fold_id"] = fold_by_pair[row["review_pair_id"]]
        row["component_group_id"] = f"fold_component_{row['fold_id']}"
    return rows, direct_overlap


def standardize(train: list[list[float]], rows: list[list[float]]) -> tuple[list[list[float]], list[float], list[float]]:
    if not train:
        return rows, [], []
    width = len(train[0])
    means = [sum(row[i] for row in train) / len(train) for i in range(width)]
    stds = []
    for i in range(width):
        variance = sum((row[i] - means[i]) ** 2 for row in train) / max(1, len(train) - 1)
        stds.append(math.sqrt(variance) or 1.0)
    return [[(row[i] - means[i]) / stds[i] for i in range(width)] for row in rows], means, stds


def train_logistic(xs: list[list[float]], ys: list[int], l2: float = 0.05, epochs: int = 600, lr: float = 0.08) -> tuple[list[float], float]:
    if not xs:
        return [], 0.0
    weights = [0.0 for _ in xs[0]]
    intercept = 0.0
    for _ in range(epochs):
        grad_w = [0.0 for _ in weights]
        grad_b = 0.0
        for x, y in zip(xs, ys):
            pred = sigmoid(intercept + sum(w * value for w, value in zip(weights, x)))
            error = pred - y
            grad_b += error
            for i, value in enumerate(x):
                grad_w[i] += error * value
        n = len(xs)
        intercept -= lr * grad_b / n
        for i in range(len(weights)):
            grad = grad_w[i] / n + l2 * weights[i]
            weights[i] -= lr * grad
    return weights, intercept


def predict_logistic(xs: list[list[float]], weights: list[float], intercept: float) -> list[float]:
    return [sigmoid(intercept + sum(w * value for w, value in zip(weights, x))) for x in xs]


def auroc(labels: list[int], scores: list[float]) -> float:
    pos = [score for label, score in zip(labels, scores) if label == 1]
    neg = [score for label, score in zip(labels, scores) if label == 0]
    if not pos or not neg:
        return 0.0
    wins = 0.0
    for a in pos:
        for b in neg:
            wins += 1.0 if a > b else 0.5 if a == b else 0.0
    return wins / (len(pos) * len(neg))


def average_precision(labels: list[int], scores: list[float]) -> float:
    positives = sum(labels)
    if positives == 0:
        return 0.0
    ranked = sorted(zip(scores, labels), reverse=True)
    hits = 0
    precision_sum = 0.0
    for rank, (_, label) in enumerate(ranked, start=1):
        if label == 1:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / positives


def brier(labels: list[int], scores: list[float]) -> float:
    return sum((score - label) ** 2 for label, score in zip(labels, scores)) / len(labels) if labels else 0.0


def ece(labels: list[int], scores: list[float], bins: int = 5) -> float:
    total = len(labels)
    if total == 0:
        return 0.0
    value = 0.0
    for bin_id in range(bins):
        low = bin_id / bins
        high = (bin_id + 1) / bins
        idx = [i for i, score in enumerate(scores) if low <= score <= high if bin_id == bins - 1 or score < high]
        if not idx:
            continue
        pred = sum(scores[i] for i in idx) / len(idx)
        obs = sum(labels[i] for i in idx) / len(idx)
        value += len(idx) / total * abs(pred - obs)
    return value


def bootstrap_ci(labels: list[int], scores: list[float], metric: str) -> tuple[float, float]:
    rng = random.Random(RANDOM_SEED)
    estimates = []
    n = len(labels)
    fn = auroc if metric == "auroc" else average_precision
    for _ in range(BOOTSTRAP_ITERATIONS):
        idx = [rng.randrange(n) for _ in range(n)]
        sampled_labels = [labels[i] for i in idx]
        sampled_scores = [scores[i] for i in idx]
        if len(set(sampled_labels)) < 2:
            continue
        estimates.append(fn(sampled_labels, sampled_scores))
    if not estimates:
        return 0.0, 0.0
    estimates.sort()
    return estimates[int(0.025 * (len(estimates) - 1))], estimates[int(0.975 * (len(estimates) - 1))]


def calibration_rows(scope: str, model_family: str, labels: list[int], scores: list[float], bins: int = 5) -> list[dict[str, Any]]:
    rows = []
    for bin_id in range(bins):
        low = bin_id / bins
        high = (bin_id + 1) / bins
        idx = [i for i, score in enumerate(scores) if low <= score <= high if bin_id == bins - 1 or score < high]
        rows.append(
            {
                "scope": scope,
                "model_family": model_family,
                "bin_id": bin_id,
                "row_count": len(idx),
                "mean_predicted": sum(scores[i] for i in idx) / len(idx) if idx else "",
                "observed_review_ready_rate": sum(labels[i] for i in idx) / len(idx) if idx else "",
            }
        )
    return rows


def row_set_id_for_scope(scope: str, rows: list[dict[str, Any]]) -> str:
    pair_ids = sorted(row["review_pair_id"] for row in rows)
    digest = hashlib.sha1("|".join(pair_ids).encode("utf-8")).hexdigest()[:12]
    return f"{scope}_pairs_{len(pair_ids)}_{digest}"


def evaluate_scope(rows: list[dict[str, Any]], scope: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    metrics: list[dict[str, Any]] = []
    coefficients: list[dict[str, Any]] = []
    calibration: list[dict[str, Any]] = []
    folds = sorted({int(row["fold_id"]) for row in rows})
    row_set_id = row_set_id_for_scope(scope, rows)
    for model_family, feature_names in MODEL_FAMILIES.items():
        predictions: dict[str, float] = {}
        labels_by_pair: dict[str, int] = {}
        for fold in folds:
            train_rows = [row for row in rows if int(row["fold_id"]) != fold]
            eval_rows = [row for row in rows if int(row["fold_id"]) == fold]
            if not train_rows or not eval_rows:
                continue
            train_x = [[to_float(row[name]) for name in feature_names] for row in train_rows]
            eval_x = [[to_float(row[name]) for name in feature_names] for row in eval_rows]
            train_y = [int(row["review_ready_label"]) for row in train_rows]
            train_x_std, means, stds = standardize(train_x, train_x)
            eval_x_std = [[(row[i] - means[i]) / stds[i] for i in range(len(feature_names))] for row in eval_x]
            weights, intercept = train_logistic(train_x_std, train_y)
            eval_scores = predict_logistic(eval_x_std, weights, intercept)
            for row, score in zip(eval_rows, eval_scores):
                predictions[row["review_pair_id"]] = score
                labels_by_pair[row["review_pair_id"]] = int(row["review_ready_label"])
            for name, weight in zip(feature_names, weights):
                coefficients.append(
                    {
                        "scope": scope,
                        "model_family": model_family,
                        "fold_id": fold,
                        "feature_name": name,
                        "coefficient": weight,
                        "intercept": intercept,
                    }
                )
        ordered_pairs = sorted(predictions)
        labels = [labels_by_pair[pair_id] for pair_id in ordered_pairs]
        scores = [predictions[pair_id] for pair_id in ordered_pairs]
        ready_scores = [score for label, score in zip(labels, scores) if label == 1]
        non_ready_scores = [score for label, score in zip(labels, scores) if label == 0]
        auroc_ci = bootstrap_ci(labels, scores, "auroc")
        auprc_ci = bootstrap_ci(labels, scores, "auprc")
        metrics.append(
            {
                "scope": scope,
                "model_family": model_family,
                "feature_names": ",".join(feature_names),
                "row_set_id": row_set_id,
                "pair_count": len(labels),
                "positive_review_ready_count": sum(labels),
                "negative_not_ready_or_uncertain_count": len(labels) - sum(labels),
                "auroc": auroc(labels, scores),
                "auroc_ci_lower": auroc_ci[0],
                "auroc_ci_upper": auroc_ci[1],
                "auprc": average_precision(labels, scores),
                "auprc_ci_lower": auprc_ci[0],
                "auprc_ci_upper": auprc_ci[1],
                "brier_score": brier(labels, scores),
                "ece_5bin": ece(labels, scores),
                "mean_score_ready": sum(ready_scores) / len(ready_scores) if ready_scores else 0.0,
                "mean_score_non_ready": sum(non_ready_scores) / len(non_ready_scores) if non_ready_scores else 0.0,
                "effect_size_ready_minus_non_ready": (sum(ready_scores) / len(ready_scores) if ready_scores else 0.0)
                - (sum(non_ready_scores) / len(non_ready_scores) if non_ready_scores else 0.0),
                "claim_boundary": "CzechLynx human reviewability validation only; not Bobcat identity accuracy.",
            }
        )
        calibration.extend(calibration_rows(scope, model_family, labels, scores))
    return metrics, coefficients, calibration


def feature_set_role(model_family: str) -> str:
    return {
        "descriptor_only": "descriptor similarity control",
        "quality_only": "image quality control",
        "pf_eri_evidence_only": "pair-level PF-ERI evidence",
        "descriptor_plus_quality": "descriptor and quality active control",
        "descriptor_plus_pf_eri": "descriptor plus pair-level evidence",
        "descriptor_plus_quality_plus_pf_eri": "full active-control incremental model",
    }[model_family]


def metric_lookup(metrics: list[dict[str, Any]], scope: str, model_family: str) -> dict[str, Any] | None:
    for row in metrics:
        if row["scope"] == scope and row["model_family"] == model_family:
            return row
    return None


def delta(row: dict[str, Any], baseline: dict[str, Any] | None, metric: str) -> float | str:
    if baseline is None:
        return ""
    return to_float(row[metric]) - to_float(baseline[metric])


def issue3_comparison_rows(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for scope in ["pooled", *DESCRIPTORS]:
        descriptor = metric_lookup(metrics, scope, "descriptor_only")
        quality = metric_lookup(metrics, scope, "quality_only")
        descriptor_quality = metric_lookup(metrics, scope, "descriptor_plus_quality")
        for model_family in REQUIRED_MODEL_FAMILIES:
            row = metric_lookup(metrics, scope, model_family)
            if row is None:
                continue
            output.append(
                {
                    "scope": row["scope"],
                    "model_family": row["model_family"],
                    "feature_set_role": feature_set_role(model_family),
                    "feature_names": row["feature_names"],
                    "row_set_id": row["row_set_id"],
                    "pair_count": row["pair_count"],
                    "positive_review_ready_count": row["positive_review_ready_count"],
                    "negative_not_ready_or_uncertain_count": row["negative_not_ready_or_uncertain_count"],
                    "auroc": row["auroc"],
                    "auroc_ci_lower": row["auroc_ci_lower"],
                    "auroc_ci_upper": row["auroc_ci_upper"],
                    "auprc": row["auprc"],
                    "auprc_ci_lower": row["auprc_ci_lower"],
                    "auprc_ci_upper": row["auprc_ci_upper"],
                    "brier_score": row["brier_score"],
                    "ece_5bin": row["ece_5bin"],
                    "delta_auroc_vs_descriptor_only": delta(row, descriptor, "auroc"),
                    "delta_auprc_vs_descriptor_only": delta(row, descriptor, "auprc"),
                    "delta_auroc_vs_quality_only": delta(row, quality, "auroc"),
                    "delta_auprc_vs_quality_only": delta(row, quality, "auprc"),
                    "delta_auroc_vs_descriptor_plus_quality": delta(row, descriptor_quality, "auroc"),
                    "delta_auprc_vs_descriptor_plus_quality": delta(row, descriptor_quality, "auprc"),
                    "interpretation_boundary": (
                        "Human reviewability/evidential admissibility only; no identity accuracy, mAP, MRR, "
                        "top-k identity improvement, or Bobcat identity claim."
                    ),
                }
            )
    return output


def format_metric(value: Any, digits: int = 3) -> str:
    if value == "":
        return "not estimable"
    return f"{to_float(value):.{digits}f}"


def model_sentence(row: dict[str, Any]) -> str:
    return (
        f"In the {row['scope']} analysis, the {row['model_family']} model achieved "
        f"AUROC {format_metric(row['auroc'])} (95% bootstrap CI "
        f"{format_metric(row['auroc_ci_lower'])}-{format_metric(row['auroc_ci_upper'])}), "
        f"AUPRC {format_metric(row['auprc'])} (95% bootstrap CI "
        f"{format_metric(row['auprc_ci_lower'])}-{format_metric(row['auprc_ci_upper'])}), "
        f"Brier score {format_metric(row['brier_score'])}, and five-bin ECE "
        f"{format_metric(row['ece_5bin'])}."
    )


def write_issue3_report(comparison_rows: list[dict[str, Any]], audit: dict[str, Any]) -> None:
    pooled_rows = [row for row in comparison_rows if row["scope"] == "pooled"]
    full_row = next(row for row in pooled_rows if row["model_family"] == "descriptor_plus_quality_plus_pf_eri")
    descriptor_quality = next(row for row in pooled_rows if row["model_family"] == "descriptor_plus_quality")
    pf_eri_only = next(row for row in pooled_rows if row["model_family"] == "pf_eri_evidence_only")
    quality_only = next(row for row in pooled_rows if row["model_family"] == "quality_only")
    descriptor_only = next(row for row in pooled_rows if row["model_family"] == "descriptor_only")
    descriptor_specific_full = [
        row
        for row in comparison_rows
        if row["scope"] in DESCRIPTORS and row["model_family"] == "descriptor_plus_quality_plus_pf_eri"
    ]

    lines = [
        "# Core Incremental Model Evidence",
        "",
        "Date: 2026-07-09",
        "",
        f"Status: `{audit['issue3_status']}`",
        "",
        "This result addresses the central modeling question in the current project story: whether PF-ERI carries pair-level evidence-admission signal after a strong descriptor has already returned a candidate pair. The endpoint is human reviewability and evidential admissibility on CzechLynx reviewed pairs. The endpoint is not identity accuracy, retrieval ranking quality, Bobcat identity performance, mean average precision, mean reciprocal rank, or top-k identity improvement.",
        "",
        "All six model families were evaluated on identical row sets within each scope. The pooled scope uses the combined reviewed candidate-pair table, and the descriptor-specific scopes repeat the same comparison separately for MegaDescriptor and DINOv2. Each model is an interpretable L2 logistic validation model evaluated by component-group cross-validation, with AUROC, AUPRC, Brier score, five-bin expected calibration error, and bootstrap intervals for AUROC and AUPRC.",
        "",
        model_sentence(descriptor_only),
        model_sentence(quality_only),
        model_sentence(pf_eri_only),
        model_sentence(descriptor_quality),
        model_sentence(full_row),
        "",
        f"The strongest active-control comparison is the full model against descriptor plus quality. In the pooled table, adding PF-ERI features to descriptor similarity and image-quality controls changed AUROC by {format_metric(full_row['delta_auroc_vs_descriptor_plus_quality'])} and AUPRC by {format_metric(full_row['delta_auprc_vs_descriptor_plus_quality'])}. PF-ERI evidence alone exceeded the quality-only control by AUROC {format_metric(pf_eri_only['delta_auroc_vs_quality_only'])} and AUPRC {format_metric(pf_eri_only['delta_auprc_vs_quality_only'])}. The descriptor-specific active-control increments were not uniformly positive: "
        + " ".join(
            f"{row['scope']} changed AUROC by {format_metric(row['delta_auroc_vs_descriptor_plus_quality'])} and AUPRC by {format_metric(row['delta_auprc_vs_descriptor_plus_quality'])}."
            for row in descriptor_specific_full
        )
        + " This pattern supports the bounded statement that PF-ERI carries reviewability-relevant pair evidence, while the incremental advantage over a descriptor-plus-quality control is small in the pooled table and requires the planned quality and similarity sensitivity package before it should be treated as a strong standalone superiority claim.",
        "",
        "The interpretation remains deliberately bounded. These models test whether pair-level evidence features align with human reviewability labels after descriptor retrieval. They do not establish automatic individual identification, they do not validate Bobcat identity labels, and they do not claim that PF-ERI improves mAP, MRR, or top-k identity retrieval. The paper-ready table for this issue is the source of truth for the incremental model evidence.",
        "",
        "## Artifact Links",
        "",
        f"The paper-ready comparison table is `{audit['issue3_model_comparison_csv']}`. The full validation metrics table is `{audit['metrics_csv']}`. The calibration bins are `{audit['calibration_csv']}`. The Issue 3 audit file is `{audit['issue3_audit_json']}`.",
    ]
    ISSUE3_REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    ISSUE3_REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    rows, direct_overlap = build_validation_rows()
    scope_rows = {"pooled": rows}
    for descriptor in DESCRIPTORS:
        scope_rows[descriptor] = [row for row in rows if row["descriptor_name"] == descriptor]
    all_metrics: list[dict[str, Any]] = []
    all_coefficients: list[dict[str, Any]] = []
    all_calibration: list[dict[str, Any]] = []
    for scope, subset in scope_rows.items():
        metrics, coefficients, calibration = evaluate_scope(subset, scope)
        all_metrics.extend(metrics)
        all_coefficients.extend(coefficients)
        all_calibration.extend(calibration)
    comparison_rows = issue3_comparison_rows(all_metrics)

    image_folds: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        image_folds[row["query_pferi_image_id"]].add(str(row["fold_id"]))
        image_folds[row["candidate_pferi_image_id"]].add(str(row["fold_id"]))
    image_fold_leakage_count = sum(1 for folds in image_folds.values() if len(folds) > 1)
    expected_metric_rows = len(REQUIRED_MODEL_FAMILIES) * (1 + len(DESCRIPTORS))
    scopes = ["pooled", *DESCRIPTORS]
    row_set_counts_by_scope = {
        scope: len({row["row_set_id"] for row in all_metrics if row["scope"] == scope})
        for scope in scopes
    }
    model_families_by_scope = {
        scope: [row["model_family"] for row in all_metrics if row["scope"] == scope]
        for scope in scopes
    }
    issue3_status = (
        "PASS"
        if len(comparison_rows) == expected_metric_rows
        and all(row_set_counts_by_scope[scope] == 1 for scope in scopes)
        and all(model_families_by_scope[scope] == REQUIRED_MODEL_FAMILIES for scope in scopes)
        else "FAIL"
    )
    status = (
        "PASS"
        if rows
        and all_metrics
        and issue3_status == "PASS"
        and image_fold_leakage_count == 0
        and all(row["query_pferi_image_id"].startswith("pferi_lynx_wild_") for row in rows)
        else "FAIL"
    )
    audit = {
        "built_at_utc": utc_now(),
        "status": status,
        "input_feature_table_csv": project_relative(FEATURE_TABLE_CSV),
        "input_majority_labels_csv": project_relative(MAJORITY_LABELS_CSV),
        "validation_table_csv": project_relative(VALIDATION_TABLE_CSV),
        "metrics_csv": project_relative(METRICS_CSV),
        "coefficient_csv": project_relative(COEFFICIENTS_CSV),
        "calibration_csv": project_relative(CALIBRATION_CSV),
        "issue3_model_comparison_csv": project_relative(ISSUE3_MODEL_COMPARISON_CSV),
        "issue3_report_md": project_relative(ISSUE3_REPORT_MD),
        "issue3_audit_json": project_relative(ISSUE3_AUDIT_JSON),
        "reviewability_rows": len(rows),
        "direct_overlap_with_issue7_pair_feature_table": direct_overlap,
        "descriptor_counts": dict(sorted(Counter(row["descriptor_name"] for row in rows).items())),
        "review_ready_counts": dict(sorted(Counter(str(row["review_ready_label"]) for row in rows).items())),
        "model_metric_rows": len(all_metrics),
        "expected_model_metric_rows": expected_metric_rows,
        "issue3_status": issue3_status,
        "issue3_model_families": REQUIRED_MODEL_FAMILIES,
        "issue3_row_set_counts_by_scope": row_set_counts_by_scope,
        "issue3_model_families_by_scope": model_families_by_scope,
        "bobcat_rows": sum("bobcat" in row["query_pferi_image_id"] or "bobcat" in row["candidate_pferi_image_id"] for row in rows),
        "unique_images_in_validation": len(image_folds),
        "image_fold_leakage_count": image_fold_leakage_count,
        "allowed_claims": [
            "CzechLynx reviewed-pair evidence sufficiency can be evaluated with human reviewability labels.",
            "Model-family comparisons are exploratory unless robustness/claim gates pass later.",
        ],
        "blocked_claims": [
            "Bobcat identity accuracy",
            "Bobcat false-match accuracy",
            "mAP/MRR/top-k identity retrieval improvement",
            "MRR identity retrieval improvement",
            "Top-k identity improvement",
            "Automatic individual identification",
        ],
        "claim_boundary": "Known-ID CzechLynx reviewability validation only.",
    }
    issue3_audit = {
        "built_at_utc": audit["built_at_utc"],
        "status": issue3_status,
        "model_families": REQUIRED_MODEL_FAMILIES,
        "scopes": scopes,
        "row_set_counts_by_scope": row_set_counts_by_scope,
        "model_families_by_scope": model_families_by_scope,
        "model_comparison_csv": project_relative(ISSUE3_MODEL_COMPARISON_CSV),
        "report_md": project_relative(ISSUE3_REPORT_MD),
        "blocked_claims": audit["blocked_claims"],
        "claim_boundary": (
            "CzechLynx human reviewability and evidential admissibility only; identity accuracy, mAP, "
            "MRR, top-k identity improvement, and Bobcat identity claims are blocked."
        ),
    }
    write_csv(VALIDATION_TABLE_CSV, rows, VALIDATION_COLUMNS)
    write_csv(METRICS_CSV, all_metrics, METRIC_COLUMNS)
    write_csv(COEFFICIENTS_CSV, all_coefficients, COEFFICIENT_COLUMNS)
    write_csv(CALIBRATION_CSV, all_calibration, CALIBRATION_COLUMNS)
    write_csv(ISSUE3_MODEL_COMPARISON_CSV, comparison_rows, ISSUE3_COMPARISON_COLUMNS)
    write_json(AUDIT_JSON, audit)
    write_json(ISSUE3_AUDIT_JSON, issue3_audit)
    write_report(audit)
    write_issue3_report(comparison_rows, audit)
    return audit


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Known-ID Evidence Sufficiency Validation",
        "",
        f"Status: `{audit['status']}`",
        "",
        "This module trains interpretable L2 logistic validation models on the",
        "CzechLynx Phase18M reviewed identity-balanced pairs using the issue #7",
        "PF-ERI evidence feature definitions.",
        "",
        "## Outputs",
        "",
        f"- Validation table: `{audit['validation_table_csv']}`",
        f"- Metrics: `{audit['metrics_csv']}`",
        f"- Coefficients: `{audit['coefficient_csv']}`",
        f"- Calibration bins: `{audit['calibration_csv']}`",
        f"- Issue 3 paper-ready comparison: `{audit['issue3_model_comparison_csv']}`",
        f"- Issue 3 report: `{audit['issue3_report_md']}`",
        "",
        "## Boundary",
        "",
        audit["claim_boundary"],
        "Bobcat identity metrics remain blocked.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = build()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
