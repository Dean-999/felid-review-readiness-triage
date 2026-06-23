#!/usr/bin/env python3
"""Build the Phase 14 2x2 pair-level comparability table.

The table is a controlled pair sample over the four 3000-image working-final
quadrants. CzechLynx pairs use known identities for positive/negative labels.
Bobcat pairs are identity-unknown and are used only for comparability and stress
diagnostics, not true false-match validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALGO_DIR = PROJECT_ROOT / "outputs/phase14/phase14_algorithm_inputs"
IMAGE_TABLE = ALGO_DIR / "phase14_2x2_image_evidence_table.csv"
OUT_TABLE = ALGO_DIR / "phase14_2x2_pair_comparability_table.csv"
OUT_SUMMARY = ALGO_DIR / "phase14_2x2_pair_comparability_summary.csv"
OUT_AUDIT = ALGO_DIR / "phase14_2x2_pair_comparability_table_audit.json"

WORKING_FINAL_DIR = PROJECT_ROOT / "outputs/phase14/phase14_final_2x2_working_labels"
WORKING_FINAL_INPUTS = {
    "urban_bobcat_high_confidence": WORKING_FINAL_DIR / "phase14_bobcat_high_confidence_3000_working_final_labels.csv",
    "urban_bobcat_low_evidence_stress": WORKING_FINAL_DIR / "phase14_bobcat_low_evidence_stress_3000_working_final_labels.csv",
    "wild_czechlynx_high_confidence": WORKING_FINAL_DIR / "phase14_czechlynx_high_confidence_3000_working_final_labels.csv",
    "wild_czechlynx_low_evidence_stress": WORKING_FINAL_DIR / "phase14_czechlynx_low_evidence_stress_3000_working_final_labels.csv",
}

PATH_COLUMNS = [
    "candidate_source_path",
    "local_image_path",
    "review_image_path_local",
    "local_relative_path",
    "path",
]

DEFAULT_RANDOM_SEED = 20260622
DEFAULT_UNLABELED_PAIRS_PER_BLOCK = 20_000
DEFAULT_POSITIVE_PAIRS_PER_BLOCK = 10_000
DEFAULT_NEGATIVE_PAIRS_PER_BLOCK = 10_000

PAIR_SCORE_WEIGHTS = {
    "weakest_image_utility_score": 0.20,
    "side_comparability_score": 0.22,
    "pattern_pair_score": 0.18,
    "body_visibility_pair_score": 0.12,
    "blur_pair_score": 0.10,
    "occlusion_pair_score": 0.08,
    "detector_geometry_pair_score": 0.10,
}

OUTPUT_COLUMNS = [
    "phase14_pair_index",
    "phase14_pair_id",
    "pair_block",
    "pair_sampling_role",
    "environment_axis",
    "species_axis",
    "query_evidence_axis",
    "candidate_evidence_axis",
    "pair_evidence_axis_relation",
    "query_image_evidence_id",
    "candidate_image_evidence_id",
    "query_image_key",
    "candidate_image_key",
    "query_image_path",
    "candidate_image_path",
    "same_identity_available",
    "same_identity",
    "identity_validation_scope",
    "query_image_utility_score",
    "candidate_image_utility_score",
    "weakest_image_utility_score",
    "mean_image_utility_score",
    "query_pattern_score",
    "candidate_pattern_score",
    "pattern_pair_score",
    "query_side_score",
    "candidate_side_score",
    "query_side_raw",
    "candidate_side_raw",
    "side_direction_compatibility",
    "side_comparability_score",
    "query_body_score",
    "candidate_body_score",
    "body_visibility_pair_score",
    "blur_pair_score",
    "occlusion_pair_score",
    "detector_geometry_pair_score",
    "edge_touch_pair_penalty",
    "evidence_axis_mismatch",
    "pair_comparability_score",
    "pair_risk_score",
    "pair_admissibility_band",
    "pair_review_decision",
    "pair_risk_flags",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def stable_id(*parts: object, prefix: str = "p14pair") -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:18]
    return f"{prefix}_{digest}"


def resolve_path(value: object) -> str:
    path = Path(str(value))
    return str(path if path.is_absolute() else PROJECT_ROOT / path)


def first_existing_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in frame.columns:
            return column
    return None


def load_identity_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in WORKING_FINAL_INPUTS.values():
        frame = pd.read_csv(path, low_memory=False)
        if "identity_label" not in frame.columns:
            continue
        path_col = first_existing_column(frame, PATH_COLUMNS)
        if path_col is None:
            continue
        for image_path, identity in zip(frame[path_col], frame["identity_label"]):
            if pd.isna(identity) or str(identity).strip().lower() in {"", "nan", "none"}:
                continue
            mapping[resolve_path(image_path)] = str(identity).strip()
    return mapping


def load_images(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    identity_map = load_identity_map()
    frame["identity_label_internal"] = frame["image_path"].map(identity_map).fillna("")
    frame["identity_label_available_for_validation"] = np.where(
        frame["identity_label_internal"].astype(str).str.len().gt(0), "yes", "no"
    )
    return frame.reset_index(drop=True)


def pair_block_name(species: str, left_axis: str, right_axis: str) -> str:
    if left_axis == right_axis:
        return f"{species}_{left_axis}_within"
    return f"{species}_high_low_cross"


def sample_unlabeled_pairs(frame: pd.DataFrame, n_pairs: int, rng: np.random.Generator) -> pd.DataFrame:
    if len(frame) < 2:
        return pd.DataFrame(columns=["query_idx", "candidate_idx", "pair_sampling_role"])
    max_unique = len(frame) * (len(frame) - 1)
    target = min(n_pairs, max_unique)
    rows: list[tuple[int, int, str]] = []
    seen: set[tuple[int, int]] = set()
    attempts = 0
    while len(rows) < target and attempts < target * 20:
        attempts += 1
        q = int(rng.integers(0, len(frame)))
        c = int(rng.integers(0, len(frame)))
        if q == c or (q, c) in seen:
            continue
        seen.add((q, c))
        rows.append((q, c, "identity_unknown_unlabeled"))
    return pd.DataFrame(rows, columns=["query_idx", "candidate_idx", "pair_sampling_role"])


def sample_cross_unlabeled_pairs(left: pd.DataFrame, right: pd.DataFrame, n_pairs: int, rng: np.random.Generator) -> pd.DataFrame:
    if len(left) == 0 or len(right) == 0:
        return pd.DataFrame(columns=["query_idx", "candidate_idx", "pair_sampling_role"])
    max_unique = len(left) * len(right)
    target = min(n_pairs, max_unique)
    rows: list[tuple[int, int, str]] = []
    seen: set[tuple[int, int]] = set()
    attempts = 0
    while len(rows) < target and attempts < target * 20:
        attempts += 1
        q = int(rng.integers(0, len(left)))
        c = int(rng.integers(0, len(right)))
        if (q, c) in seen:
            continue
        seen.add((q, c))
        rows.append((q, c, "identity_unknown_unlabeled"))
    return pd.DataFrame(rows, columns=["query_idx", "candidate_idx", "pair_sampling_role"])


def sample_positive_pairs(frame: pd.DataFrame, n_pairs: int, rng: np.random.Generator) -> pd.DataFrame:
    groups = {
        identity: group.index.to_numpy()
        for identity, group in frame.groupby("identity_label_internal")
        if str(identity) and len(group) >= 2
    }
    identities = list(groups)
    possible = sum(len(indices) * (len(indices) - 1) for indices in groups.values())
    target = min(n_pairs, possible)
    rows: list[tuple[int, int, str]] = []
    seen: set[tuple[int, int]] = set()
    if not identities:
        return pd.DataFrame(columns=["query_idx", "candidate_idx", "pair_sampling_role"])
    attempts = 0
    while len(rows) < target and attempts < target * 30:
        attempts += 1
        identity = identities[int(rng.integers(0, len(identities)))]
        picks = rng.choice(groups[identity], size=2, replace=False)
        q, c = int(picks[0]), int(picks[1])
        if (q, c) in seen:
            continue
        seen.add((q, c))
        rows.append((q, c, "known_identity_positive"))
    return pd.DataFrame(rows, columns=["query_idx", "candidate_idx", "pair_sampling_role"])


def sample_cross_positive_pairs(left: pd.DataFrame, right: pd.DataFrame, n_pairs: int, rng: np.random.Generator) -> pd.DataFrame:
    left_groups = {identity: group.index.to_numpy() for identity, group in left.groupby("identity_label_internal") if str(identity)}
    right_groups = {identity: group.index.to_numpy() for identity, group in right.groupby("identity_label_internal") if str(identity)}
    identities = sorted(set(left_groups) & set(right_groups))
    if not identities:
        return pd.DataFrame(columns=["query_idx", "candidate_idx", "pair_sampling_role"])
    possible = sum(len(left_groups[identity]) * len(right_groups[identity]) for identity in identities)
    target = min(n_pairs, possible)
    rows: list[tuple[int, int, str]] = []
    seen: set[tuple[int, int]] = set()
    attempts = 0
    while len(rows) < target and attempts < target * 30:
        attempts += 1
        identity = identities[int(rng.integers(0, len(identities)))]
        q = int(rng.choice(left_groups[identity]))
        c = int(rng.choice(right_groups[identity]))
        if (q, c) in seen:
            continue
        seen.add((q, c))
        rows.append((q, c, "known_identity_positive"))
    return pd.DataFrame(rows, columns=["query_idx", "candidate_idx", "pair_sampling_role"])


def sample_negative_pairs(frame: pd.DataFrame, n_pairs: int, rng: np.random.Generator) -> pd.DataFrame:
    valid = frame[frame["identity_label_internal"].astype(str).str.len().gt(0)]
    if valid["identity_label_internal"].nunique() < 2:
        return pd.DataFrame(columns=["query_idx", "candidate_idx", "pair_sampling_role"])
    indices = valid.index.to_numpy()
    identities = valid["identity_label_internal"].to_dict()
    max_unique = len(indices) * (len(indices) - 1)
    target = min(n_pairs, max_unique)
    rows: list[tuple[int, int, str]] = []
    seen: set[tuple[int, int]] = set()
    attempts = 0
    while len(rows) < target and attempts < target * 40:
        attempts += 1
        q = int(rng.choice(indices))
        c = int(rng.choice(indices))
        if q == c or identities[q] == identities[c] or (q, c) in seen:
            continue
        seen.add((q, c))
        rows.append((q, c, "known_identity_negative"))
    return pd.DataFrame(rows, columns=["query_idx", "candidate_idx", "pair_sampling_role"])


def sample_cross_negative_pairs(left: pd.DataFrame, right: pd.DataFrame, n_pairs: int, rng: np.random.Generator) -> pd.DataFrame:
    left_valid = left[left["identity_label_internal"].astype(str).str.len().gt(0)]
    right_valid = right[right["identity_label_internal"].astype(str).str.len().gt(0)]
    if left_valid.empty or right_valid.empty:
        return pd.DataFrame(columns=["query_idx", "candidate_idx", "pair_sampling_role"])
    left_indices = left_valid.index.to_numpy()
    right_indices = right_valid.index.to_numpy()
    left_ids = left_valid["identity_label_internal"].to_dict()
    right_ids = right_valid["identity_label_internal"].to_dict()
    max_unique = len(left_indices) * len(right_indices)
    target = min(n_pairs, max_unique)
    rows: list[tuple[int, int, str]] = []
    seen: set[tuple[int, int]] = set()
    attempts = 0
    while len(rows) < target and attempts < target * 40:
        attempts += 1
        q = int(rng.choice(left_indices))
        c = int(rng.choice(right_indices))
        if left_ids[q] == right_ids[c] or (q, c) in seen:
            continue
        seen.add((q, c))
        rows.append((q, c, "known_identity_negative"))
    return pd.DataFrame(rows, columns=["query_idx", "candidate_idx", "pair_sampling_role"])


def side_direction_compatibility(left: object, right: object) -> float:
    a = str(left).strip().lower()
    b = str(right).strip().lower()
    strong = {"left", "right", "both", "side"}
    weak = {"unknown", "", "nan", "<na>"}
    front_rear = {"frontal", "rear", "front", "back"}
    if a == b and a in {"left", "right", "both", "side"}:
        return 1.0
    if a == "both" and b in strong:
        return 0.90
    if b == "both" and a in strong:
        return 0.90
    if a in {"left", "right"} and b in {"left", "right"}:
        return 0.45
    if a in weak or b in weak:
        return 0.65
    if a in front_rear or b in front_rear:
        return 0.25
    return 0.50


def pair_band(score: float) -> str:
    if score >= 0.80:
        return "high_comparability"
    if score >= 0.55:
        return "reviewable_comparability"
    if score >= 0.30:
        return "low_comparability"
    return "non_comparable"


def pair_decision(score: float, flags: str) -> str:
    flag_set = set(flags.split(";")) if flags else set()
    if score >= 0.80 and not (flag_set & {"edge_touch_pair", "side_mismatch_or_unknown"}):
        return "accept_pair_evidence"
    if score >= 0.55:
        return "review_pair_evidence"
    if score >= 0.30:
        return "defer_low_pair_admissibility"
    return "species_level_or_non_comparable"


def row_risk_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if row["evidence_axis_mismatch"] == "yes":
        flags.append("mixed_high_low_pair")
    if float(row["side_comparability_score"]) < 0.35:
        flags.append("side_mismatch_or_unknown")
    if float(row["pattern_pair_score"]) < 0.35:
        flags.append("weak_pattern_pair")
    if float(row["body_visibility_pair_score"]) < 0.35:
        flags.append("weak_body_pair")
    if float(row["blur_pair_score"]) < 0.35:
        flags.append("blur_pair")
    if float(row["occlusion_pair_score"]) < 0.35:
        flags.append("occlusion_pair")
    if float(row["edge_touch_pair_penalty"]) > 0:
        flags.append("edge_touch_pair")
    return ";".join(flags) if flags else "none"


def score_pairs(pairs: pd.DataFrame, left: pd.DataFrame, right: pd.DataFrame, block: str) -> pd.DataFrame:
    if pairs.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS[1:])
    q = left.loc[pairs["query_idx"].to_numpy()].reset_index(drop=True)
    c = right.loc[pairs["candidate_idx"].to_numpy()].reset_index(drop=True)

    side_direction = [
        side_direction_compatibility(a, b)
        for a, b in zip(q["side_flank_visibility_raw"], c["side_flank_visibility_raw"])
    ]
    weakest_utility = np.minimum(q["image_evidence_utility_score"].astype(float), c["image_evidence_utility_score"].astype(float))
    side_score = (
        np.minimum(q["side_flank_evidence_score"].astype(float), c["side_flank_evidence_score"].astype(float))
        * np.array(side_direction)
    )
    edge_penalty = (
        q["md_edge_touch"].astype(str).str.lower().eq("yes")
        | c["md_edge_touch"].astype(str).str.lower().eq("yes")
    ).astype(float)

    out = pd.DataFrame()
    out["phase14_pair_id"] = [
        stable_id(block, qid, cid, role)
        for qid, cid, role in zip(q["phase14_image_evidence_id"], c["phase14_image_evidence_id"], pairs["pair_sampling_role"])
    ]
    out["pair_block"] = block
    out["pair_sampling_role"] = pairs["pair_sampling_role"].to_numpy()
    out["environment_axis"] = q["environment_axis"].to_numpy()
    out["species_axis"] = q["species_axis"].to_numpy()
    out["query_evidence_axis"] = q["evidence_axis"].to_numpy()
    out["candidate_evidence_axis"] = c["evidence_axis"].to_numpy()
    out["pair_evidence_axis_relation"] = np.where(out["query_evidence_axis"].eq(out["candidate_evidence_axis"]), "same_axis", "cross_axis")
    out["query_image_evidence_id"] = q["phase14_image_evidence_id"].to_numpy()
    out["candidate_image_evidence_id"] = c["phase14_image_evidence_id"].to_numpy()
    out["query_image_key"] = q["image_key"].to_numpy()
    out["candidate_image_key"] = c["image_key"].to_numpy()
    out["query_image_path"] = q["image_path"].to_numpy()
    out["candidate_image_path"] = c["image_path"].to_numpy()

    same_available = q["identity_label_internal"].astype(str).str.len().gt(0) & c["identity_label_internal"].astype(str).str.len().gt(0)
    same_identity = q["identity_label_internal"].astype(str).eq(c["identity_label_internal"].astype(str))
    out["same_identity_available"] = np.where(same_available, "yes", "no")
    out["same_identity"] = np.where(same_available, np.where(same_identity, "yes", "no"), "unknown")
    out["identity_validation_scope"] = np.where(
        out["species_axis"].eq("czechlynx") & out["same_identity_available"].eq("yes"),
        "known_id_validation",
        "identity_unknown_comparability_only",
    )

    out["query_image_utility_score"] = q["image_evidence_utility_score"].astype(float).round(6)
    out["candidate_image_utility_score"] = c["image_evidence_utility_score"].astype(float).round(6)
    out["weakest_image_utility_score"] = weakest_utility.round(6)
    out["mean_image_utility_score"] = ((q["image_evidence_utility_score"].astype(float) + c["image_evidence_utility_score"].astype(float)) / 2).round(6)
    out["query_pattern_score"] = q["pattern_evidence_score"].astype(float).round(6)
    out["candidate_pattern_score"] = c["pattern_evidence_score"].astype(float).round(6)
    out["pattern_pair_score"] = np.minimum(q["pattern_evidence_score"].astype(float), c["pattern_evidence_score"].astype(float)).round(6)
    out["query_side_score"] = q["side_flank_evidence_score"].astype(float).round(6)
    out["candidate_side_score"] = c["side_flank_evidence_score"].astype(float).round(6)
    out["query_side_raw"] = q["side_flank_visibility_raw"].to_numpy()
    out["candidate_side_raw"] = c["side_flank_visibility_raw"].to_numpy()
    out["side_direction_compatibility"] = np.array(side_direction).round(6)
    out["side_comparability_score"] = side_score.round(6)
    out["query_body_score"] = q["body_visibility_score"].astype(float).round(6)
    out["candidate_body_score"] = c["body_visibility_score"].astype(float).round(6)
    out["body_visibility_pair_score"] = np.minimum(q["body_visibility_score"].astype(float), c["body_visibility_score"].astype(float)).round(6)
    out["blur_pair_score"] = np.minimum(q["blur_evidence_score"].astype(float), c["blur_evidence_score"].astype(float)).round(6)
    out["occlusion_pair_score"] = np.minimum(q["occlusion_evidence_score"].astype(float), c["occlusion_evidence_score"].astype(float)).round(6)
    out["detector_geometry_pair_score"] = np.minimum(q["detector_geometry_score"].astype(float), c["detector_geometry_score"].astype(float)).round(6)
    out["edge_touch_pair_penalty"] = edge_penalty.round(6)
    out["evidence_axis_mismatch"] = np.where(out["query_evidence_axis"].eq(out["candidate_evidence_axis"]), "no", "yes")

    score = sum(float(weight) * out[column].astype(float) for column, weight in PAIR_SCORE_WEIGHTS.items())
    score = (score - 0.08 * out["edge_touch_pair_penalty"].astype(float)).clip(0, 1)
    out["pair_comparability_score"] = score.round(6)
    out["pair_risk_score"] = (1 - score).round(6)
    out["pair_admissibility_band"] = out["pair_comparability_score"].map(pair_band)
    out["pair_risk_flags"] = out.apply(row_risk_flags, axis=1)
    out["pair_review_decision"] = [
        pair_decision(float(score_value), flags)
        for score_value, flags in zip(out["pair_comparability_score"], out["pair_risk_flags"])
    ]
    return out[OUTPUT_COLUMNS[1:]]


def sample_block(
    images: pd.DataFrame,
    species: str,
    left_axis: str,
    right_axis: str,
    rng: np.random.Generator,
    unlabeled_pairs: int,
    positive_pairs: int,
    negative_pairs: int,
) -> pd.DataFrame:
    left = images[(images["species_axis"].eq(species)) & (images["evidence_axis"].eq(left_axis))].copy().reset_index(drop=True)
    right = images[(images["species_axis"].eq(species)) & (images["evidence_axis"].eq(right_axis))].copy().reset_index(drop=True)
    block = pair_block_name(species, left_axis, right_axis)
    if left_axis == right_axis:
        if species == "czechlynx":
            positives = sample_positive_pairs(left, positive_pairs, rng)
            negatives = sample_negative_pairs(left, negative_pairs, rng)
            pairs = pd.concat([positives, negatives], ignore_index=True)
        else:
            pairs = sample_unlabeled_pairs(left, unlabeled_pairs, rng)
        return score_pairs(pairs, left, left, block)

    if species == "czechlynx":
        positives = sample_cross_positive_pairs(left, right, positive_pairs, rng)
        negatives = sample_cross_negative_pairs(left, right, negative_pairs, rng)
        pairs = pd.concat([positives, negatives], ignore_index=True)
    else:
        pairs = sample_cross_unlabeled_pairs(left, right, unlabeled_pairs, rng)
    return score_pairs(pairs, left, right, block)


def build_pair_table(
    images: pd.DataFrame,
    seed: int,
    unlabeled_pairs: int,
    positive_pairs: int,
    negative_pairs: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    blocks = []
    for species in ["bobcat", "czechlynx"]:
        for left_axis, right_axis in [
            ("high_confidence", "high_confidence"),
            ("low_evidence_stress", "low_evidence_stress"),
            ("high_confidence", "low_evidence_stress"),
        ]:
            blocks.append(
                sample_block(
                    images,
                    species,
                    left_axis,
                    right_axis,
                    rng,
                    unlabeled_pairs,
                    positive_pairs,
                    negative_pairs,
                )
            )
    table = pd.concat(blocks, ignore_index=True)
    table = table.drop_duplicates("phase14_pair_id").reset_index(drop=True)
    table.insert(0, "phase14_pair_index", range(1, len(table) + 1))
    return table[OUTPUT_COLUMNS]


def summarize(table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouped = table.groupby(["species_axis", "environment_axis", "pair_block", "pair_sampling_role"], dropna=False)
    for keys, frame in grouped:
        rows.append(
            {
                "species_axis": keys[0],
                "environment_axis": keys[1],
                "pair_block": keys[2],
                "pair_sampling_role": keys[3],
                "pair_count": int(len(frame)),
                "known_same_identity_yes": int(frame["same_identity"].eq("yes").sum()),
                "known_same_identity_no": int(frame["same_identity"].eq("no").sum()),
                "same_identity_unknown": int(frame["same_identity"].eq("unknown").sum()),
                "pair_comparability_mean": float(frame["pair_comparability_score"].mean()),
                "pair_comparability_median": float(frame["pair_comparability_score"].median()),
                "pair_risk_mean": float(frame["pair_risk_score"].mean()),
                "high_comparability_count": int(frame["pair_admissibility_band"].eq("high_comparability").sum()),
                "reviewable_comparability_count": int(frame["pair_admissibility_band"].eq("reviewable_comparability").sum()),
                "low_or_non_comparable_count": int(
                    frame["pair_admissibility_band"].isin(["low_comparability", "non_comparable"]).sum()
                ),
                "decision_counts": json.dumps(
                    {str(k): int(v) for k, v in frame["pair_review_decision"].value_counts().sort_index().items()},
                    sort_keys=True,
                ),
            }
        )
    return pd.DataFrame(rows)


def audit_payload(table: pd.DataFrame, summary: pd.DataFrame, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "inputs": {
            "image_evidence_table": rel(args.image_table),
            "working_final_identity_sources": {key: rel(path) for key, path in WORKING_FINAL_INPUTS.items()},
        },
        "outputs": {
            "pair_table": rel(args.output),
            "summary": rel(args.summary),
            "audit": rel(args.audit),
        },
        "row_count": int(len(table)),
        "column_count": int(len(table.columns)),
        "random_seed": int(args.seed),
        "sampling": {
            "unlabeled_pairs_per_bobcat_block": int(args.unlabeled_pairs_per_block),
            "positive_pairs_per_czechlynx_block": int(args.positive_pairs_per_block),
            "negative_pairs_per_czechlynx_block": int(args.negative_pairs_per_block),
        },
        "pair_block_counts": {str(k): int(v) for k, v in table["pair_block"].value_counts().sort_index().items()},
        "same_identity_counts": {str(k): int(v) for k, v in table["same_identity"].value_counts().sort_index().items()},
        "duplicate_pair_ids": int(table["phase14_pair_id"].duplicated().sum()),
        "self_pairs": int(table["query_image_evidence_id"].eq(table["candidate_image_evidence_id"]).sum()),
        "scientific_boundary": {
            "czechlynx_pairs": "known identity positive/negative validation is available",
            "bobcat_pairs": "identity unknown comparability and stress diagnostics only",
            "descriptor_similarity": "not included in step 2; added in step 3",
        },
        "summary_rows": summary.to_dict(orient="records"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-table", type=Path, default=IMAGE_TABLE)
    parser.add_argument("--output", type=Path, default=OUT_TABLE)
    parser.add_argument("--summary", type=Path, default=OUT_SUMMARY)
    parser.add_argument("--audit", type=Path, default=OUT_AUDIT)
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--unlabeled-pairs-per-block", type=int, default=DEFAULT_UNLABELED_PAIRS_PER_BLOCK)
    parser.add_argument("--positive-pairs-per-block", type=int, default=DEFAULT_POSITIVE_PAIRS_PER_BLOCK)
    parser.add_argument("--negative-pairs-per-block", type=int, default=DEFAULT_NEGATIVE_PAIRS_PER_BLOCK)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.image_table.exists():
        raise FileNotFoundError(f"Missing image evidence table: {args.image_table}")
    images = load_images(args.image_table)
    table = build_pair_table(
        images,
        args.seed,
        args.unlabeled_pairs_per_block,
        args.positive_pairs_per_block,
        args.negative_pairs_per_block,
    )
    summary = summarize(table)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    summary.to_csv(args.summary, index=False)
    payload = audit_payload(table, summary, args)
    args.audit.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))

    if payload["duplicate_pair_ids"] != 0:
        raise SystemExit("Duplicate pair IDs detected")
    if payload["self_pairs"] != 0:
        raise SystemExit("Self-pairs detected")
    if table["same_identity"].eq("yes").sum() == 0 or table["same_identity"].eq("no").sum() == 0:
        raise SystemExit("CzechLynx positive/negative pair labels were not generated")
    if table["same_identity"].eq("unknown").sum() == 0:
        raise SystemExit("Bobcat identity-unknown comparability pairs were not generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
